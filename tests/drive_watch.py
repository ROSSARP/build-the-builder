#!/usr/bin/env python3
"""Watch / mirror the PUBLIC final-case Google Drive folder.

Stdlib only (urllib). Companion skill: .claude/skills/case-watch/SKILL.md

CLI:
    python3 tests/drive_watch.py list                 # print the current tree
    python3 tests/drive_watch.py sync --once          # one sync pass
    python3 tests/drive_watch.py sync                 # sync, then poll every 120s

The bank adds documents to the folder during the first hour of the window, so
run `sync` (poll mode) under the harness Monitor and re-check before finishing.

Manifest: <dest_root>/.manifest.json  ->  {file_or_folder_id: {name, kind, size, ...}}
Sync never deletes local files. One failure per file is a "FAIL: <name> <reason>"
line, never a crash.
"""

from __future__ import annotations

import argparse
import html as html_mod
import http.cookiejar
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

FOLDER_ID = os.environ.get("FINALCASE_DRIVE_ID", "1r9KOek3SXiE0mu1wBofezD0bjiAJhcYQ")
DEFAULT_DEST = os.environ.get("FINALCASE_DEST", "finalcase")
POLL_INTERVAL = int(os.environ.get("FINALCASE_POLL", "120"))

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

EMBED_URL = "https://drive.google.com/embeddedfolderview?id={fid}#list"
EMBED_URL_NOHASH = "https://drive.google.com/embeddedfolderview?id={fid}"
EMBED_URL_GRID = "https://drive.google.com/embeddedfolderview?id={fid}#grid"
UC_URL = "https://drive.google.com/uc?export=download&id={fid}"

MAX_DEPTH = 12

# ---------------------------------------------------------------- HTTP layer

_opener = None


def _http():
    """Cookie-aware opener (the uc confirm flow uses a cookie / form token)."""
    global _opener
    if _opener is None:
        jar = http.cookiejar.CookieJar()
        _opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(jar)
        )
    return _opener


def _get(url, headers=None, timeout=60):
    hdrs = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    return _http().open(req, timeout=timeout)


# ---------------------------------------------------------------- parsing

