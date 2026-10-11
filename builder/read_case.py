"""Read a case folder (the final package) into one text blob for the extractor.

The final input form of the builder is a single case folder — the unzipped
package: Markdown, Word (.docx), PDF and Excel (.xlsx) files (BRIEF.md, README.md,
analysis, flow drawing, announcements, service contract, test customers, Q&A, six
example conversations; Turkish).  This module turns that folder into text.  No
LLM, no network: pure functions, and every file is read defensively, so one
corrupt file (or one missing optional library) never kills the whole read.

API
---
    read_case_folder(folder) -> {"files":    [{"name": str, "text": str}, ...],
                                 "combined": str,
                                 "skipped":  [{"name": str, "reason": str}, ...]}

        folder may also be the .zip itself; it is then extracted into the default
        case directory first.

    unzip_case(zip_path, dest_dir=DEFAULT_CASE_DIR) -> pathlib.Path

        Stdlib zipfile extraction.  Zip-slip safe (members that would land outside
        dest_dir are skipped), symlinks and macOS junk (__MACOSX, .DS_Store, ._*)
        are skipped.  Returns the directory that actually holds the package: the
        single top-level folder when the zip wrapped everything in one, else
        dest_dir.  The default extraction target is the local directory `case/`.

By extension
------------
    .md .txt .markdown .csv .tsv .json .yml .yaml   read as text (UTF-8, cp1254 fallback)
    .docx   paragraphs, tables, headers/footers via python-docx
    .pdf    page text via pypdf
    .xlsx   cell values as text rows via openpyxl (" | " between cells)
    other   skipped, with a note in "skipped" and in "combined"

The three optional libraries are imported lazily, so a Markdown-only folder needs
none of them:  pip install python-docx openpyxl pypdf
"""
import datetime
import pathlib
import shutil
import stat
import sys
import zipfile

DEFAULT_CASE_DIR = pathlib.Path("case")

# read directly as text; everything else is binary/unknown by default
TEXT_EXTS = {".md", ".markdown", ".txt", ".csv", ".tsv", ".json", ".yml", ".yaml"}

__all__ = ["read_case_folder", "unzip_case", "DEFAULT_CASE_DIR", "TEXT_EXTS"]


# --------------------------------------------------------------------------- #
# one file -> text
# --------------------------------------------------------------------------- #

def _read_text(path):
    """File bytes decoded as text; Turkish packages are often cp1254, not UTF-8."""
    data = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp1254"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _read_docx(path):
    try:
        import docx  # python-docx
    except ImportError as e:
        raise RuntimeError("python-docx is not installed — pip install python-docx") from e
    d = docx.Document(str(path))
    parts = [p.text for p in d.paragraphs]
    for i, table in enumerate(d.tables, 1):
        parts.append(f"[table {i}]")
        for row in table.rows:
            parts.append(" | ".join(c.text.strip() for c in row.cells))
    seen = set()
    for section in d.sections:
        for hf in (section.header, section.footer):
            for p in hf.paragraphs:
                if p.text.strip() and p.text not in seen:
                    seen.add(p.text)
                    parts.append("[header/footer] " + p.text)
    return "\n".join(parts)


def _read_pdf(path):
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise RuntimeError("pypdf is not installed — pip install pypdf") from e
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            pass
    pages = []
    for i, page in enumerate(reader.pages, 1):
        try:
            text = (page.extract_text() or "").strip()
        except Exception as e:  # one broken page must not lose the rest of the pdf
            text = f"[unreadable page {i}: {e}]"
        pages.append(f"[page {i}]\n{text}")
    return "\n\n".join(pages)


def _cell_text(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))  # 100.0 -> 100 in text rows
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat(sep=" ") if isinstance(value, datetime.datetime) else value.isoformat()
    return str(value).replace("\n", " ").strip()


def _xlsx_text(path, data_only):
    """Cell values to text rows; returns (text, number of non-empty cells)."""
    try:
        import openpyxl
    except ImportError as e:
        raise RuntimeError("openpyxl is not installed — pip install openpyxl") from e
    wb = openpyxl.load_workbook(filename=str(path), read_only=True, data_only=data_only)
    try:
        parts, cells = [], 0
        for ws in wb.worksheets:
            lines = [f"[sheet: {ws.title}]"]
            for row in ws.iter_rows(values_only=True):
                vals = [_cell_text(v) for v in row]
                if any(vals):
                    lines.append(" | ".join(vals).rstrip(" |"))
                    cells += sum(1 for v in vals if v)
            parts.append("\n".join(lines))
        return "\n\n".join(parts), cells
    finally:
        wb.close()


