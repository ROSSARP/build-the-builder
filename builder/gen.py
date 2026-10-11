"""Generate a Freya workflow JSON from a structured spec and the bank's tool API.

The generator is spec-driven: every value that can change between briefs
(identity questions, holidays, deadline bands, closing table, note reasons,
tool fields) comes from the extracted spec or the tool API file. The
mechanism (node structure, business-day math, tool wiring) is fixed.

Two layers sit on top of the structured spec:

* the RULE LEDGER (spec["rule_ledger"]): typed rule records the extractor
  copies out of the brief. ``apply_ledger`` fills empty structured slots from
  it, and ``compile_closing`` turns its closing_rule into the mechanism below.
* the DETERMINISTIC CLOSE-CALL CORRECTOR (``close_corrector_code``): a
  pre_process_code hook, generated from the closing_rule table, that recomputes
  close_call's outcome/reason from the engine's own counters and tool results
  (promises recorded, transfers, notes, identity state, callbacks) and
  overwrites whatever the dialogue model proposed. The model cannot lose a
  promise it recorded, a transfer it made, or a note reason it wrote.

Prompt text is generated in the brief's language: ``localize`` rewrites the
fixed English scaffolding into the brief's language (Turkish today) at
generation time; rule text copied from the brief is already in that language.
"""
import json, os, sys

# ---------------------------------------------------------------- language

def brief_language(spec):
    """The language the brief is written in ("Turkish", "English", ...)."""
    raw = str((spec or {}).get("language") or "English").strip()
    return raw or "English"

def is_turkish(lang):
    low = str(lang or "").lower()
    return "turk" in low or "türk" in low or low.strip() in ("tr", "tr-tr", "tr_tr")

def speak_name(lang):
    return "Türkçe" if is_turkish(lang) else str(lang or "English")

def goodbye_phrase(lang):
    return "İyi günler." if is_turkish(lang) else "Have a good day."