_ENTRY_START_RE = re.compile(r'<div[^>]*class="flip-entry"', re.I)
_ENTRY_ID_RE = re.compile(r'id="entry-([A-Za-z0-9_-]{5,})"', re.I)
_FILE_URL_RE = re.compile(
    r'(?:drive|docs)\.google\.com/file/d/([A-Za-z0-9_-]{10,})', re.I
)
_FOLDER_URL_RE = re.compile(
    r'drive\.google\.com/drive/(?:u/\d+/)?folders/([A-Za-z0-9_-]{10,})', re.I
)
_OPEN_ID_RE = re.compile(
    r'drive\.google\.com/(?:open|uc)\?[^"\'\s>]*?\bid=([A-Za-z0-9_-]{10,})', re.I
)
_TITLE_RE = re.compile(
    r'<div[^>]*class="flip-entry-title"[^>]*>(.*?)</div>', re.I | re.S
)
_ANCHOR_RE = re.compile(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
_FOLDER_ICON_RE = re.compile(r"application/vnd\.google-apps\.folder", re.I)


def _clean_name(raw):
    text = re.sub(r"<[^>]+>", "", raw or "")
    text = html_mod.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _id_kind_from_block(block):
    """Return (file_id, kind) or (None, None) for one slice of HTML."""
    m = _FOLDER_URL_RE.search(block)
    if m:
        return m.group(1), "folder"
    m = _FILE_URL_RE.search(block)
    if m:
        return m.group(1), "file"
    m = _OPEN_ID_RE.search(block)
    if m:
        kind = "folder" if _FOLDER_ICON_RE.search(block) else "file"
        return m.group(1), kind
    m = _ENTRY_ID_RE.search(block)
    if m:
        kind = "folder" if _FOLDER_ICON_RE.search(block) else "file"
        return m.group(1), kind
    return None, None


def parse_entries(html_text):
    """Parse embeddedfolderview HTML -> [{id, name, kind}], deduped by id."""
    found = {}
    order = []

    # Split on the start of every flip-entry <div>; each slice is one entry.
    starts = [m.start() for m in _ENTRY_START_RE.finditer(html_text)]
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(html_text)
        block = html_text[start:end]
        fid, kind = _id_kind_from_block(block)
        if not fid:
            continue
        tm = _TITLE_RE.search(block)
        name = _clean_name(tm.group(1)) if tm else ""
        if fid not in found:
            found[fid] = {"id": fid, "name": name or "untitled", "kind": kind}
            order.append(fid)
        elif found[fid]["name"] == "untitled" and name:
            found[fid]["name"] = name

    # Fallback: no flip-entry blocks -> scan every anchor that points at Drive.
    if not found:
        for m in _ANCHOR_RE.finditer(html_text):
            href, inner = m.group(1), m.group(2)
            fid, kind = _id_kind_from_block(href)
            if not fid:
                continue
            name = _clean_name(inner)
            if fid not in found:
                found[fid] = {
                    "id": fid,
                    "name": name or "untitled",
                    "kind": kind,
                }
                order.append(fid)
            elif found[fid]["name"] == "untitled" and name:
                found[fid]["name"] = name

    return [found[i] for i in order]


def _fetch_folder_html(folder_id):
    """Fetch the embedded folder view; retry alternate endpoint forms if empty."""
    last_err = None
    for url in (
        EMBED_URL.format(fid=folder_id),
        EMBED_URL_NOHASH.format(fid=folder_id),
        EMBED_URL_GRID.format(fid=folder_id),
    ):
        try:
            with _get(url) as r:
                data = r.read().decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001 - try the next form
            last_err = exc
            continue
        if data.strip():
            return data
        last_err = RuntimeError("empty response body")
    raise RuntimeError(f"folder view unavailable for {folder_id}: {last_err}")


# ---------------------------------------------------------------- list_drive


def list_drive(folder_id, recursive=True):
    """Return a flat tree: [{id, name, kind: file|folder, parent}, ...].

    `parent` is the id of the containing folder (the requested folder_id for
    top-level entries). Recurses into subfolders, dedupes by id.
    """
    out = []
    visited = set()
    seen_ids = set()

    def walk(fid, parent, depth):
        if fid in visited or depth > MAX_DEPTH:
            return
        visited.add(fid)
        try:
            html_text = _fetch_folder_html(fid)
        except Exception as exc:  # noqa: BLE001 - surface as a warning, keep going
            print(f"WARN: cannot list folder {fid}: {exc}", file=sys.stderr, flush=True)
            return
        for entry in parse_entries(html_text):
            if entry["id"] in seen_ids:
                continue  # dedupe: first occurrence wins
            seen_ids.add(entry["id"])
            node = {
                "id": entry["id"],
                "name": entry["name"],
                "kind": entry["kind"],
                "parent": parent,
            }
            out.append(node)
            if recursive and entry["kind"] == "folder" and entry["id"] not in visited:
                walk(entry["id"], entry["id"], depth + 1)

    walk(folder_id, folder_id, 0)
    return out


def tree_paths(tree, root_id):
    """Map id -> relative mirror path (posix), using the parent chain."""
    nodes = {n["id"]: n for n in tree}

    def rel_path(node):
        parts = [node["name"]]
        cur = node
        seen = {node["id"]}
        while cur.get("parent") and cur["parent"] != root_id:
            parent = nodes.get(cur["parent"])
            if not parent or parent["id"] in seen:
                break
            seen.add(parent["id"])
            parts.append(parent["name"])
            cur = parent
        return "/".join(reversed(parts))

    return {n["id"]: rel_path(n) for n in tree}


def _safe_rel(rel):
    """Sanitize a mirror-relative path; never escape the destination root."""
    parts = []
    for seg in str(rel).replace("\\", "/").split("/"):
        seg = seg.strip()
        if seg in ("", ".", ".."):
            continue
        seg = seg.replace("\x00", "_")
        parts.append(seg)
    return "/".join(parts) or "untitled"


# ---------------------------------------------------------------- download

_MARKERS = (
    'id="download-form"',
    "drive.usercontent.google.com/download",
    "Virus scan warning",
    "Quota exceeded",
    "you can't view or download",
    "Access denied",
    "You need permission",
    "confirm=",
)


def _is_interstitial(ctype, head):
    """True when the first bytes look like a Drive interstitial/error page."""
    ctype = (ctype or "").lower()
    snippet = head[:4096].decode("utf-8", "replace")
    is_html = "text/html" in ctype or "<html" in snippet[:400].lower() or "<!doctype html" in snippet[:400].lower()
    if not is_html:
        return False
    return any(m in snippet for m in _MARKERS)


def _html_reason(body):
    low = body.lower()
    if "quota exceeded" in low or "too many users" in low:
        return "quota exceeded by Google Drive"
    if "access denied" in low or "need permission" in low or "request access" in low:
        return "permission denied (access request required)"
    if "sign in" in low:
        return "sign-in required"
    if "virus scan warning" in low or "download-form" in low:
        return "download-confirm page could not be followed"
    if "you can't view or download" in low:
        return "Google Drive refused the download"
    m = re.search(r"<title>(.*?)</title>", body, re.I | re.S)
    title = _clean_name(m.group(1)) if m else ""
    return f"unexpected HTML response{(': ' + title) if title else ''}"


def _confirm_url(html_text, base_url, file_id):
    """Build the follow-up URL for the virus-scan confirm page, or None."""
    m = re.search(
        r'<form[^>]*\baction="([^"]+)"[^>]*>(.*?)</form>', html_text, re.I | re.S
    )
    if m:
        action = html_mod.unescape(m.group(1))
        fields = []
        for tag in re.findall(r"<input\b[^>]*>", m.group(2), re.I):
            nm = re.search(r'\bname="([^"]*)"', tag, re.I)
            if not nm:
                continue
            vm = re.search(r'\bvalue="([^"]*)"', tag, re.I)
            fields.append(
                (
                    html_mod.unescape(nm.group(1)),
                    html_mod.unescape(vm.group(1)) if vm else "",
                )
            )
        if fields and any(k == "confirm" for k, _ in fields):
            if action.startswith("/"):
                action = urllib.parse.urljoin(base_url, action)
            qs = urllib.parse.urlencode(fields)
            return action + ("&" if "?" in action else "?") + qs
    m = re.search(r"\bconfirm=([0-9A-Za-z_\-]+)", html_text)
    if m:
        return UC_URL.format(fid=file_id) + "&confirm=" + m.group(1)
    return None


def _stream_response(resp, tmp_path, first=b""):
    cl = resp.headers.get("Content-Length")
    expected = None
    if cl is not None and getattr(resp, "status", 200) == 200:
        try:
            expected = int(cl)
        except ValueError:
            expected = None
    got = 0
    with open(tmp_path, "wb") as fh:
        if first:
            fh.write(first)
            got += len(first)
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            fh.write(chunk)
            got += len(chunk)
    if expected is not None and got != expected:
        raise RuntimeError(f"truncated download ({got}/{expected} bytes)")
    return got


def _fetch_to(file_id, tmp_path, timeout=180):
    """Download file_id to tmp_path. Follows the virus-scan confirm page."""
    url = UC_URL.format(fid=file_id)
    resp = _get(url, timeout=timeout)
    try:
        ctype = resp.headers.get("Content-Type", "")
        head = resp.read(4096)
        if _is_interstitial(ctype, head):
            body = (head + resp.read()).decode("utf-8", "replace")
            confirm = _confirm_url(body, resp.geturl(), file_id)
            if not confirm:
                raise RuntimeError(_html_reason(body))
            resp2 = _get(confirm, timeout=timeout)
            try:
                head2 = resp2.read(4096)
                if _is_interstitial(resp2.headers.get("Content-Type", ""), head2):
                    body2 = (head2 + resp2.read()).decode("utf-8", "replace")
                    raise RuntimeError(_html_reason(body2))
                return _stream_response(resp2, tmp_path, first=head2)
            finally:
                resp2.close()
        return _stream_response(resp, tmp_path, first=head)
    finally:
        resp.close()


def download_file(file_id, dest, timeout=180):
    """Download one Drive file to `dest` (atomically). Returns size in bytes."""
    dest = os.path.abspath(dest)
    parent = os.path.dirname(dest)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp = _tmp_path(dest)
    try:
        size = _fetch_to(file_id, tmp, timeout=timeout)
        os.replace(tmp, dest)
        return size
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        raise


def remote_size(file_id, timeout=30):
    """Remote file size, or None when it cannot be established cheaply."""
    try:
        with _get(UC_URL.format(fid=file_id), headers={"Range": "bytes=0-0"}, timeout=timeout) as r:
            cr = r.headers.get("Content-Range", "")
            if "/" in cr:
                try:
                    return int(cr.rsplit("/", 1)[1])
                except ValueError:
                    pass
            if getattr(r, "status", None) == 200:
                ctype = (r.headers.get("Content-Type") or "").lower()
                cl = r.headers.get("Content-Length")
                head = r.read(64)
                if cl is not None and not _is_interstitial(ctype, head):
                    try:
                        return int(cl)
                    except ValueError:
                        pass
    except Exception:  # noqa: BLE001 - size probe is best-effort
        pass
    return None


# ---------------------------------------------------------------- sync

MANIFEST_NAME = ".manifest.json"


def _tmp_path(dest):
    """Per-process temp path so two concurrent syncs never share a .part file."""
    return f"{dest}.{os.getpid()}.part"


def _load_manifest(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return data
    except FileNotFoundError:
        pass
    except Exception as exc:  # noqa: BLE001 - corrupt manifest must not kill sync
        print(f"WARN: manifest unreadable ({exc}); starting fresh", file=sys.stderr, flush=True)
    return {}


def _save_manifest(path, manifest):
    # Merge with any concurrent writer's records (sync never deletes anything).
    for key, value in _load_manifest(path).items():
        manifest.setdefault(key, value)
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)


def _sync_one_file(entry, rel, dest, old):
    """Sync a single file. Returns 'new' | 'changed' | 'same'."""
    dest = os.path.abspath(dest)
    stale_name = bool(old) and old.get("name") != entry["name"]
    old_size = old.get("size") if old else None
    old_is_file = bool(old) and old.get("kind") == "file"

    if old_is_file and not stale_name and old_size is not None and os.path.exists(dest):
        if remote_size(entry["id"]) == old_size:
            return "same"

    parent = os.path.dirname(dest)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp = _tmp_path(dest)
    try:
        size = _fetch_to(entry["id"], tmp)
        if old_is_file and not stale_name and size == old_size and os.path.exists(dest):
            os.remove(tmp)
            return "same"
        os.replace(tmp, dest)
        return "new" if not old_is_file else "changed"
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        raise


def sync(folder_id, dest_root=DEFAULT_DEST):
    """Mirror the Drive folder under dest_root. Returns (new, changed)."""
    dest_root = os.path.abspath(dest_root)
    os.makedirs(dest_root, exist_ok=True)
    manifest_path = os.path.join(dest_root, MANIFEST_NAME)
    manifest = _load_manifest(manifest_path)

    tree = list_drive(folder_id, recursive=True)
    if not tree:
        print(
            "WARN: empty listing from Drive (folder view empty or unreachable)",
            file=sys.stderr,
            flush=True,
        )
    paths = tree_paths(tree, folder_id)

    new_count = 0
    changed_count = 0
    seen_ids = set()

    for entry in tree:
        fid = entry["id"]
        seen_ids.add(fid)
        rel = _safe_rel(paths.get(fid, entry["name"]))
        old = manifest.get(fid)

        if entry["kind"] == "folder":
            try:
                os.makedirs(os.path.join(dest_root, rel), exist_ok=True)
            except OSError as exc:
                print(f"FAIL: {entry['name']} cannot create folder: {exc}", flush=True)
                continue
            manifest[fid] = {"name": entry["name"], "kind": "folder", "size": None, "path": rel}
            continue

        dest = os.path.join(dest_root, rel)
        try:
            result = _sync_one_file(entry, rel, dest, old)
        except Exception as exc:  # noqa: BLE001 - one failure = one FAIL line
            print(f"FAIL: {rel} {exc}", flush=True)
            continue

        if result == "same":
            continue
        size = os.path.getsize(dest) if os.path.exists(dest) else None
        manifest[fid] = {
            "name": entry["name"],
            "kind": "file",
            "size": size,
            "path": rel,
            "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        shown = os.path.join(os.path.basename(dest_root) or dest_root, rel)
        if result == "new":
            new_count += 1
            print(f"NEW: {shown}", flush=True)
        else:
            changed_count += 1
            print(f"CHANGED: {shown}", flush=True)

    # Keep records for files that are temporarily invisible / still uploading;
    # never delete local files. Just remember which ids the last listing saw.
    manifest["__last_listing__"] = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "ids": sorted(seen_ids),
    }
    _save_manifest(manifest_path, manifest)
    print(f"sync done: {new_count} new, {changed_count} changed", flush=True)
    return new_count, changed_count


# ---------------------------------------------------------------- CLI


def _print_tree(tree, root_id):
    nodes = {n["id"]: n for n in tree}
    depth_of = {}

    def depth(node):
        if node["id"] in depth_of:
            return depth_of[node["id"]]
        d = 0
        cur = node
        seen = {node["id"]}
        while cur.get("parent") and cur["parent"] != root_id:
            parent = nodes.get(cur["parent"])
            if not parent or parent["id"] in seen:
                break
            seen.add(parent["id"])
            d += 1
            cur = parent
        depth_of[node["id"]] = d
        return d

    for node in tree:
        pad = "  " * depth(node)
        tag = "dir " if node["kind"] == "folder" else "file"
        print(f"{pad}{node['name']}  [{tag}]  id={node['id']}")

    files = sum(1 for n in tree if n["kind"] == "file")
    folders = sum(1 for n in tree if n["kind"] == "folder")
    print(f"total: {len(tree)} entries ({files} files, {folders} folders)")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="print the current Drive tree")
    p_list.add_argument("--folder-id", default=FOLDER_ID)
    p_list.add_argument("--json", action="store_true", help="dump the tree as JSON")

    p_sync = sub.add_parser("sync", help="mirror the Drive folder under dest")
    p_sync.add_argument("--once", action="store_true", help="single pass, then exit")
    p_sync.add_argument("--folder-id", default=FOLDER_ID)
    p_sync.add_argument("--dest", default=DEFAULT_DEST)
    p_sync.add_argument("--interval", type=int, default=POLL_INTERVAL)

    args = parser.parse_args(argv)

    if args.cmd == "list":
        tree = list_drive(args.folder_id, recursive=True)
        if args.json:
            json.dump(tree, sys.stdout, indent=2)
            sys.stdout.write("\n")
        else:
            _print_tree(tree, args.folder_id)
        return 0

    sync(args.folder_id, args.dest)
    if args.once:
        return 0

    print(
        f"polling every {args.interval}s for new documents (Ctrl-C to stop)",
        flush=True,
    )
    try:
        while True:
            time.sleep(args.interval)
            try:
                sync(args.folder_id, args.dest)
            except Exception as exc:  # noqa: BLE001 - keep polling through outages
                print(f"WARN: sync failed: {exc}", flush=True)
    except KeyboardInterrupt:
        print("stopped", flush=True)
        return 0


if __name__ == "__main__":
    sys.exit(main())