def _read_xlsx(path):
    text, cells = _xlsx_text(path, data_only=True)
    if not cells:
        # a workbook saved without cached formula results reads empty with
        # data_only=True; fall back to the formulas themselves
        text2, cells2 = _xlsx_text(path, data_only=False)
        if cells2 > cells:
            return text2
    return text


def _looks_binary(path):
    try:
        with open(path, "rb") as fh:
            return b"\x00" in fh.read(4096)
    except OSError:
        return True


def _skip_reason(path):
    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    ext = path.suffix.lower() or "(no extension)"
    kind = "binary" if _looks_binary(path) else "unrecognised format"
    return f"{kind} {ext} file, {size} bytes"


def _read_file(path):
    """Return (text, None) when readable, else (None, reason to skip a binary/unknown)."""
    ext = path.suffix.lower()
    if ext in TEXT_EXTS:
        return _read_text(path), None
    if ext == ".docx":
        return _read_docx(path), None
    if ext == ".pdf":
        return _read_pdf(path), None
    if ext == ".xlsx":
        return _read_xlsx(path), None
    return None, _skip_reason(path)


# --------------------------------------------------------------------------- #
# the whole folder
# --------------------------------------------------------------------------- #

def read_case_folder(folder):
    """Read every file under `folder` into {"files", "combined", "skipped"}.

    Files are read one by one; on any failure (corrupt file, missing optional
    library, unreadable encoding) the file lands in "skipped" with the reason and
    the rest of the folder is still read.  "combined" is every readable file as
    `=== relative/path ===` sections, plus a SKIPPED FILES note when anything was
    skipped, joined with blank lines — the text the extractor consumes.
    """
    src = pathlib.Path(folder)
    if src.is_file() and src.suffix.lower() == ".zip":
        src = unzip_case(src, DEFAULT_CASE_DIR)
    if not src.is_dir():
        raise FileNotFoundError(f"case folder not found: {src}")

    files, skipped, parts = [], [], []
    paths = sorted((p for p in src.rglob("*") if p.is_file()),
                   key=lambda p: str(p.relative_to(src)).lower())
    for path in paths:
        rel = path.relative_to(src).as_posix()
        try:
            text, reason = _read_file(path)
        except Exception as e:
            text, reason = None, f"error: {type(e).__name__}: {e}"
        if text is None:
            skipped.append({"name": rel, "reason": reason})
            continue
        files.append({"name": rel, "text": text})
        parts.append(f"=== {rel} ===\n{text}")
    if skipped:
        note = ["=== SKIPPED FILES (no extractable text) ==="]
        note += [f"{s['name']} — {s['reason']}" for s in skipped]
        parts.append("\n".join(note))
    return {"files": files, "combined": "\n\n".join(parts), "skipped": skipped}


# --------------------------------------------------------------------------- #
# zip
# --------------------------------------------------------------------------- #

def _zip_member_is_junk(name):
    base = pathlib.PurePosixPath(name).name
    return (name.startswith("__MACOSX/") or "/__MACOSX/" in name
            or base in (".DS_Store", "Thumbs.db") or base.startswith("._"))


def unzip_case(zip_path, dest_dir=DEFAULT_CASE_DIR):
    """Extract a case .zip into `dest_dir` (default: the local directory `case/`).

    Extraction is zip-slip safe: any member that would land outside `dest_dir` is
    skipped with a warning on stderr, as are symlinks and macOS metadata files.
    Existing files with the same names are overwritten; nothing else in `dest_dir`
    is touched.  Returns the directory that holds the package — the zip's single
    top-level folder when it wrapped everything in one, else `dest_dir` itself.
    """
    src = pathlib.Path(zip_path)
    if not src.is_file():
        raise FileNotFoundError(f"case zip not found: {src}")
    if not zipfile.is_zipfile(str(src)):
        raise ValueError(f"not a zip file: {src}")
    dest = pathlib.Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    root = dest.resolve()
    with zipfile.ZipFile(str(src)) as zf:
        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            if not name or name.endswith("/") or _zip_member_is_junk(name):
                continue
            if stat.S_ISLNK(info.external_attr >> 16):
                print(f"skipping symlink in zip: {name}", file=sys.stderr)
                continue
            target = (dest / name).resolve()
            if target != root and root not in target.parents:
                print(f"skipping unsafe zip member: {name}", file=sys.stderr)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as fsrc, open(target, "wb") as fdst:
                shutil.copyfileobj(fsrc, fdst)
    entries = [p for p in dest.iterdir() if not p.name.startswith(".")]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return dest