# The fixed scaffolding sentences, English -> the brief's language. Applied with
# plain replacements, longest first, and only when the brief is not English, so
# an English build stays byte-for-byte what it always was. Rule text copied from
# the brief never matches a key and passes through untouched.
TR_SENTENCES = [
    ("Disambiguation: not_verified is ONLY for security-check endings after the questions were asked "
     "(failed = wrong answers, declined = refusal to answer). not_reached is for calls where the right "
     "person was never confirmed or never engaged: if no security question was ever answered, the call "
     "is not_reached with reason unclear — never not_verified.",
     "Ayrım: not_verified YALNIZCA güvenlik soruları sorulduktan sonra biten aramalar içindir "
     "(failed = yanlış cevaplar, declined = cevap vermeyi reddetme). not_reached, doğru kişinin hiç "
     "doğrulanmadığı ya da konuşmaya hiç girmediği aramalar içindir: hiçbir güvenlik sorusu "
     "cevaplanmadıysa arama not_reached ve reason unclear ile biter — asla not_verified."),
    ("Ends the call. You normally do NOT call this: the phrase \"Have a good day.\" ends the call by "
     "itself. Call it without any text only if the customer answers after your goodbye.",
     "Aramayı bitirir. Normalde bunu ÇAĞIRMAZSINIZ: \"İyi günler.\" cümlesi aramayı kendiliğinden "
     "bitirir. Yalnızca müşteri vedanızdan sonra konuşursa metinsiz çağırın."),
    ("If the result's hint says the day and month were swapped, ask the customer to say the month as a "
     "word, then verify the new answer. That retry is not a wrong answer.",
     "Sonuçtaki hint gün ile ayın yer değiştirdiğini söylüyorsa müşteriden ayı kelimeyle söylemesini "
     "isteyin, sonra yeni cevabı doğrulayın. Bu yeniden deneme yanlış cevap sayılmaz."),
    ("Never close the check as failed while the customer is still giving an answer in parts; ask for "
     "the rest first.", "Müşteri cevabı parça parça verirken kontrolü asla failed olarak kapatmayın; "
     "önce kalanı isteyin."),
    ("The customer never gave a usable security answer after several attempts. Do not ask again.",
     "Müşteri birkaç denemeye rağmen kullanılabilir bir güvenlik cevabı vermedi. Tekrar sormayın."),
    ("Close the call as not_verified with reason declined: say goodbye ending with \"Have a good day.\"",
     "Aramayı not_verified ve reason declined ile kapatın: veda edip \"İyi günler.\" diyerek bitirin."),
    ("You are on a collection call. The customer's identity is verified.",
     "Bir tahsilat aramasındasınız. Müşterinin kimliği doğrulandı."),
    ("The customer is going through hardship. Say exactly ONE short sentence of sympathy, then make NO "
     "persuasion attempt at all.", "Müşteri zor bir dönemden geçiyor. Tam olarak BİR kısa teselli "
     "cümlesi söyleyin ve hiçbir ikna denemesi yapmayın."),
    ("Offer the customer support team ONCE: if they accept, CALL transfer_to_agent with the support "
     "queue and end the call; if they decline, end the call without a promise.",
     "Müşteriye destek ekibini BİR KEZ teklif edin: kabul ederse transfer_to_agent aracını support "
     "kuyruğuyla ÇAĞIRIN ve aramayı bitirin; reddederse vaatsiz bitirin."),
    ("If the customer names a payment date or amount themselves, still record it under the date and "
     "amount rules — CALL create_promise after the read-back and a clear yes.",
     "Müşteri kendisi bir ödeme tarihi ya da tutarı söylerse yine tarih ve tutar kurallarına göre "
     "kaydedin — geri okuma ve net bir evetten sonra create_promise aracını ÇAĞIRIN."),
    ("If a promise was already read back and confirmed, CALL create_promise IMMEDIATELY, before any "
     "other talk — a confirmed promise must always be recorded.",
     "Bir vaat zaten geri okunup onaylandıysa başka her konuşmadan önce create_promise aracını HEMEN "
     "ÇAĞIRIN — onaylanan vaat her zaman kaydedilmelidir."),
    ("Never say goodbye in a way that implies a promise was recorded when create_promise was not called.",
     "create_promise çağrılmadıysa vaat kaydedilmiş gibi bir veda etmeyin."),
    ("The customer's latest message describes hardship: illness, a death in the family, job loss, "
     "care-home or medical fees, a closed business, lost income, or similar serious trouble. A plain "
     "yes, a confirmation, or a payment date is NEVER hardship.",
     "Müşterinin son mesajı zor durumu anlatıyor: hastalık, ailede vefat, iş kaybı, bakımevi ya da "
     "tedavi masrafları, kapanan iş, gelir kaybı veya benzeri ciddi bir sıkıntı. Düz bir evet, bir "
     "onay ya da bir ödeme tarihi ASLA hardship değildir."),
    ("The customer declines the support team and wants to keep talking about paying, or names an amount "
     "or a date themselves.",
     "Müşteri destek ekibini reddediyor ve ödeme konuşmasına devam etmek istiyor ya da kendisi bir "
     "tutar veya tarih söylüyor."),
    ("A claim that THIS past-due amount was already paid — however the customer says it (in the app, by "
     "card, online, yesterday) — means close paid, no promise, even when the customer asks when the "
     "payment shows up.", "BU gecikmiş tutarın zaten ödendiği iddiası — müşteri bunu nasıl söylerse "
     "söylesin (uygulamadan, kartla, internetten, dün) — paid olarak kapatmak demektir, vaat alınmaz; "
     "müşteri ödemenin ne zaman görüneceğini sorsa bile."),
    ("A claim that the product is not theirs or was closed long ago means dispute.",
     "Ürünün kendisine ait olmadığı ya da uzun zaman önce kapatıldığı iddiası dispute demektir."),
    ("When transferring for restructuring, say only that you will connect them with the restructuring "
     "team — never describe or promise an instalment plan, lower instalments or any new terms.",
     "Yeniden yapılandırma için transfer ederken yalnızca kendilerini yeniden yapılandırma ekibine "
     "bağlayacağınızı söyleyin — asla bir taksit planı, daha düşük taksit ya da yeni koşul anlatmayın "
     "ve vaat etmeyin."),
    ("Before ending the call, CALL add_note for EVERY product that ended without a promise, with the "
     "reason the notes rules say.", "Aramayı bitirmeden önce vaatsiz biten HER ürün için not "
     "kurallarının söylediği sebeple add_note aracını ÇAĞIRIN."),
    ("A date or an amount the customer proposes is NEVER a refusal: respond to that value under the "
     "date and amount rules, and do not count it as one of your persuasion attempts.",
     "Müşterinin önerdiği bir tarih ya da tutar ASLA ret değildir: bu değere tarih ve tutar "
     "kurallarına göre karşılık verin ve onu ikna denemelerinden saymayın."),
    ("Before closing as refused, make sure the customer has had the chance to name their own amount or "
     "date.", "refused olarak kapatmadan önce müşterinin kendi tutarını ya da tarihini söyleme fırsatı "
     "olduğundan emin olun."),
    ("After a refusal, do NOT say goodbye in the same turn: give the customer one more turn to speak "
     "before you close.", "Bir retten sonra aynı turda veda ETMEYİN: kapatmadan önce müşteriye bir tur "
     "daha konuşma fırsatı verin."),
    ("Say goodbye ending with \"Have a good day.\" The close outcome is recorded automatically from the "
     "rules above — you do NOT call close_call yourself, it is not available to you.",
     "\"İyi günler.\" diyerek veda edin. Kapanış sonucu yukarıdaki kurallardan otomatik kaydedilir — "
     "close_call aracını siz ÇAĞIRMAZSINIZ, sizin için kullanılabilir değildir."),
    ("When the call must end, say goodbye ending with \"Have a good day.\"",
     "Arama bitmesi gerektiğinde veda edip \"İyi günler.\" diyerek bitirin."),
    ("To end the call, say goodbye ending with \"Have a good day.\"",
     "Aramayı bitirmek için veda edip \"İyi günler.\" diyerek bitirin."),
    ("Say you are connecting them to the right team now, then end the call by saying goodbye ending "
     "with \"Have a good day.\"", "Şimdi onları doğru ekibe bağladığınızı söyleyin, sonra veda edip "
     "\"İyi günler.\" diyerek aramayı bitirin."),
    ("Tell the customer to say the month as a word, then call verify_identity again with the new answer.",
     "Müşteriye ayı kelimeyle söylemesini söyleyin, sonra yeni cevapla verify_identity aracını tekrar "
     "çağırın."),
    ("This answer passed. Move to the next security question, or continue the call if all questions "
     "passed.", "Bu cevap doğru. Sıradaki güvenlik sorusuna geçin; tüm sorular geçtiyse aramaya devam "
     "edin."),
    ("The identity check failed. Tell the customer to use the mobile app or a branch, then end the call.",
     "Kimlik kontrolü başarısız oldu. Müşteriye mobil uygulamayı ya da bir şubeyi kullanmasını "
     "söyleyin, sonra aramayı bitirin."),
    ("Tell the customer the answer was wrong and ask the same question again.",
     "Müşteriye cevabın yanlış olduğunu söyleyin ve aynı soruyu tekrar sorun."),
    ("Say the promise is recorded and the text-message sentence. Then continue with any remaining "
     "product, or end the call.", "Verdiğiniz sözün kaydedildiğini ve kısa mesaj cümlesini söyleyin. "
     "Sonra kalan ürün varsa devam edin ya da aramayı bitirin."),
    ("The recording failed. Call create_promise once more. If it fails again, tell the customer it could "
     "not be recorded and end the call.", "Kayıt başarısız oldu. create_promise aracını bir kez daha "
     "çağırın. Yine başarısız olursa müşteriye kaydedilemediğini söyleyip aramayı bitirin."),
    ("The note is recorded. Continue with the remaining products, or end the call.",
     "Not kaydedildi. Kalan ürünlerle devam edin ya da aramayı bitirin."),
    ("The note failed. Call add_note once more, then continue or end the call.",
     "Not kaydedilemedi. add_note aracını bir kez daha çağırın, sonra devam edin ya da aramayı bitirin."),
    ("Record a payment promise. CALL it only after the customer said yes to the read-back of amount and "
     "date. The date is filled in for you from what the customer agreed.",
     "Ödeme vaadini kaydeder. Yalnızca müşteri tutar ve tarihin geri okunmasına evet dedikten sonra "
     "ÇAĞIRIN. Tarih, müşterinin kabul ettiğinden sizin için doldurulur."),
    ("Check one security answer. CALL it once for each answer the customer gives.",
     "Bir güvenlik cevabını kontrol eder. Müşterinin verdiği her cevap için bir kez ÇAĞIRIN."),
    ("The customer's late products. CALL it once, before you say anything about the account.",
     "Müşterinin gecikmiş ürünleri. Hesap hakkında bir şey söylemeden önce bir kez ÇAĞIRIN."),
    ("Hand the call to a person. CALL it with the queue the rule says.",
     "Aramayı bir kişiye aktarır. Kuralların söylediği kuyrukla ÇAĞIRIN."),
    ("Book a callback. CALL it only after the customer agreed a day and time inside the window.",
     "Geri arama randevusu oluşturur. Yalnızca müşteri pencere içinde bir gün ve saat üzerinde "
     "anlaştıktan sonra ÇAĞIRIN."),
    ("Record how the call ended. The platform calls it automatically when the call ends.",
     "Aramanın nasıl bittiğini kaydeder. Platform arama bittiğinde bunu otomatik çağırır."),
    ("Record why a product ended without a promise. CALL it once per product without a promise.",
     "Bir ürünün neden vaatsiz bittiğini kaydeder. Vaat alınamayan her ürün için bir kez ÇAĞIRIN."),
    ("You just started the call. Say nothing about collections, debt, payment or any product before the "
     "identity is verified.", "Arama yeni başladı. Kimlik doğrulanmadan önce tahsilat, borç, ödeme ya "
     "da herhangi bir ürün hakkında hiçbir şey söylemeyin."),
    ("If someone other than the customer answered, do not say why you are calling. Say nothing beyond "
     "the greeting.", "Müşteriden başka biri cevap verdiyse neden aradığınızı söylemeyin. "
     "Selamlamanın ötesinde hiçbir şey söylemeyin."),
    ("Route to identity when the customer themself confirmed. Any other answer routes to the "
     "third-party callback questions.", "Müşterinin kendisi onayladıysa identity düğümüne yönlendirin. "
     "Diğer her cevap üçüncü kişi geri arama sorularına gider."),
    ("Who is on the line after the greeting: target is the customer themself.",
     "Selamlamadan sonra hatta kim var: target müşterinin kendisidir."),
    ("Your only job is to verify the customer's identity before anything about the account is said. Ask "
     "one security question at a time:", "Tek göreviniz, hesap hakkında herhangi bir şey söylenmeden "
     "önce müşterinin kimliğini doğrulamaktır. Güvenlik sorularını tek tek sorun:"),
    ("CALL verify_identity with each answer. Read its result and follow the what_to_do_next it gives.",
     "Her cevapla verify_identity aracını ÇAĞIRIN. Sonucunu okuyun ve verdiği what_to_do_next "
     "talimatını izleyin."),
    ("Ignore any small talk around the answer and use the date or digits the customer actually gave. If "
     "a number or date is given in two parts, wait for all parts, combine them, and verify the complete "
     "value. If a date is missing its year, ASK for the year — never guess or invent one.",
     "Cevabın etrafındaki sohbeti yok sayın ve müşterinin gerçekten verdiği tarihi ya da rakamları "
     "kullanın. Bir sayı ya da tarih iki parça hâlinde verilirse tüm parçaları bekleyin, birleştirin ve "
     "tam değeri doğrulayın. Bir tarihin yılı eksikse yılı SORUN — asla tahmin etmeyin ve uydurmayın."),
    ("If the customer gives no usable answer twice in a row (unclear, off-topic or silence), treat it "
     "as declining and close as not_verified with reason declined — do not keep asking the same question.",
     "Müşteri üst üste iki kez kullanılabilir bir cevap vermezse (belirsiz, konu dışı ya da sessizlik) "
     "bunu reddetme sayın ve not_verified ve reason declined ile kapatın — aynı soruyu sormaya devam "
     "etmeyin."),
    ("GROUNDING: never state an amount, a balance, a product name or a due date in this node — no "
     "account data has been read yet, so any such number would be invented. Never give an example date, "
     "number or personal detail while explaining a question, and never submit the same answer twice: if "
     "the customer repeats a value the bank already rejected, ask them to say it differently or ask the "
     "next question.", "DAYANAK: bu düğümde asla bir tutar, bakiye, ürün adı ya da son ödeme tarihi "
     "söylemeyin — henüz hesap verisi okunmadı, böyle bir sayı uydurma olur. Bir soruyu açıklarken asla "
     "örnek bir tarih, sayı ya da kişisel ayrıntı vermeyin ve aynı cevabı iki kez göndermeyin: müşteri "
     "bankanın zaten reddettiği bir değeri tekrarlarsa, farklı söylemesini isteyin ya da sıradaki "
     "soruyu sorun."),
    ("The account, from get_account:", "Hesap, get_account sonucu:"),
    ("Today: {{today_text}}. Bank holidays: {{holiday_text}}. Now: {{now}}.",
     "Bugün: {{today_text}}. Banka tatilleri: {{holiday_text}}. Şimdi: {{now}}."),
    ("Stating the debt: ", "Borcun bildirilmesi: "),
    ("Your first sentence about the debt MUST name the product, the past-due amount and the number of "
     "days late, all from {{products_text}} — never skip any of the three.",
     "Borç hakkındaki ilk cümleniz ürünü, gecikmiş tutarı ve gecikme gün sayısını {{products_text}} "
     "içinden söylemek ZORUNDADIR — üçünden hiçbirini atlamayın."),
    ("Per-product facts (from the bank):", "Ürün başına bilgiler (bankadan):"),
    ("Each product has its OWN latest date: do not apply one product's deadline to another. A date past "
     "one product's latest date is still fine for a product whose latest date is later. Make exactly the "
     "listed number of attempts for each product, never more.",
     "Her ürünün KENDİ son tarihi vardır: bir ürünün son tarihini diğerine uygulamayın. Bir ürünün son "
     "tarihini geçen bir tarih, son tarihi daha ileri olan bir ürün için hâlâ uygundur. Her ürün için "
     "listelenen sayıda ikna denemesi yapın, asla daha fazla değil."),
    ("Weekday names mean these exact dates:", "Hafta günü adları şu kesin tarihleri belirtir:"),
    ("this week: {{this_week_days}}", "bu hafta: {{this_week_days}}"),
    ("next week: {{next_week_days}}", "gelecek hafta: {{next_week_days}}"),
    ("When the customer says 'next Friday', use the next-week Friday from that list, never this week's.",
     "Müşteri 'gelecek cuma' derse o listedeki gelecek haftanın cuma gününü kullanın, asla bu haftanın "
     "cumasını."),
    ("The date check says: {{date_msg}}. The date to record in create_promise is filled in for you as "
     "{{fixed_date}}. If the check says the date cannot be recorded, do NOT call create_promise with it; "
     "offer the latest date instead. When the date check MOVES the customer's date (weekend, holiday or "
     "deadline), always read back the MOVED date and wait for a fresh yes before recording — never "
     "record a date the customer has not confirmed.",
     "Tarih kontrolü şunu diyor: {{date_msg}}. create_promise içine kaydedilecek tarih sizin için "
     "{{fixed_date}} olarak doldurulur. Kontrol tarihin kaydedilemeyeceğini söylüyorsa onunla "
     "create_promise ÇAĞIRMAYIN; bunun yerine en son tarihi teklif edin. Tarih kontrolü müşterinin "
     "tarihini DEĞİŞTİRİRSE (hafta sonu, tatil ya da son tarih), her zaman DEĞİŞEN tarihi geri okuyun ve "
     "kaydetmeden önce yeni bir evet bekleyin — müşterinin onaylamadığı bir tarihi asla kaydetmeyin."),
    ("Amounts: ", "Tutarlar: "),
    ("When you offer the floor, always say that the rest of the balance stays overdue. Whenever the "
     "recorded amount is below the full amount — whether you offered it or the customer proposed it — "
     "say that the rest of the balance stays overdue. Offer the floor AT MOST ONCE; if it is refused, "
     "treat it as a flat refusal. NEVER ask the customer how much they can pay: you propose every amount.",
     "Taban tutarı teklif ettiğinizde her zaman bakiyenin kalanının gecikmiş kaldığını söyleyin. "
     "Kaydedilen tutar tam tutarın altındaysa — siz teklif etmiş olun ya da müşteri önermiş olsun — "
     "bakiyenin kalanının gecikmiş kaldığını söyleyin. Taban tutarı EN FAZLA BİR KEZ teklif edin; "
     "reddedilirse bunu net bir ret sayın. Müşteriye ASLA ne kadar ödeyebileceğini sormayın: her "
     "tutarı siz teklif edersiniz."),
    ("Persuasion: ", "İkna: "),
    ("Attempt 1 proposes {{attempt1}}.", "Deneme 1, {{attempt1}} tarihini teklif eder."),
    ("A flat refusal uses the attempts in order: attempt 1 first (the FULL amount on {{attempt1}}, the "
     "last business day of this week), and attempt 2 only when the band allows it (the floor on the "
     "latest date). Never skip to attempt 2 before attempt 1 was made. NEVER repeat an amount-and-date "
     "offer the customer already refused; if the floor was already offered and refused, make no further "
     "offer and close as refused.",
     "Net bir ret, denemeleri sırayla kullanır: önce deneme 1 ({{attempt1}} tarihinde TAM tutar, bu "
     "haftanın son iş günü), deneme 2 ise yalnızca bant izin veriyorsa (en son tarihte taban tutar). "
     "Deneme 1 yapılmadan asla deneme 2'ye geçmeyin. Müşterinin zaten reddettiği bir tutar-tarih "
     "teklifini ASLA tekrarlamayın; taban tutar zaten teklif edilip reddedildiyse başka teklif yapmayın "
     "ve refused olarak kapatın."),
    ("Hardship: ", "Zor durum: "),
    ("When hardship is mentioned (illness, a death in the family, job loss): say exactly ONE short "
     "sentence of sympathy, then make NO persuasion attempt. Offer the support team once. If they "
     "accept, call transfer_to_agent with the support queue. If they decline, close without a promise. "
     "A date or amount the customer names themselves is still recorded.",
     "Zor durumdan söz edilirse (hastalık, ailede vefat, iş kaybı): tam olarak BİR kısa teselli cümlesi "
     "söyleyin, sonra HİÇBİR ikna denemesi yapmayın. Destek ekibini bir kez teklif edin. Kabul "
     "ederlerse transfer_to_agent aracını support kuyruğuyla çağırın. Reddederlerse vaatsiz kapatın. "
     "Müşterinin kendisinin söylediği tarih ya da tutar yine kaydedilir."),
    ("What customers say: ", "Müşterilerin söyledikleri: "),
    ("Recording a promise: ", "Vaat kaydetme: "),
    ("Never call create_promise without the customer's clear yes to the read-back.",
     "Müşteri geri okumaya net bir evet demeden create_promise aracını asla çağırmayın."),
    ("GROUNDING: say ONLY numbers, dates and product names that appear in the tool results. If a number "
     "is not in the results, do not say it. Never claim a capability the bank's tools do not have (no "
     "instalment plans, no waivers, no transfers the rules do not name).",
     "DAYANAK: yalnızca araç sonuçlarında görünen sayıları, tarihleri ve ürün adlarını söyleyin. Bir "
     "sayı sonuçlarda yoksa onu söylemeyin. Bankanın araçlarında olmayan bir yeteneği asla iddia "
     "etmeyin (taksit planı yok, borç silme yok, kuralların adlandırmadığı transfer yok)."),
    ("Notes: ", "Notlar: "),
    ("Ending the call: ", "Aramanın bitirilmesi: "),
    ("Going through the products: ", "Ürünlerin tek tek ele alınması: "),
    ("Several products: ", "Birkaç ürün: "),
    ("Dates: ", "Tarihler: "),
    ("Someone other than the customer answered, or it is unclear who is on the line.",
     "Müşteriden başka biri cevap verdi ya da hatta kimin olduğu belirsiz."),
    ("Do not say why the bank is calling. Say nothing about any account.",
     "Bankanın neden aradığını söylemeyin. Hesap hakkında hiçbir şey söylemeyin."),
    ("GROUNDING: never invent a name, number or detail the caller did not give you.",
     "DAYANAK: arayan kişinin vermediği bir isim, numara ya da ayrıntıyı asla uydurmayın."),
    ("Otherwise ask when the customer can be reached.", "Aksi hâlde müşteriye ne zaman ulaşılabileceğini sorun."),
    ("If the day or the time is outside the window, ask once for another time.",
     "Gün ya da saat pencere dışındaysa bir kez başka bir zaman isteyin."),
    ("If that is also outside it, do not schedule and close as ",
     "O da pencere dışındaysa randevu oluşturmayın ve şu şekilde kapatın: "),
    ("Only if the person literally says the number does not belong to the customer, close as ",
     "Yalnızca kişi numaranın müşteriye ait olmadığını açıkça söylerse şöyle kapatın: "),
    ("Do not use this close for anything else.", "Bu kapanışı başka bir şey için kullanmayın."),
    ("If the person says the customer has died, say ",
     "Kişi müşterinin vefat ettiğini söylerse şunu söyleyin: "),
    ("ask nothing else, and close as ", "başka hiçbir şey sormayın ve şöyle kapatın: "),
    ("If a valid day and time are agreed, CALL schedule_callback with them and close as ",
     "Geçerli bir gün ve saat üzerinde anlaşılırsa schedule_callback aracını bunlarla ÇAĞIRIN ve şöyle "
     "kapatın: "),
    ("A callback is for ", "Geri arama şu zaman içindir: "),
    ("a day and time inside the window", "pencere içinde bir gün ve saat"),
    ("What the person on the line said.", "Hattaki kişinin söylediği."),
    ("The day the person named for a callback.", "Kişinin geri arama için söylediği gün."),
    ("The time the person named for a callback, HH:MM.",
     "Kişinin geri arama için söylediği saat, SS:DD."),
    ("The person on the line insists they are the customer themself.",
     "Hattaki kişi kendisinin müşteri olduğunu ısrarla söylüyor."),
    ("The person insists they ARE the customer", "Kişi müşterinin KENDİSİ olduğunu söylüyor"),
    ("The person now denies knowing the account or says it is a wrong number",
     "Kişi artık hesabı bilmediğini söylüyor ya da numaranın yanlış olduğunu söylüyor"),
    ("The person denies having this account or loan, or says the number is wrong or belongs to someone "
     "else.", "Kişi bu hesabı ya da krediyi almadığını söylüyor ya da numaranın yanlış olduğunu veya "
     "başkasına ait olduğunu söylüyor."),
    ("The customer mentions hardship in their latest message",
     "Müşteri son mesajında zor durumdan söz ediyor"),
    ("The customer named a payment date", "Müşteri bir ödeme tarihi söyledi"),
    ("Keep asking", "Sormaya devam et"),
    ("Keep going", "Devam et"),
    ("Keep talking", "Konuşmaya devam et"),
    ("The customer themself confirmed", "Müşterinin kendisi onayladı"),
    ("A relative answered", "Bir yakını cevap verdi"),
    ("Wrong number", "Yanlış numara"),
    ("The customer has died", "Müşteri vefat etmiş"),
    ("Both security answers verified", "Her iki güvenlik cevabı doğrulandı"),
    ("The customer declines support and wants to continue the payment conversation",
     "Müşteri desteği reddediyor ve ödeme konuşmasına devam etmek istiyor"),
    ("The customer's answer to the read-back confirmation.",
     "Müşterinin geri okuma onayına cevabı."),
    ("The customer's answer to the support-team offer.",
     "Müşterinin destek ekibi teklifine cevabı."),
    ("The payment date the CUSTOMER named in their own words. Never take a date that only the assistant "
     "said (for example from a read-back); when the customer only confirms, leave it unset.",
     "Müşterinin kendi sözleriyle söylediği ödeme tarihi. Yalnızca asistanın söylediği bir tarihi "
     "(örneğin geri okumadan) asla almayın; müşteri yalnızca onaylıyorsa boş bırakın."),
    ("The payment amount the customer agreed to, if any.",
     "Müşterinin kabul ettiği ödeme tutarı, varsa."),
    ("The payment date the CUSTOMER named in their own words, if any.",
     "Müşterinin kendi sözleriyle söylediği ödeme tarihi, varsa."),
    ("Why a product ended without a promise.", "Bir ürünün neden vaatsiz bittiği."),
    ("hardship is ANY serious personal or financial trouble the customer mentions: illness, a death in "
     "the family, job loss, care-home or medical fees they cannot afford, a closed business, lost "
     "income, benefits problems, or similar — not only those exact words. A mere refusal to pay is NOT "
     "hardship, and saying the full amount is too much is NOT hardship (that is the amounts "
     "negotiation). paid ONLY when the customer says they ALREADY paid this past-due amount; a promise "
     "to pay is not paid. Otherwise what the customer is saying, if it is one of these.",
     "hardship, müşterinin sözünü ettiği HER ciddi kişisel ya da mali sıkıntıdır: hastalık, ailede "
     "vefat, iş kaybı, karşılayamadığı bakımevi ya da tedavi masrafları, kapanan iş, gelir kaybı, "
     "yardım sorunları ya da benzerleri — yalnızca bu kelimeler değil. Sadece ödemeyi reddetmek "
     "hardship DEĞİLDİR ve tam tutarın çok olduğunu söylemek de hardship DEĞİLDİR (bu tutar "
     "görüşmesidir). paid YALNIZCA müşteri bu gecikmiş tutarı ZATEN ödediğini söylerse; ödeme vaadi "
     "paid değildir. Aksi hâlde müşterinin söylediği, bunlardan biriyse."),
    ("The current call date is {{now}}. Interpret every date the caller says (today, tomorrow, next "
     "Friday, the 20th, dates in words) relative to {{now}}, never to the real-world clock.",
     "Aramanın bugünkü tarihi {{now}}. Arayanın söylediği her tarihi (bugün, yarın, gelecek cuma, ayın "
     "20'si, kelimeyle söylenen tarihler) {{now}} tarihine göre yorumlayın, asla gerçek dünya saatine "
     "göre değil."),
]

# longest English sentence first, so a sentence that contains a shorter one is
# replaced before the shorter one can cut it up
_TR_SORTED = sorted(TR_SENTENCES, key=lambda pair: -len(pair[0]))

def localize(text, lang):
    """Rewrite the fixed English scaffolding into the brief's language (Turkish today)."""
    if not text or not is_turkish(lang):
        return text
    for en, tr in _TR_SORTED:
        if en in text:
            text = text.replace(en, tr)
    return text

# Keys whose STRING values reach the dialogue model and may hold English scaffolding.
# Everything else (executed code, variable defaults, enum values, urls) is left alone:
# generated hooks localize their own sentences where they are built, and rewriting
# code would corrupt it.
_LOC_TEXT_KEYS = ("task_message", "routing_prompt", "system_prompt", "description",
                  "extraction_prompt", "text", "prompt", "message", "when")
_LOC_SKIP_KEYS = ("pre_process_code", "post_process_code")

def localize_workflow(workflow, lang):
    """One final pass: the built workflow's model-facing text in the brief's language.

    The nodes build their Turkish text inline (or the English one when the brief is
    English); this pass catches the fixed English scaffolding that is written once
    (system prompt, tool guidance from the tool API file, extraction descriptions,
    transition descriptions). Rule sentences copied from the brief never match an
    English key and pass through untouched. An English build is returned unchanged.
    """
    if not is_turkish(lang) or not isinstance(workflow, dict):
        return workflow

    def walk(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in _LOC_SKIP_KEYS:
                    continue
                if isinstance(value, str):
                    if key in _LOC_TEXT_KEYS:
                        obj[key] = localize(value, lang)
                else:
                    walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(workflow)
    return workflow

# ---------------------------------------------------------------- rule ledger

LEDGER_TYPES = ("date_rule", "amount_rule", "closing_rule", "sequence_rule",
                "attempt_rule", "vocabulary_rule", "verbatim_rule")

def ledger_records(spec, rtype):
    """Every record of one type in the spec's rule ledger, in brief order."""
    out = []
    for rec in (spec or {}).get("rule_ledger") or []:
        if isinstance(rec, dict) and str(rec.get("type") or "").strip() == rtype:
            out.append(rec)
    return out

def ledger_params(spec, rtype):
    """Merged params of every record of one type (later records win)."""
    merged = {}
    for rec in ledger_records(spec, rtype):
        params = rec.get("params")
        if isinstance(params, dict):
            merged.update(params)
    return merged

def ledger_text(spec, rtype):
    return " ".join(str(r.get("text") or "").strip() for r in ledger_records(spec, rtype)).strip()

def ledger_by_key(spec, rtype, key, item_key="id"):
    """{item[item_key]: item} for a ledger list of dicts (mandatory sentences, verbatim items)."""
    out = {}
    for rec in ledger_records(spec, rtype):
        params = rec.get("params")
        if not isinstance(params, dict):
            continue
        for item in params.get(key) or []:
            if isinstance(item, dict) and str(item.get(item_key) or "").strip():
                out[str(item[item_key]).strip()] = item
    return out

def _as_list(value):
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []

def apply_ledger(spec):
    """Fill the spec's empty structured slots from the rule ledger (ADDITIVE).

    The structured slots stay the source of truth when the extractor filled
    them; the ledger only fills what is missing, so a brief whose extraction
    dropped a value still compiles, and a spec without a ledger is unchanged.
    """
    if not isinstance(spec, dict):
        return spec
    out = json.loads(json.dumps(spec))
    d = out.get("dates") if isinstance(out.get("dates"), dict) else {}
    dr = ledger_params(spec, "date_rule")
    if isinstance(d.get("bands"), list):
        # ledger bands may use {min,max}; the code reads days_late_min/max
        for b in d["bands"]:
            if isinstance(b, dict) and b.get("min") is not None and b.get("days_late_min") is None:
                b["days_late_min"] = b.get("min")
            if isinstance(b, dict) and b.get("max") is not None and b.get("days_late_max") is None:
                b["days_late_max"] = b.get("max")
    for slot, lkey in (("business_days", "business_days"), ("holidays", "holidays"),
                       ("bands", "bands"), ("validity_text", "valid"),
                       ("weekend_text", "weekend_holiday"), ("vague_text", "vague"),
                       ("next_weekday_text", "next_weekday"), ("over_deadline_text", "after_deadline")):
        if not d.get(slot) and dr.get(lkey):
            d[slot] = dr[lkey]
    if d:
        out["dates"] = d
    if isinstance(d.get("bands"), list):
        for b in d["bands"]:
            if isinstance(b, dict) and b.get("min") is not None and b.get("days_late_min") is None:
                b["days_late_min"] = b.get("min")
            if isinstance(b, dict) and b.get("max") is not None and b.get("days_late_max") is None:
                b["days_late_max"] = b.get("max")
    am = ledger_params(spec, "amount_rule")
    a = out.get("amounts") if isinstance(out.get("amounts"), dict) else {}
    atext = ledger_text(spec, "amount_rule")
    for slot, lkey in (("full_first_text", "full_first_text"), ("floor_text", "floor_text"),
                       ("floor_once_text", "floor_once_text"), ("range_text", "range_accept"),
                       ("below_floor_text", "below_floor")):
        if not a.get(slot) and am.get(lkey):
            a[slot] = am[lkey]
    if not a.get("below_floor_text") and atext:
        a.setdefault("below_floor_text", "")
    if a:
        out["amounts"] = a
    p = out.get("persuasion") if isinstance(out.get("persuasion"), dict) else {}
    at = ledger_params(spec, "attempt_rule")
    for slot, lkey in (("attempt1_text", "attempt1"), ("attempt2_text", "attempt2"),
                       ("stop_text", "stop")):
        if not p.get(slot) and at.get(lkey):
            p[slot] = at[lkey]
    if p:
        out["persuasion"] = p
    return out

def _split_reasons(value):
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        return [part.strip() for part in value.replace(";", ",").split(",") if part.strip()]
    return []

def closing_table(spec):
    """The closing table as [{"outcome", "reasons", "when"}].

    The rule ledger's closing_rule wins when it has a table; otherwise the
    structured closing.table of the spec is used (the pre-ledger behaviour).
    """
    rows = []
    raw = ledger_params(spec, "closing_rule").get("table")
    if isinstance(raw, list):
        for row in raw:
            if isinstance(row, dict) and str(row.get("outcome") or "").strip():
                rows.append({"outcome": str(row["outcome"]).strip(),
                             "reasons": _split_reasons(row.get("reasons") or row.get("reason")),
                             "when": str(row.get("when") or "")})
    if not rows:
        for row in (spec.get("closing") or {}).get("table") or []:
            if isinstance(row, dict) and str(row.get("outcome") or "").strip():
                rows.append({"outcome": str(row["outcome"]).strip(),
                             "reasons": _split_reasons(row.get("reason")),
                             "when": str(row.get("when") or "")})
    if not rows:
        # a spec with no closing table at all: the two outcomes that take no reason
        rows = [{"outcome": "promise", "reasons": [], "when": ""},
                {"outcome": "paid", "reasons": [], "when": ""}]
    return rows

def _find_pair(table, reason_names, outcome=None):
    """(outcome, reason with the table's own casing) of the first row carrying one of these reasons."""
    wanted = [str(r).lower() for r in reason_names]
    for row in table:
        if outcome and row["outcome"] != outcome:
            continue
        for r in row["reasons"]:
            if r.lower() in wanted:
                return row["outcome"], r
    return None, None

def compile_closing(spec):
    """The closing_rule compiled to the values the corrector mechanism runs on."""
    table = closing_table(spec)
    allowed, order = {}, []
    for row in table:
        if row["outcome"] not in allowed:
            allowed[row["outcome"]] = []
            order.append(row["outcome"])
        for r in row["reasons"]:
            if r not in allowed[row["outcome"]]:
                allowed[row["outcome"]].append(r)
    cr = ledger_params(spec, "closing_rule")
    no_reason = _split_reasons(cr.get("no_reason"))
    if not no_reason:
        no_reason = [o for o in order if not allowed[o]]
    no_reason = [o for o in no_reason if o in allowed] or ["promise", "paid"]

    tap = cr.get("transfer_after_promise")
    tap = tap if isinstance(tap, dict) else {}
    wins = tap.get("wins")
    if wins is None:
        # a brief sentence about a transfer that follows a recorded promise means
        # that transfer keeps its own outcome even after the promise was recorded
        wins = bool(str((spec.get("closing") or {}).get("transfer_after_promise_text") or "").strip())
    queues = _split_reasons(tap.get("queues"))

    qmap = {}
    raw_qmap = cr.get("transfer_reason_by_queue")
    if isinstance(raw_qmap, dict):
        for k, v in raw_qmap.items():
            if str(k).strip() and str(v).strip():
                qmap[str(k).strip().lower()] = str(v).strip()
    if not wins and not queues:
        # brief convention: a hand-off to the "general" queue closes with the
        # human reason when the table lists "human" but not "general"
        if "human" in [r.lower() for r in allowed.get("transferred", [])] \
                and "general" not in [r.lower() for r in allowed.get("transferred", [])]:
            qmap.setdefault("general", "human")

    def pair(field, reasons, fallback):
        raw_pair = cr.get(field) if isinstance(cr.get(field), dict) else {}
        o = str(raw_pair.get("outcome") or "").strip()
        r = str(raw_pair.get("reason") or "").strip()
        if o and (o in allowed):
            return o, (r or (_find_pair(table, reasons, o)[1] or ""))
        found = _find_pair(table, reasons)
        if found[0]:
            return found
        return fallback

    notes_raw = cr.get("notes") if isinstance(cr.get("notes"), dict) else {}
    notes_enabled = bool(spec.get("notes")) or bool(notes_raw.get("enabled"))
    notes_outcome = str(notes_raw.get("outcome") or "").strip()
    if notes_outcome not in allowed:
        notes_outcome = "no_promise" if "no_promise" in allowed else (_find_pair(table, ["refused"])[0] or "no_promise")
    paid_all = cr.get("paid_when_all_notes_paid")
    promise_wins = cr.get("promise_wins")
    return {
        "allowed": allowed,
        "no_reason": no_reason,
        "promise_wins": True if promise_wins is None else bool(promise_wins),
        "transfer_wins": bool(wins),
        "transfer_queues": queues,
        "queue_reasons": qmap,
        "notes_enabled": notes_enabled,
        "notes_outcome": notes_outcome,
        "paid_when_all_notes_paid": True if paid_all is None else bool(paid_all),
        "identity_fail": pair("identity_fail", ["failed"], ("not_verified", "failed")),
        "identity_decline": pair("identity_decline", ["declined"], ("not_verified", "declined")),
        "callback": pair("callback", ["callback"], ("not_reached", "callback")),
        "no_callback": pair("no_callback", ["no_callback"], ("not_reached", "no_callback")),
        "wrong_number": pair("wrong_number", ["wrong_number"], ("not_reached", "wrong_number")),
        "deceased": pair("deceased", ["deceased"], ("not_reached", "deceased")),
        "unclear": pair("unclear", ["unclear"], ("not_reached", "unclear")),
    }

CORRECTOR_BODY = '''try:
    _ALLOWED = __ALLOWED__
    _NO_REASON = __NO_REASON__
    _PROMISE_WINS = __PROMISE_WINS__
    _TRANSFER_WINS = __TRANSFER_WINS__
    _TRANSFER_QUEUES = __TRANSFER_QUEUES__
    _QUEUE_REASONS = __QUEUE_REASONS__
    _PAID_ALL = __PAID_ALL__
    _NOTES_OUTCOME = __NOTES_OUTCOME__

    def _s(v):
        return '' if v is None else str(v).strip()

    def _lc(v):
        return _s(v).lower()

    def _num(v):
        try:
            s = _s(v)
            return int(float(s)) if s else 0
        except Exception:
            return 0

    def _true(v):
        return _lc(v) in ('true', '1', 'yes', 'evet', 'ok', 'success')

    def _allowed(o):
        return [str(x) for x in (_ALLOWED.get(o) or [])]

    def _pair_ok(o, r):
        if o not in _ALLOWED:
            return False
        rs = _allowed(o)
        rl = _lc(r)
        if not rs:
            return rl in ('', 'none', 'null')
        return rl in [x.lower() for x in rs]

    def _pick(o, *prefs):
        rs = _allowed(o)
        for p in prefs:
            pl = _lc(p)
            for r in rs:
                if r.lower() == pl:
                    return r
        return rs[0] if len(rs) == 1 else None

    def _put(o, r):
        if not _pair_ok(o, r):
            return False
        b = config.get('body')
        if not isinstance(b, dict):
            b = {}
            config['body'] = b
        b['outcome'] = o
        if o in _NO_REASON or not _lc(r):
            b.pop('reason', None)
        else:
            b['reason'] = r
        return True

    def _notes():
        out = []
        seq = _s(vars.get('notes_seq'))
        if seq:
            for part in seq.split('|'):
                part = part.strip().lower()
                if part:
                    out.append(part)
        if not out:
            r = _lc(vars.get('add_note_args.reason'))
            if r:
                out.append(r)
        return out

    def _first_note(notes):
        for n in notes:
            if n != 'paid':
                return n
        return notes[0] if notes else None

    promised = _num(vars.get('create_promise_success_count')) > 0
    transfers = _num(vars.get('transfer_to_agent_success_count'))
    queue = _s(vars.get('transfer_to_agent_args.queue'))
    qlow = queue.lower()
    verified = (_true(vars.get('verify_identity_response.data.all_verified'))
                or _true(vars.get('verify_identity_response.data.verified')))
    wrong_left = _lc(vars.get('verify_identity_response.data.wrong_answers_left'))
    notes = _notes()

    def _transfer_reason():
        rs = _allowed('transferred')
        if not rs:
            return None
        mapped = _QUEUE_REASONS.get(qlow)
        if mapped and _lc(mapped) in [r.lower() for r in rs]:
            return mapped
        for r in rs:
            if r.lower() == qlow:
                return r
        return _pick('transferred')

    transfer_wins = transfers > 0 and (_TRANSFER_WINS or (qlow and qlow in [str(q).lower() for q in _TRANSFER_QUEUES]))
    done = False
    if promised and transfer_wins:
        done = _put('transferred', _transfer_reason())
    if not done and promised and _PROMISE_WINS:
        done = _put('promise', None)
    if not done and transfers > 0:
        done = _put('transferred', _transfer_reason())
    if not done and notes and _PAID_ALL and all(n == 'paid' for n in notes):
        done = _put('paid', None)
    if not done and notes:
        first = _first_note(notes)
        done = _put(_NOTES_OUTCOME, _pick(_NOTES_OUTCOME, first)) or _put(_NOTES_OUTCOME, first)
__BRANCHES__
    b = config.get('body')
    if isinstance(b, dict):
        o = _lc(b.get('outcome'))
        if o in _NO_REASON:
            b.pop('reason', None)
        elif o in _ALLOWED:
            rs = _allowed(o)
            if len(rs) == 1 and _lc(b.get('reason')) != _lc(rs[0]):
                b['reason'] = rs[0]
except Exception:
    pass
'''

def close_corrector_code(spec):
    """The close_call pre_process_code: a deterministic outcome/reason corrector.

    Generated from the closing_rule table (never hardcoded to a practice brief).
    Every branch only overwrites close_call's body when the engine's own counters
    and tool results make the outcome determinate; otherwise the model's choice
    is left untouched. The code contains no {{ }} (the engine templates those)
    and is wrapped in try/except so it can never break the end-of-call path.
    """
    cc = compile_closing(spec)
    branches = []
    checks = []
    ident_fail = cc["identity_fail"]
    if ident_fail[0]:
        checks.append(
            "    if not done and not verified and wrong_left in ('0', '0.0'):\n"
            "        done = _put(%r, _pick(%r, %r))\n" % (ident_fail[0], ident_fail[0], ident_fail[1]))
    decl = cc["identity_decline"]
    if decl[0]:
        checks.append(
            "    if not done and not verified and (_true(vars.get('identity_declined'))"
            " or _true(vars.get('declined'))):\n"
            "        done = _put(%r, _pick(%r, %r))\n" % (decl[0], decl[0], decl[1]))
    for field, flags in (("deceased", ("is_deceased", "deceased")),
                         ("wrong_number", ("is_wrong_number", "wrong_number"))):
        pair = cc[field]
        if not pair[0]:
            continue
        flag_checks = " or ".join("_true(vars.get(%r))" % f for f in flags)
        who = "'wrong_number'" if field == "wrong_number" else "'deceased'"
        checks.append(
            "    if not done and ((_lc(vars.get('who_answers')) == %s) or %s):\n"
            "        done = _put(%r, _pick(%r, %r))\n" % (who, flag_checks, pair[0], pair[0], pair[1]))
    pair = cc["callback"]
    if pair[0]:
        checks.append(
            "    if not done and _num(vars.get('schedule_callback_success_count')) > 0:\n"
            "        done = _put(%r, _pick(%r, %r))\n" % (pair[0], pair[0], pair[1]))
    pair = cc["no_callback"]
    if pair[0]:
        checks.append(
            "    if not done and (_true(vars.get('callback_declined')) or _true(vars.get('no_callback'))):\n"
            "        done = _put(%r, _pick(%r, %r))\n" % (pair[0], pair[0], pair[1]))

    code = CORRECTOR_BODY
    code = code.replace("__ALLOWED__", repr(cc["allowed"]))
    code = code.replace("__NO_REASON__", repr(cc["no_reason"]))
    code = code.replace("__PROMISE_WINS__", repr(bool(cc["promise_wins"])))
    code = code.replace("__TRANSFER_WINS__", repr(bool(cc["transfer_wins"])))
    code = code.replace("__TRANSFER_QUEUES__", repr(cc["transfer_queues"]))
    code = code.replace("__QUEUE_REASONS__", repr(cc["queue_reasons"]))
    code = code.replace("__PAID_ALL__", repr(bool(cc["paid_when_all_notes_paid"])))
    code = code.replace("__NOTES_OUTCOME__", repr(cc["notes_outcome"]))
    code = code.replace("__BRANCHES__", "".join(checks).rstrip("\n"))
    # the engine templates {{...}}: the generated Python must never contain one
    code = code.replace("{{", "{").replace("}}", "}")
    compile(code, "<close_corrector>", "exec")  # a broken corrector must never ship
    return code

def note_sequence_hook():
    """Extend the add_note post-hook: remember every note reason, in order.

    The close_call corrector reads this to close multi-product calls with the
    first non-paid note reason, in get_account order.
    """
    return """try:
    d = result.get('data')
    if isinstance(d, dict):
        if d.get('ok'):
            d['what_to_do_next'] = 'The note is recorded. Continue with the remaining products, or end the call.'
        else:
            d['what_to_do_next'] = 'The note failed. Call add_note once more, then continue or end the call.'
    _ok = d.get('ok') if isinstance(d, dict) else None
    _failed = _ok is False or str(_ok).strip().lower() == 'false'
    _r = ''
    try:
        _cb = config.get('body') if isinstance(config, dict) else None
        if isinstance(_cb, dict):
            _r = str(_cb.get('reason') or '')
    except Exception:
        _r = ''
    if not _r:
        _r = str(vars.get('add_note_args.reason') or '')
    _r = _r.strip().lower()
    if _r and not _failed:
        _seq = vars.get('notes_seq')
        _seq = _seq if isinstance(_seq, str) else ''
        if _seq.count('|') < 20:
            vars['notes_seq'] = (_seq + '|' + _r) if _seq else _r
except Exception:
    pass
"""


def bool_group(variable, operands=("true", "True")):
    return {"logic": "or", "conditions": [
        {"variable": variable, "operator": "equals", "operand": o} for o in operands]}

def cond(var, op, operand):
    return {"logic": "or", "conditions": [{"variable": var, "operator": op, "operand": operand}]}

def cond_is_set(var):
    return {"logic": "or", "conditions": [{"variable": var, "operator": "is_set"}]}

def always():
    return {"operator": "always"}

def trans(target, description, condition):
    return {"target_node": target, "description": description, "condition": condition}

def self_trans(description="Keep going"):
    return {"target_node": None, "description": description, "condition": always()}  # target filled by caller

def mock_base_url(api=None):
    """The mock base URL the tools must post to, or "" for the tool API file's own server.

    Read in this order (the first non-empty wins):
      1. builder.build.MOCK_URL   - set by build.py's case-folder CLI form
      2. the MOCK_URL env var     - so a subprocess or a plain import also sees it
      3. api["mock_url"]          - belt and braces, written by build.py
    """
    candidates = []
    build_mod = sys.modules.get("builder.build")
    if build_mod is not None:
        candidates.append(getattr(build_mod, "MOCK_URL", None))
    candidates.append(os.environ.get("MOCK_URL"))
    if isinstance(api, dict):
        candidates.append(api.get("mock_url"))
    for c in candidates:
        if c is not None and str(c).strip():
            return str(c).strip().rstrip("/")
    return ""

def api_tool(api, path, guidance, response_mapping=None, max_retries=0,
             pre_process_code=None, post_process_code=None, always_runs_at=None,
             body_defaults=None):
    """One bank API call as a Freya function object, fields taken from the tool API file.

    The URL is the tool API file's server plus the path; when a mock base URL is
    set (see ``mock_base_url``) the URL is that base plus the same path instead,
    so one built workflow can be pointed at our own mock without editing the API file.
    """
    op = api["paths"][path]["post"]
    mock = mock_base_url(api)
    url = (mock + path) if mock else (api["servers"][0]["url"] + path)
    schema = op["requestBody"]["content"]["application/json"]["schema"]
    props = {}
    for fname, fspec in schema.get("properties", {}).items():
        leaf = {}
        if "type" in fspec:
            leaf["type"] = fspec["type"]
        if "enum" in fspec:
            leaf["enum"] = fspec["enum"]
        if "description" in fspec:
            leaf["description"] = fspec["description"]
        # customer_id is baked from the call variable; every other field the model fills.
        # The {{var}} default is what makes the model fill it — without a default the
        # model sends nothing (proven by the 0/10 identity run). The editor's
        # "will not resolve" warning for these is noise.
        if fname == "customer_id":
            leaf["default"] = "{{customer_id}}"
        elif body_defaults and fname in body_defaults:
            leaf["default"] = body_defaults[fname]
        else:
            leaf["default"] = "{{" + fname + "}}"
        props[fname] = leaf
    required = [r for r in schema.get("required", []) if r != "customer_id"]
    body = {"type": "object", "properties": props}
    if required:
        body["required"] = required
    tool = {
        "type": "function",
        "config": {"timeoutMs": 12000, "maxRetries": max_retries},
        "function": {
            "name": path.lstrip("/"),
            "handler": "__function__:api_call",
            "description": guidance,
            "parameters": {"type": "object", "properties": {
                "url": {"type": "string", "default": url},
                "method": {"type": "string", "default": "POST"},
                "headers": {"type": "object", "properties": {
                    "Content-Type": {"type": "string", "default": "application/json"}}},
                "body": body,
            }},
        },
    }
    if always_runs_at:
        tool["config"]["alwaysRunsAt"] = always_runs_at
    if response_mapping:
        tool["response_mapping"] = response_mapping
    if pre_process_code:
        tool["pre_process_code"] = pre_process_code
    if post_process_code:
        tool["post_process_code"] = post_process_code
    return tool

# The extraction model anchors relative dates (today, next Friday...) on the REAL
# clock, but every call has its own `now`. Without this prompt the extractor turns
# "today" into the real world date and the whole date pipeline shifts.
EXTRACT_DATE_ANCHOR = ("The current call date is {{now}}. Interpret every date the caller says "
    "(today, tomorrow, next Friday, the 20th, dates in words) relative to {{now}}, never to the real-world clock.\n\n"
    "{{extractor.speech}}\n\n{{extractor.type_preamble}}\n\n{{extractor.variables_list}}\n\n"
    "{{extractor.conversation.last-10}}")

END_CALL_TOOL = {
    "type": "function",
    "config": {"timeoutMs": 10000},
    "function": {
        "name": "end_call",
        "handler": "__function__:end_call",
        "parameters": {"type": "object", "properties": {
            "message_mode": {"type": "string", "default": "none"},
            "interruptible": {"type": "boolean", "default": True},
            "trigger_pattern": {"type": "string", "default": "Have a good day|have a good day"},
            "trigger_timeout": {"type": "number", "default": 3},
            "trigger_pattern_both": {"type": "string",
                                     "default": "goodbye|bye|have a good day|you too|thank you|thanks|take care"},
        }},
        "description": "Ends the call. You normally do NOT call this: the phrase \"Have a good day.\" ends the call by itself. Call it without any text only if the customer answers after your goodbye.",
    },
}

def end_call_tool(lang="English"):
    """END_CALL_TOOL with the goodbye phrase and its trigger patterns in the brief's language."""
    if not is_turkish(lang):
        return END_CALL_TOOL
    tool = json.loads(json.dumps(END_CALL_TOOL))
    props = tool["function"]["parameters"]["properties"]
    props["trigger_pattern"]["default"] = "İyi günler|iyi günler"
    props["trigger_pattern_both"]["default"] = ("görüşürüz|hoşça kal|iyi günler|teşekkürler|teşekkür ederim|"
                                                "kendine iyi bak")
    tool["function"]["description"] = localize(END_CALL_TOOL["function"]["description"], lang)
    return tool

VERIFY_HOOK = """try:
    d = result.get('data')
    if isinstance(d, dict):
        if d.get('hint') == 'day_month_swapped':
            d['what_to_do_next'] = 'Tell the customer to say the month as a word, then call verify_identity again with the new answer.'
        elif d.get('verified') or d.get('all_verified'):
            d['what_to_do_next'] = 'This answer passed. Move to the next security question, or continue the call if all questions passed.'
        elif d.get('wrong_answers_left') is not None and str(d['wrong_answers_left']) == '0':
            d['what_to_do_next'] = 'The identity check failed. Tell the customer to use the mobile app or a branch, then end the call.'
        else:
            d['what_to_do_next'] = 'Tell the customer the answer was wrong and ask the same question again.'
except Exception:
    pass
"""

PROMISE_HOOK = """try:
    d = result.get('data')
    if isinstance(d, dict):
        if d.get('ok'):
            d['what_to_do_next'] = 'Say the promise is recorded and the text-message sentence. Then continue with any remaining product, or end the call.'
        else:
            d['what_to_do_next'] = 'The recording failed. Call create_promise once more. If it fails again, tell the customer it could not be recorded and end the call.'
except Exception:
    pass
"""

# Multi-product: the engine bakes one {{fixed_date}} for every create_promise call.
# This hook rewrites the date per product from fixed_date_p<id>, which carries each
# product's own deadline-clamped date, so "one date for everything" records the
# earlier-deadline product on its own deadline.
PROMISE_DATE_HOOK = """try:
    b = config.get('body')
    if isinstance(b, dict) and b.get('product_id'):
        f = 'fixed_date_' + str(b.get('product_id'))
        if vars.get(f):
            b['date'] = vars[f]
except Exception:
    pass
"""

NOTE_HOOK = """try:
    d = result.get('data')
    if isinstance(d, dict):
        if d.get('ok'):
            d['what_to_do_next'] = 'The note is recorded. Continue with the remaining products, or end the call.'
        else:
            d['what_to_do_next'] = 'The note failed. Call add_note once more, then continue or end the call.'
except Exception:
    pass
"""

# After a transfer the model sometimes goes silent ("no speakable content") and
# the customer is left hanging. This hook tells it exactly what to say.
TRANSFER_HOOK = """try:
    d = result.get('data')
    if isinstance(d, dict):
        d['what_to_do_next'] = 'Say you are connecting them to the right team now, then end the call by saying goodbye ending with "Have a good day."'
except Exception:
    pass
"""

def closing_descriptions(spec, lang="English"):
    """Outcome and reason guidance for the close_call tool, from the closing table
    (the rule ledger's closing_rule when it has one, else the structured table)."""
    table = closing_table(spec)
    lines = []
    reasons_by_outcome = {}
    no_reason = []
    for row in table:
        o, rs, when = row["outcome"], row["reasons"], row["when"]
        if rs:
            reasons_by_outcome.setdefault(o, []).extend(r for r in rs if r not in reasons_by_outcome.get(o, []))
        elif o not in no_reason:
            no_reason.append(o)
        r_text = ", ".join(rs)
        lines.append(f"{o}: {when}" + (f" (reason: {r_text})" if r_text else ""))
    outcome_desc = "How the call ended. " + " ".join(lines)
    reason_lines = []
    for o, rs in reasons_by_outcome.items():
        if rs:
            reason_lines.append(f"for {o}: one of " + ", ".join(rs))
    reason_desc = "Required for every outcome except " + ", ".join(no_reason) + ". " + " ".join(reason_lines)
    return localize(outcome_desc, lang), localize(reason_desc, lang), no_reason

def close_call_tool(api, spec, lang="English"):
    """The end_of_call close_call tool, with the deterministic corrector as its pre-hook.

    The corrector is generated from the closing_rule table: it recomputes the
    outcome and reason from the engine's counters and tool results and overwrites
    the model's proposal when the evidence is determinate.
    """
    outcome_desc, reason_desc, no_reason = closing_descriptions(spec, lang)
    tool = api_tool(api, "/close_call",
                    localize("Record how the call ended. The platform calls it automatically when "
                             "the call ends.", lang),
                    always_runs_at=["end_of_call"])
    body = tool["function"]["parameters"]["properties"]["body"]
    body["properties"]["outcome"]["description"] = outcome_desc
    if "reason" in body["properties"]:
        body["properties"]["reason"]["description"] = reason_desc
    tool["pre_process_code"] = close_corrector_code(spec)
    return tool

def conv_node(name, task_message, tools, extraction_schema, transitions, on_enter=None, routing_prompt=None):
    node = {
        "name": name,
        "node_type": "conversation",
        "task_message": task_message,
        "max_node_turns": 80,
        "on_enter": on_enter if on_enter else {"type": "llm"},
        "on_enter_first_entry_only": True,
        "extraction_schema": extraction_schema,
        "tools": tools,
        "transitions": transitions,
    }
    if routing_prompt:
        node["routing_prompt"] = routing_prompt
    return node

def api_node(name, tool, mapping, next_node):
    return {
        "name": name,
        "node_type": "api_request",
        "passthrough": True,
        "passthrough_default_transition": next_node,
        "on_enter": {"type": "silent"},
        "pre_actions": [tool],
        "response_mapping": mapping,
        "transitions": [trans(next_node, "always", always())],
    }

def code_node(name, code, next_node):
    return {
        "name": name,
        "node_type": "code",
        "passthrough": True,
        "passthrough_default_transition": next_node,
        "on_enter": {"type": "silent"},
        "pre_actions": [{
            "type": "function",
            "function": {
                "name": "code_exec",
                "handler": "__function__:code_exec",
                "parameters": {"type": "object", "properties": {
                    "code": {"type": "string", "default": code},
                    "timeout_ms": {"type": "number", "default": 30000},
                }},
            },
        }],
        "transitions": [trans(next_node, "always", always())],
    }

def _date_fragments(lang):
    """Words the date code writes into variables the dialogue model reads mid-call.

    English reproduces byte-for-byte what the code always wrote (so an English
    build is unchanged); a Turkish brief gets Turkish fragments, keeping the
    facts of the call in the brief's language. Values are Python source snippets,
    injected into the code template at __L_*__ tokens.
    """
    tr = is_turkish(lang)
    return {
        "L_CC": "'kredi kartı ' + str(p.get('card_last4') or '')" if tr
                else "'credit card ending ' + str(p.get('card_last4') or '')",
        "L_PL": "'bireysel kredi'" if tr else "'personal loan'",
        "L_CL": "'taşıt kredisi'" if tr else "'car loan'",
        "L_PASTDUE": "' gecikmiş tutar, '" if tr else "' past due, '",
        "L_DALATE": "' gün gecikme'" if tr else "' days late'",
        "L_FLOOR": "', taban tutar '" if tr else "', floor '",
        "L_LATEST": "', en son tarih '" if tr else "', latest date '",
        "L_NODATA": "'Hesap verisi yok.'" if tr else "'No account data.'",
        "L_READDATA": "'Hesap verisini araç sonucundan okuyun.'" if tr
                      else "'Read the account data from the tool result.'",
        "L_NONE": "'yok'" if tr else "'none'",
        "L_TODAY": "' (bugün)'" if tr else "' (today)'",
        "L_NAMES": ("['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']" if tr
                    else "['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']"),
        "L_TODAYNAME": "' (' + names[today.weekday()] + ')'" if tr
                       else "' (' + today.strftime('%A') + ')'",
        "L_REL": "'Müşteri göreli bir tarih söyledi; düzeltilmiş tarih '" if tr
                 else "'The customer said a relative date; the corrected date is '",
        "L_WKND": ("'Müşterinin söylediği tarih hafta sonu ya da banka tatili. Bunun yerine '" if tr
                   else "'The date the customer named is a weekend day or a bank holiday. Offer '"),
        "L_WKND2": "' tarihini teklif edin ve o tarihi kaydedin.'" if tr
                   else "' instead and record that date.'",
        "L_PASTLATE": ("'Söylenen tarih bazı ürünlerin en son tarihini geçiyor. Şunları kendi son "
                       "tarihlerine kaydedin: '" if tr
                       else "'The named date is past the latest date of some products. Record '"),
        "L_PASTLATE2": "' ve bunu geri okumada söyleyin.'" if tr
                       else "' on their own deadlines and say so in the read-back.'",
        "L_AFTER": ("'Müşterinin söylediği tarih en son tarihten sonra. Söylenen tarihle "
                    "create_promise ÇAĞIRMAYIN. Kaydedebileceğiniz en son tarih '" if tr
                    else "'The date the customer named is after the latest date. Do NOT call "
                         "create_promise with the named date. Say the latest date you can record is '"),
        "L_AFTER2": "' ve onu teklif edin.'" if tr else "' and offer it.'",
    }

def dates_code(spec, lang="English"):
    """Business-day facts the collect prompt needs: per-product deadlines, floors, attempt dates.

    Built with replace tokens so the generated Python contains no {{ }} (the engine
    templates those).
    """
    holidays = json.dumps(spec.get("dates", {}).get("holidays", []))
    bands = json.dumps(spec.get("dates", {}).get("bands", []))
    code = """import json, datetime
try:
    HOL = json.loads('__HOL__')
    BANDS = json.loads('__BANDS__')
    def is_biz(d):
        return d.weekday() < 5 and d.isoformat() not in HOL
    def add_biz(d, n):
        d = d + datetime.timedelta(days=1)
        while True:
            if is_biz(d):
                n = n - 1
                if n == 0:
                    return d
            d = d + datetime.timedelta(days=1)
    def last_biz(d):
        end = d + datetime.timedelta(days=(6 - d.weekday()))
        while not is_biz(end):
            end = end - datetime.timedelta(days=1)
        return end
    now = str(vars.get('now') or '')[:10]
    today = datetime.date.fromisoformat(now) if now else datetime.date.today()
    p_raw = vars.get('products')
    if isinstance(p_raw, str):
        p_raw = json.loads(p_raw) if p_raw.strip() else None
    if isinstance(p_raw, dict):
        p_raw = p_raw.get('products') or p_raw.get('items')
    if not isinstance(p_raw, list) or not p_raw:
        # the platform flattens the account result as account_response.data.products.<i>.<field>;
        # rebuild the product list from those keys (values arrive as strings)
        p_raw = []
        for i in range(3):
            pid = vars.get('account_response.data.products.' + str(i) + '.product_id')
            if not pid:
                continue
            p = {}
            for f in ('product_id', 'type', 'card_last4', 'past_due', 'days_late', 'minimum_payment', 'instalment_amount'):
                v = vars.get('account_response.data.products.' + str(i) + '.' + f)
                if v is not None:
                    p[f] = v
            p_raw.append(p)
    texts, infos = [], []
    for i, p in enumerate(p_raw[:3], start=1):
        if not isinstance(p, dict):
            continue
        pid = p.get('product_id') or ('p' + str(i))
        ptype = str(p.get('type') or 'product')
        if ptype == 'credit_card':
            label = __L_CC__
        elif ptype == 'personal_loan':
            label = __L_PL__
        elif ptype == 'car_loan':
            label = __L_CL__
        else:
            label = ptype
        days_late = p.get('days_late')
        try:
            days_late = int(float(days_late))
        except Exception:
            days_late = 0
        floor = p.get('minimum_payment')
        if floor is None:
            floor = p.get('instalment_amount')
        try:
            floor = float(floor)
        except Exception:
            floor = None
        deadline, attempts = None, 1
        for b in BANDS:
            lo = b.get('days_late_min')
            hi = b.get('days_late_max')
            if lo is not None and hi is not None and lo <= days_late <= hi:
                if b.get('business_day'):
                    deadline = add_biz(today, int(b['business_day']))
                if b.get('persuasion_attempts'):
                    attempts = int(b['persuasion_attempts'])
                break
        t = pid + ' (' + label + '): ' + str(p.get('past_due')) + __L_PASTDUE__ + str(days_late) + __L_DALATE__
        if floor is not None:
            t = t + __L_FLOOR__ + str(floor)
        if deadline is not None:
            t = t + __L_LATEST__ + deadline.isoformat()
        texts.append(t)
        infos.append({'pid': pid, 'deadline': deadline.isoformat() if deadline else '',
                      'floor': floor, 'attempts': attempts})
    a1 = last_biz(today)
    if a1 <= today:
        a1 = last_biz(today + datetime.timedelta(days=7))
    # weekday semantics, so "next Friday" and "this Saturday" resolve to exact dates
    names = __L_NAMES__
    this_monday = today - datetime.timedelta(days=today.weekday())
    this_w = []
    next_w = []
    for i, nm in enumerate(names):
        tw = this_monday + datetime.timedelta(days=i)
        nw = tw + datetime.timedelta(days=7)
        this_w.append(nm + ' ' + tw.isoformat() + (__L_TODAY__ if tw == today else ''))
        next_w.append(nm + ' ' + nw.isoformat())
    vars['this_week_days'] = ', '.join(this_w)
    vars['next_week_days'] = ', '.join(next_w)
    vars['p_count'] = str(len(infos))
    for i, inf in enumerate(infos, start=1):
        vars['p' + str(i) + '_text'] = texts[i - 1]
        vars['p' + str(i) + '_deadline'] = inf['deadline']
        vars['p' + str(i) + '_floor'] = '' if inf['floor'] is None else str(inf['floor'])
        vars['p' + str(i) + '_attempts'] = str(inf['attempts'])
    vars['products_text'] = chr(10).join(texts) if texts else __L_NODATA__
    vars['attempt1'] = a1.isoformat()
    vars['today_text'] = today.isoformat() + __L_TODAYNAME__
    vars['holiday_text'] = ', '.join(HOL) if HOL else __L_NONE__
except Exception:
    vars['p_count'] = '0'
    vars['products_text'] = __L_READDATA__
    for k in ('attempt1', 'today_text', 'holiday_text'):
        vars[k] = ''
    for i in range(1, 4):
        for s in ('text', 'deadline', 'floor', 'attempts'):
            vars.setdefault('p' + str(i) + '_' + s, '')
""".replace("__HOL__", holidays).replace("__BANDS__", bands)
    for _token, _fragment in _date_fragments(lang).items():
        code = code.replace("__" + _token + "__", _fragment)
    return code

def fix_date_code(spec, lang="English"):
    """Validate the extracted payment date and bake the corrected one into fixed_date.

    Weekend/holiday -> next business day (mechanical). Past the product deadline ->
    date_ok is set to false with a message; the model must offer the deadline.
    Clears payment_date afterwards so the check runs once per customer answer.
    """
    holidays = json.dumps(spec.get("dates", {}).get("holidays", []))
    return """import json, datetime
try:
    HOL = json.loads('__HOL__')
    raw = str(vars.get('payment_date') or '')[:10]
    vars['date_ok'] = 'true'
    vars.pop('payment_date', None)
    # IMPORTANT: when no fresh date was extracted (e.g. the customer only confirmed),
    # keep the previous fixed_date — clearing it makes the model invent a date.
    if raw:
        vars.pop('fixed_date', None)
        vars.pop('date_msg', None)
        d = datetime.date.fromisoformat(raw)
        now = str(vars.get('now') or '')[:10]
        call_today = datetime.date.fromisoformat(now) if now else None
        if call_today is not None and d < call_today:
            # the extraction model anchored on the real clock: shift by the offset
            # between the real day and the call's day, so "today" and "tomorrow"
            # land on the call's today and tomorrow
            real_now = str(vars.get('system.iso_utc_now') or '')[:10]
            if real_now:
                real_today = datetime.date.fromisoformat(real_now)
                d = d + (call_today - real_today)
            else:
                d = call_today
            vars['date_msg'] = 'The customer said a relative date; the corrected date is ' + d.isoformat() + '.'
        if d.weekday() >= 5 or d.isoformat() in HOL:
            while d.weekday() >= 5 or d.isoformat() in HOL:
                d = d + datetime.timedelta(days=1)
            vars['fixed_date'] = d.isoformat()
            vars['date_msg'] = 'The date the customer named is a weekend day or a bank holiday. Offer ' + d.isoformat() + ' instead and record that date.'
        else:
            vars['fixed_date'] = d.isoformat()
        deadlines = [vars.get('p' + str(i) + '_deadline') for i in range(1, 4)]
        deadlines = [x for x in deadlines if x]
        if len(deadlines) >= 2:
            # one date for everything: a product whose deadline is earlier than the
            # named date is recorded on its own deadline (multi-product rule).
            # Do NOT block the whole date: the per-product clamp below handles it.
            moved = []
            for i in range(1, 4):
                dl = vars.get('p' + str(i) + '_deadline')
                if not dl:
                    continue
                dd = datetime.date.fromisoformat(dl)
                fixed = d if d <= dd else dd
                if fixed != d:
                    moved.append('p' + str(i) + ' on ' + fixed.isoformat())
                vars['fixed_date_p' + str(i)] = fixed.isoformat()
            if moved:
                vars['date_msg'] = ('The named date is past the latest date of some products. Record '
                                    + ', '.join(moved) + ' on their own deadlines and say so in the read-back.')
        elif deadlines and d.isoformat() > max(deadlines):
            vars['date_ok'] = 'false'
            # the only recordable date is the deadline the model is about to offer;
            # bake it so a spoken acceptance cannot record the rejected date
            vars['fixed_date'] = max(deadlines)
            vars['date_msg'] = 'The date the customer named is after the latest date. Do NOT call create_promise with the named date. Say the latest date you can record is ' + max(deadlines) + ' and offer it.'
except Exception:
    vars.pop('payment_date', None)
    vars['date_ok'] = 'true'
""".replace("__HOL__", holidays)

def first_line(text):
    return (text or "").strip().splitlines()[0] if (text or "").strip() else ""

def build_workflow(spec, api):
    spec = apply_ledger(spec)          # the rule ledger fills empty structured slots
    bank = spec.get("bank_name", "the bank")
    language = brief_language(spec)
    lang = language
    products_max = int(spec.get("products", {}).get("max", 1) or 1)
    end_call = end_call_tool(lang)

    closing = spec.get("closing", {})
    closing_table_text = "\n".join(
        f"- {r['outcome']}" + (f" / {', '.join(r['reasons'])}" if r["reasons"] else "") + f": {r['when']}"
        for r in closing_table(spec))
    speak_line = ("Siz " + bank + " adına tahsilat aramasını yürüten dijital asistansınız. "
                  + speak_name(language) + " konuşun. ") if is_turkish(lang) else (
                  f"You are the digital assistant of {bank} on a collection call. Speak {language}. ")
    system_prompt = (
        speak_line +
        "One or two short sentences per turn. "
        "Never tell the customer something is recorded when a tool call failed. "
        "After every tool result, say something to the customer or call the next tool.\n"
        "Now: {{now}}.\n\n"
        "How the call ends (recorded automatically when the call ends):\n" + closing_table_text +
        "\nDisambiguation: not_verified is ONLY for security-check endings after the questions were asked "
        "(failed = wrong answers, declined = refusal to answer). not_reached is for calls where the right "
        "person was never confirmed or never engaged: if no security question was ever answered, the call "
        "is not_reached with reason unclear — never not_verified.")

    # ---- tools from the tool API file
    verify = api_tool(api, "/verify_identity",
        "Check one security answer. CALL it once for each answer the customer gives.",
        post_process_code=localize(VERIFY_HOOK, lang))
    get_account = api_tool(api, "/get_account",
        "The customer's late products. CALL it once, before you say anything about the account.",
        max_retries=2)
    promise = api_tool(api, "/create_promise",
        "Record a payment promise. CALL it only after the customer said yes to the read-back of amount and date. "
        "The date is filled in for you from what the customer agreed.",
        post_process_code=localize(PROMISE_HOOK, lang), body_defaults={"date": "{{fixed_date}}"},
        pre_process_code=PROMISE_DATE_HOOK if products_max > 1 else None)
    transfer = api_tool(api, "/transfer_to_agent",
        "Hand the call to a person. CALL it with the queue the rule says.",
        post_process_code=localize(TRANSFER_HOOK, lang))
    callback = api_tool(api, "/schedule_callback",
        "Book a callback. CALL it only after the customer agreed a day and time inside the window.")
    close = close_call_tool(api, spec, lang)
    collect_tools = [get_account, promise, transfer, end_call]
    note_tool = None
    if spec.get("notes") and "/add_note" in api.get("paths", {}):
        note_tool = api_tool(api, "/add_note",
            "Record why a product ended without a promise. CALL it once per product without a promise.",
            post_process_code=localize(note_sequence_hook(), lang))
        collect_tools.insert(1, note_tool)

    # ---- opening node
    op = spec.get("opening", {})
    # rule ledger, vocabulary_rule: the words forbidden before identity, and the
    # never-ask phrases, compiled into the prompts that can violate them
    vocab = ledger_params(spec, "vocabulary_rule")
    verbatim = ledger_by_key(spec, "verbatim_rule", "items", item_key="where")
    mandatory = ledger_by_key(spec, "vocabulary_rule", "mandatory_sentences", item_key="id")
    forbidden = _as_list(vocab.get("forbidden_before_identity"))
    never_ask = _as_list(vocab.get("never_ask")) + _as_list(ledger_params(spec, "amount_rule").get("never_ask"))
    op_extra = " ".join(filter(None, [
        first_line(op.get("forbidden_text")), first_line(op.get("confirm_words_text")),
        first_line(op.get("second_ask_text")), first_line(op.get("unclear_text")),
        first_line(op.get("robot_text")), first_line(op.get("scam_text"))]))
    forbidden_line = ""
    if forbidden:
        forbidden_line = ("Never say these words or anything about them before the identity is verified: "
                          + ", ".join(filter(None, (str(w).strip() for w in forbidden))) + ".") if not is_turkish(lang) else (
                          "Kimlik doğrulanmadan önce şu kelimeleri ya da onlarla ilgili hiçbir şeyi söylemeyin: "
                          + ", ".join(filter(None, (str(w).strip() for w in forbidden))) + ".")
    default_greeting = ("Merhaba, ben " + bank + " dijital asistanı. {{title}} {{last_name}} ile mi görüşüyorum?") \
        if is_turkish(lang) else ("Hello, this is the digital assistant of " + bank
                                  + ". Am I speaking with {{title}} {{last_name}}?")
    greeting = op.get("greeting") or verbatim.get("greeting", {}).get("text") or default_greeting
    opening = conv_node(
        "opening",
        f"You just started the call. Say nothing about collections, debt, payment or any product before the identity is verified.\n"
        f"{op_extra}\n"
        + (forbidden_line + "\n" if forbidden_line else "") +
        "If someone other than the customer answered, do not say why you are calling. Say nothing beyond the greeting.\n"
        "When the call must end, say goodbye ending with \"Have a good day.\"",
        [end_call],
        [{"name": "who_answers", "type": "string", "min_confidence": 0.7,
          "enum_values": ["target", "relative", "wrong_number", "deceased", "unclear"],
          "description": "Who is on the line after the greeting: target is the customer themself."}],
        [],
        on_enter={"type": "tts", "text": greeting.replace("{title}", "{{title}}").replace("{last_name}", "{{last_name}}")},
        routing_prompt="Route to identity when the customer themself confirmed. Any other answer routes to the third-party callback questions.")

    # ---- third-party node
    tp = spec.get("third_party", {})
    tr = is_turkish(lang)
    def close_str(o):
        if not isinstance(o, dict) or not o.get("outcome"):
            return "?"
        return o["outcome"] + (("/" + o["reason"]) if o.get("reason") else "")
    tp_lines = ["Someone other than the customer answered, or it is unclear who is on the line. "
                "Do not say why the bank is calling. Say nothing about any account. "
                "GROUNDING: never invent a name, number or detail the caller did not give you."]
    if tp.get("wrong_number_close"):
        if tr:
            tp_lines.append("Yalnızca kişi numaranın müşteriye ait olmadığını açıkça söylerse "
                            + close_str(tp["wrong_number_close"]) + " olarak kapatın. Bu kapanışı başka bir şey için kullanmayın.")
        else:
            tp_lines.append("Only if the person literally says the number does not belong to the customer, "
                            "close as " + close_str(tp["wrong_number_close"]) + ". Do not use this close for anything else.")
    if tp.get("deceased_close"):
        loss_line = str(tp.get("deceased_line") or verbatim.get("deceased", {}).get("text")
                        or mandatory.get("sympathy", {}).get("text") or "I am sorry for your loss.")
        if tr:
            tp_lines.append("Kişi müşterinin vefat ettiğini söylerse \"" + loss_line + "\" deyin, "
                            "başka hiçbir şey sormayın ve " + close_str(tp["deceased_close"]) + " olarak kapatın.")
        else:
            tp_lines.append(("If the person says the customer has died, say \"" + loss_line + "\", "
                             "ask nothing else, and close as " + close_str(tp["deceased_close"]) + "."))
    tp_lines.append(("Aksi hâlde müşteriye ne zaman ulaşılabileceğini sorun. " if tr
                     else "Otherwise ask when the customer can be reached. ") + first_line(tp.get("callback_window_text", "")))
    if tr:
        tp_lines.append("Gün ya da saat pencere dışındaysa bir kez başka bir zaman isteyin. O da pencere dışındaysa "
                        "randevu oluşturmayın ve " +
                        close_str(tp.get("no_callback_close") or {"outcome": "not_reached", "reason": "no_callback"}) + " olarak kapatın.")
        tp_lines.append("Geçerli bir gün ve saat üzerinde anlaşılırsa schedule_callback aracını bunlarla ÇAĞIRIN ve " +
                        close_str(tp.get("callback_close") or {"outcome": "not_reached", "reason": "callback"}) + " olarak kapatın.")
    else:
        tp_lines.append("If the day or the time is outside the window, ask once for another time. "
                        "If that is also outside it, do not schedule and close as " +
                        close_str(tp.get("no_callback_close") or {"outcome": "not_reached", "reason": "no_callback"}) + ".")
        tp_lines.append("If a valid day and time are agreed, CALL schedule_callback with them and close as " +
                        close_str(tp.get("callback_close") or {"outcome": "not_reached", "reason": "callback"}) + ".")
    if tp.get("unclear_text"):
        tp_lines.append(first_line(tp["unclear_text"]))
    tp_lines.append("To end the call, say goodbye ending with \"Have a good day.\"")
    third_party = conv_node(
        "third_party",
        "\n".join(l for l in tp_lines if l.strip()),
        [callback, end_call],
        [{"name": "situation", "type": "string", "min_confidence": 0.7,
          "enum_values": ["relative", "wrong_number", "deceased", "callback_agreed", "callback_refused"],
          "description": "What the person on the line said."},
         {"name": "callback_date", "type": "date", "min_confidence": 0.8,
          "extraction_prompt": EXTRACT_DATE_ANCHOR,
          "description": "The day the person named for a callback."},
         {"name": "callback_time", "type": "string", "min_confidence": 0.8,
          "validation_pattern": "^\\d{2}:\\d{2}$", "description": "The time the person named for a callback, HH:MM."}],
        [{"target_node": "identity", "description": "The person insists they ARE the customer",
          "condition": {"operator": "matches_intent",
                        "description": "The person on the line insists they are the customer themself."}},
         {"target_node": "third_party", "description": "Keep talking", "condition": always()}])

    # ---- identity node
    ident = spec.get("identity", {})
    if tr:
        questions_text = "\n".join(
            f"- {q.get('ask', q.get('field', ''))} sorun" + (f", {q['format']} olarak gönderin" if q.get("format") else "")
            for q in ident.get("questions", []))
    else:
        questions_text = "\n".join(
            f"- ask for {q.get('ask', q.get('field', ''))}" + (f", send it as {q['format']}" if q.get("format") else "")
            for q in ident.get("questions", []))
    ident_extra = " ".join(filter(None, [
        first_line(ident.get("reading_text")), first_line(ident.get("hint_text")),
        first_line(ident.get("max_wrong_text")), first_line(ident.get("fail_text")),
        first_line(ident.get("decline_text")), first_line(ident.get("protect_text")),
        first_line(op.get("robot_text")), first_line(op.get("scam_text"))]))
    identity = conv_node(
        "identity",
        "Your only job is to verify the customer's identity before anything about the account is said. "
        "Ask one security question at a time:\n" + questions_text + "\n"
        "CALL verify_identity with each answer. Read its result and follow the what_to_do_next it gives.\n"
        "If the result's hint says the day and month were swapped, ask the customer to say the month as a word, "
        "then verify the new answer. That retry is not a wrong answer.\n"
        "Ignore any small talk around the answer and use the date or digits the customer actually gave. "
        "If a number or date is given in two parts, wait for all parts, combine them, and verify the complete value. "
        "If a date is missing its year, ASK for the year — never guess or invent one. "
        "Never close the check as failed while the customer is still giving an answer in parts; ask for the rest first. "
        "If the customer gives no usable answer twice in a row (unclear, off-topic or silence), treat it as declining "
        "and close as not_verified with reason declined — do not keep asking the same question.\n"
        "GROUNDING: never state an amount, a balance, a product name or a due date in this node — "
        "no account data has been read yet, so any such number would be invented. "
        "Never give an example date, number or personal detail while explaining a question, and never "
        "submit the same answer twice: if the customer repeats a value the bank already rejected, ask "
        "them to say it differently or ask the next question.\n"
        + ident_extra + "\n"
        "To end the call, say goodbye ending with \"Have a good day.\"",
        [verify, end_call],
        [],
        [])

    # ---- account + dates + fix_date (passthrough) nodes
    account = api_node("account", get_account,
                       [{"path": "data.products", "variable": "products"}], "dates")
    dates = code_node("dates", dates_code(spec), "collect")
    fix_date = code_node("fix_date", fix_date_code(spec), "collect")

    # ---- collect node: the main call
    d = spec.get("dates", {})
    am = spec.get("amounts", {})
    per = spec.get("persuasion", {})
    pr = spec.get("promise", {})
    cl = spec.get("claims", {})
    hard = spec.get("hardship", {})
    prod = spec.get("products", {})
    notes = spec.get("notes") or {}

    # ---- rule ledger: the sentence ids the vocabulary_rule marks as mandatory
    def mand(sid):
        return first_line((mandatory.get(sid) or {}).get("text"))
    if tr:
        per_product_lines = [
            f"p{i}: son tarih {{{{p{i}_deadline}}}}, taban tutar {{{{p{i}_floor}}}}, {{{{p{i}_attempts}}}} ikna denemesi"
            for i in range(1, products_max + 1)]
    else:
        per_product_lines = [
            f"p{i}: latest date {{{{p{i}_deadline}}}}, floor {{{{p{i}_floor}}}}, {{{{p{i}_attempts}}}} persuasion attempts"
            for i in range(1, products_max + 1)]
    per_product_text = "\n".join(per_product_lines)
    seq_steps = _as_list(ledger_params(spec, "sequence_rule").get("steps")) or _as_list(
        ledger_params(spec, "sequence_rule").get("texts"))

    sections = []
    sections.append("The account, from get_account:\n{{products_text}}\n\n"
                    "Today: {{today_text}}. Bank holidays: {{holiday_text}}. Now: {{now}}.")
    if products_max > 1:
        sections.append("Several products: " + first_line(prod.get("state_all_text", "")))
    sections.append("Stating the debt: " + first_line(prod.get("state_text", "")) +
                    "\nYour first sentence about the debt MUST name the product, the past-due amount and the "
                    "number of days late, all from {{products_text}} — never skip any of the three.")
    if products_max > 1:
        sections.append("Going through the products: " + " ".join(filter(None, [
            first_line(prod.get("today_ask_text")), first_line(prod.get("order_text")),
            first_line(prod.get("one_date_text")), first_line(prod.get("read_back_together_text")),
            first_line(prod.get("attempts_per_product_text"))])))
    sections.append("Per-product facts (from the bank):\n" + per_product_text +
                    "\nEach product has its OWN latest date: do not apply one product's deadline to another. "
                    "A date past one product's latest date is still fine for a product whose latest date is later. "
                    "Make exactly the listed number of attempts for each product, never more.")
    sections.append("Dates: " + " ".join(filter(None, [
        first_line(d.get("validity_text")), first_line(d.get("weekend_text")),
        first_line(d.get("vague_text")), first_line(d.get("next_weekday_text")),
        first_line(d.get("over_deadline_text"))])))
    sections.append("Weekday names mean these exact dates:\n"
                    "this week: {{this_week_days}}\n"
                    "next week: {{next_week_days}}\n"
                    "When the customer says 'next Friday', use the next-week Friday from that list, never this week's.")
    sections.append("The date check says: {{date_msg}}. The date to record in create_promise is filled in for you "
                    "as {{fixed_date}}. If the check says the date cannot be recorded, do NOT call create_promise with it; "
                    "offer the latest date instead. When the date check MOVES the customer's date (weekend, holiday or "
                    "deadline), always read back the MOVED date and wait for a fresh yes before recording — never record "
                    "a date the customer has not confirmed.")
    sections.append("Amounts: " + " ".join(filter(None, [
        first_line(am.get("full_first_text")), first_line(am.get("floor_text")),
        first_line(am.get("floor_once_text")), first_line(am.get("range_text")),
        first_line(am.get("below_floor_text"))])) +
        "\nWhen you offer the floor, always say that the rest of the balance stays overdue. "
        "Whenever the recorded amount is below the full amount — whether you offered it or the "
        "customer proposed it — say that the rest of the balance stays overdue. "
        + (('Say exactly this sentence when the amount is below the full amount: "' + mand("rest_overdue")
            + '" ') if mand("rest_overdue") else "")
        + "Offer the floor AT MOST ONCE; if it is refused, treat it as a flat refusal. "
        "NEVER ask the customer how much they can pay: you propose every amount."
        + ((" Asla sormayın: " + "; ".join(never_ask) + ".") if never_ask and tr else
           ((" Never ask any of these: " + "; ".join(never_ask) + ".") if never_ask else "")))
    sections.append("Persuasion: " + " ".join(filter(None, [
        first_line(per.get("attempt1_text")), f"Attempt 1 proposes {{{{attempt1}}}}.",
        first_line(per.get("attempt2_text")), first_line(per.get("stop_text")),
        first_line(per.get("never_repeat_text"))])) +
        "\nA flat refusal uses the attempts in order: attempt 1 first (the FULL amount on {{attempt1}}, "
        "the last business day of this week), and attempt 2 only when the band allows it (the floor on the "
        "latest date). Never skip to attempt 2 before attempt 1 was made. NEVER repeat an amount-and-date "
        "offer the customer already refused; if the floor was already offered and refused, make no further "
        "offer and close as refused.")
    sections.append("Hardship: " + " ".join(filter(None, [
        first_line(hard.get("sympathy_text")), first_line(hard.get("support_text")),
        first_line(hard.get("decline_text")), first_line(hard.get("beats_persuasion_text"))])) +
        "\nWhen hardship is mentioned (illness, a death in the family, job loss): say exactly ONE short sentence "
        "of sympathy, then make NO persuasion attempt. Offer the support team once. If they accept, call "
        "transfer_to_agent with the support queue. If they decline, close without a promise. A date or amount "
        "the customer names themselves is still recorded."
        + ((' Say the sympathy sentence exactly ONCE, never twice: "' + mand("sympathy") + '".')
           if mand("sympathy") else ""))
    claims_text = " ".join(filter(None, [
        first_line(cl.get("paid_text")), first_line(cl.get("dispute_text")),
        first_line(cl.get("restructuring_text")), first_line(cl.get("human_text")),
        first_line(cl.get("scam_text")), first_line(cl.get("dont_know_text")),
        first_line(cl.get("dont_want_text"))]))
    if claims_text:
        sections.append("What customers say: " + claims_text +
                        "\nA claim that THIS past-due amount was already paid — however the customer says it "
                        "(in the app, by card, online, yesterday) — means close paid, no promise, even when the "
                        "customer asks when the payment shows up. "
                        "A claim that the product is not theirs or was closed long ago means dispute. "
                        "When transferring for restructuring, say only that you will connect them with the "
                        "restructuring team — never describe or promise an instalment plan, lower instalments "
                        "or any new terms.")
    sms_sentence = mand("sms")
    sections.append("Recording a promise: " + " ".join(filter(None, [
        first_line(pr.get("read_back_text")), first_line(pr.get("confirm_text")),
        first_line(pr.get("retry_text")), first_line(pr.get("sms_text")),
        first_line(pr.get("one_per_product_text"))])) +
        "\nNever call create_promise without the customer's clear yes to the read-back. "
        + (('After a recorded promise say exactly this sentence: "' + sms_sentence + '" ') if sms_sentence else "")
        + "GROUNDING: say ONLY numbers, dates and product names that appear in the tool results. "
        "If a number is not in the results, do not say it. Never claim a capability the bank's "
        "tools do not have (no instalment plans, no waivers, no transfers the rules do not name).")
    if note_tool:
        sections.append("Notes: " + " ".join(filter(None, [
            first_line(notes.get("when_text")), first_line(notes.get("reasons_text")),
            first_line(notes.get("transfer_note_text"))])) +
            "\nBefore ending the call, CALL add_note for EVERY product that ended without a promise, "
            "with the reason the notes rules say.")
    order_line = ""
    if seq_steps:
        order_line = (" Tool order from the brief: " + "; ".join(seq_steps) + ".") if not tr else (
            " Brief'in araç sırası: " + "; ".join(seq_steps) + ".")
    sections.append("Ending the call: " + first_line(closing.get("goodbye_text", "")) +
                    " Say goodbye ending with \"Have a good day.\" The close outcome is recorded automatically from the rules above — "
                    "you do NOT call close_call yourself, it is not available to you. "
                    "A date or an amount the customer proposes is NEVER a refusal: respond to that value under the "
                    "date and amount rules, and do not count it as one of your persuasion attempts. "
                    "Before closing as refused, make sure the customer has had the chance to name their own amount or date. "
                    "After a refusal, do NOT say goodbye in the same turn: give the customer one more turn to speak "
                    "before you close." + order_line)

    collect_task = ("You are on a collection call. The customer's identity is verified.\n\n"
                    + "\n\n".join(s for s in sections if s.strip()))

    note_reasons = notes.get("reasons", [])
    collect = conv_node(
        "collect",
        collect_task,
        collect_tools,
        [{"name": "payment_date", "type": "date", "min_confidence": 0.85,
          "extraction_prompt": EXTRACT_DATE_ANCHOR,
          "description": "The payment date the CUSTOMER named in their own words. Never take a date that only the assistant said (for example from a read-back); when the customer only confirms, leave it unset."},
         {"name": "payment_amount", "type": "float", "min_confidence": 0.8,
          "description": "The payment amount the customer agreed to, if any."},
         {"name": "claim", "type": "string", "min_confidence": 0.7,
          "enum_values": ["none", "paid", "dispute", "hardship", "restructuring", "human", "scam", "dont_know", "dont_want"],
          "description": "hardship is ANY serious personal or financial trouble the customer mentions: illness, a death in the family, job loss, care-home or medical fees they cannot afford, a closed business, lost income, benefits problems, or similar — not only those exact words. A mere refusal to pay is NOT hardship, and saying the full amount is too much is NOT hardship (that is the amounts negotiation). paid ONLY when the customer says they ALREADY paid this past-due amount; a promise to pay is not paid. Otherwise what the customer is saying, if it is one of these."},
         {"name": "confirmation", "type": "string", "min_confidence": 0.7,
          "enum_values": ["none", "yes", "no"], "description": "The customer's answer to the read-back confirmation."},
         {"name": "note_reason", "type": "string", "min_confidence": 0.7,
          "enum_values": note_reasons, "description": "Why a product ended without a promise."},
        ] if note_reasons else [{"name": "payment_date", "type": "date", "min_confidence": 0.85,
          "extraction_prompt": EXTRACT_DATE_ANCHOR,
          "description": "The payment date the CUSTOMER named in their own words. Never take a date that only the assistant said (for example from a read-back); when the customer only confirms, leave it unset."},
         {"name": "payment_amount", "type": "float", "min_confidence": 0.8,
          "description": "The payment amount the customer agreed to, if any."},
         {"name": "claim", "type": "string", "min_confidence": 0.7,
          "enum_values": ["none", "paid", "dispute", "hardship", "restructuring", "human", "scam", "dont_know", "dont_want"],
          "description": "hardship is ANY serious personal or financial trouble the customer mentions: illness, a death in the family, job loss, care-home or medical fees they cannot afford, a closed business, lost income, benefits problems, or similar — not only those exact words. A mere refusal to pay is NOT hardship, and saying the full amount is too much is NOT hardship (that is the amounts negotiation). paid ONLY when the customer says they ALREADY paid this past-due amount; a promise to pay is not paid. Otherwise what the customer is saying, if it is one of these."},
         {"name": "confirmation", "type": "string", "min_confidence": 0.7,
          "enum_values": ["none", "yes", "no"], "description": "The customer's answer to the read-back confirmation."}],
        [{"target_node": "collect", "description": "Keep going", "condition": always()}])

    # ---- hardship node: a real branch, not just prompt text. The collect
    # extraction sets claim='hardship'; this node consumes it.
    hardship_node = conv_node(
        "hardship",
        "The customer is going through hardship. Say exactly ONE short sentence of sympathy, then make NO "
        "persuasion attempt at all. Offer the customer support team ONCE: if they accept, CALL "
        "transfer_to_agent with the support queue and end the call; if they decline, end the call without "
        "a promise. If the customer names a payment date or amount themselves, still record it under the "
        "date and amount rules — CALL create_promise after the read-back and a clear yes. "
        "If a promise was already read back and confirmed, CALL create_promise IMMEDIATELY, before any "
        "other talk — a confirmed promise must always be recorded. Never say goodbye in a way that "
        "implies a promise was recorded when create_promise was not called.\n"
        "To end the call, say goodbye ending with \"Have a good day.\"",
        [transfer, promise, end_call],
        [{"name": "payment_date", "type": "date", "min_confidence": 0.85,
          "extraction_prompt": EXTRACT_DATE_ANCHOR,
          "description": "The payment date the CUSTOMER named in their own words, if any."},
         {"name": "confirmation", "type": "string", "min_confidence": 0.7,
          "enum_values": ["none", "yes", "no"], "description": "The customer's answer to the support-team offer."}],
        [{"target_node": "hardship", "description": "Keep talking", "condition": always()}])

    # ---- identity cap: an unanswered/unclear caller must not be asked forever
    identity_timeout = conv_node(
        "identity_timeout",
        "The customer never gave a usable security answer after several attempts. Do not ask again. "
        "Close the call as not_verified with reason declined: say goodbye ending with \"Have a good day.\"",
        [end_call],
        [],
        [{"target_node": "identity_timeout", "description": "Keep talking", "condition": always()}])

    nodes = {}
    for node in (opening, third_party, identity, account, dates, fix_date, collect, hardship_node, identity_timeout):
        nodes[node["name"]] = node

    # fill the self-transitions' targets and wire the routing ones
    opening["transitions"] = [
        trans("identity", "The customer themself confirmed", cond("who_answers", "equals", "target")),
        trans("third_party", "A relative answered", cond("who_answers", "equals", "relative")),
        trans("third_party", "Wrong number", cond("who_answers", "equals", "wrong_number")),
        trans("third_party", "The customer has died", cond("who_answers", "equals", "deceased")),
        # "unclear" falls through here: stay and ask once more (rule 3)
        trans("opening", "Keep asking", always()),
    ]
    identity["max_node_turns"] = 12
    identity["max_turn_transition"] = "identity_timeout"
    identity["transitions"] = [
        trans("account", "Both security answers verified",
              bool_group("verify_identity_response.data.all_verified")),
        trans("third_party", "The person now denies knowing the account or says it is a wrong number",
              {"operator": "matches_intent",
               "description": "The person denies having this account or loan, or says the number is wrong or belongs to someone else."}),
        trans("identity", "Keep asking", always()),
    ]
    collect["transitions"] = [
        trans("hardship", "The customer mentions hardship in their latest message",
              {"operator": "matches_intent",
               "description": "The customer's latest message describes hardship: illness, a death in the family, "
                              "job loss, care-home or medical fees, a closed business, lost income, or similar "
                              "serious trouble. A plain yes, a confirmation, or a payment date is NEVER hardship."}),
        trans("fix_date", "The customer named a payment date", cond_is_set("payment_date")),
        trans("collect", "Keep going", always()),
    ]
    hardship_node["transitions"] = [
        trans("collect", "The customer declines support and wants to continue the payment conversation",
              {"operator": "matches_intent",
               "description": "The customer declines the support team and wants to keep talking about paying, "
                              "or names an amount or a date themselves."}),
        trans("fix_date", "The customer named a payment date", cond_is_set("payment_date")),
        trans("hardship", "Keep talking", always()),
    ]

    workflow = {
        "initial_node": "opening",
        "system_prompt": system_prompt,
        "nodes": nodes,
        "global_nodes": {},
        "tools": [close],
        "test_variables": {
            "customer_id": "c_test", "first_name": "Daniel", "last_name": "Reyes",
            "title": "Mr", "now": "2026-10-14T11:00",
        },
    }
    return workflow
