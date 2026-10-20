#!/usr/bin/env python3
"""Check public/ against cubby's noindex and privacy rules. Exits 1 on any error."""
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
public = root / "public"
pages_dir = public / "p"
errors, warnings = [], []


def rel(path):
    return path.relative_to(root).as_posix()


def tokens(value):
    return {t.strip() for t in (value or "").lower().split(",") if t.strip()}


# _headers: the catch-all rule must send the three privacy headers.
headers_file = public / "_headers"
rules, current = {}, None
if headers_file.is_file():
    for line in headers_file.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[0].isspace():
            current = rules.setdefault(line.strip(), {})
        elif current is not None and ":" in line:
            name, value = line.split(":", 1)
            current[name.strip().lower()] = value.strip().lower()
else:
    errors.append("public/_headers is missing")
catch_all = rules.get("/*", {})
if not {"noindex", "nofollow", "noarchive"} <= tokens(catch_all.get("x-robots-tag")):
    errors.append("public/_headers: the /* rule must send X-Robots-Tag: noindex, nofollow, noarchive")
if catch_all.get("referrer-policy") != "no-referrer":
    errors.append("public/_headers: the /* rule must send Referrer-Policy: no-referrer")
if catch_all.get("x-content-type-options") != "nosniff":
    errors.append("public/_headers: the /* rule must send X-Content-Type-Options: nosniff")

# robots.txt must let crawlers in (to read noindex) and must not list URLs.
robots_txt = public / "robots.txt"
if robots_txt.is_file():
    text = robots_txt.read_text(encoding="utf-8")
    if re.search(r"(?im)^\s*disallow:\s*/\s*$", text):
        errors.append("public/robots.txt: 'Disallow: /' stops crawlers from seeing noindex")
    if re.search(r"(?im)^\s*sitemap:", text):
        errors.append("public/robots.txt: remove the Sitemap line")
else:
    warnings.append("public/robots.txt is missing")

if not (public / "404.html").is_file():
    errors.append("public/404.html is missing, so Pages would serve the root page for unknown paths")

for path in public.rglob("*"):
    if path.name == ".DS_Store" or path.name.startswith("._"):
        warnings.append(f"{rel(path)}: deploy.sh skips it, but a dashboard upload would publish it")

# Page folders: 32-char lowercase hex ids, each with an index.html.
ids = []
if pages_dir.is_dir():
    for entry in sorted(pages_dir.iterdir()):
        if not entry.is_dir():
            if entry.name != ".DS_Store":
                errors.append(f"{rel(entry)}: only page folders belong in public/p/")
            continue
        if not re.fullmatch(r"[0-9a-f]{32}", entry.name):
            errors.append(f"{rel(entry)}: folder name must be a 32-character lowercase hex id")
        if not (entry / "index.html").is_file():
            errors.append(f"{rel(entry)}: missing index.html")
        ids.append(entry.name)


def meta_content(html, name):
    for tag in re.findall(r"<meta\b[^>]*>", html, re.I):
        if re.search(r"\bname\s*=\s*[\"']?%s[\"'\s>/]" % name, tag, re.I):
            content = re.search(r"\bcontent\s*=\s*[\"']([^\"']*)", tag, re.I)
            return content.group(1).lower() if content else ""
    return None


for page in sorted(public.rglob("*.html")):
    raw = page.read_bytes()
    html = raw.decode("utf-8", errors="replace")
    where = rel(page)
    if not re.match(r"\s*<!doctype html", html, re.I):
        errors.append(f"{where}: missing <!DOCTYPE html>")
    if not re.search(rb"<meta\b[^>]*charset", raw[:1024], re.I):
        errors.append(f"{where}: no charset meta in the first 1024 bytes")
    if "noindex" not in tokens(meta_content(html, "robots")):
        errors.append(f"{where}: robots meta must include noindex")
    if "noindex" not in tokens(meta_content(html, "googlebot")):
        errors.append(f"{where}: googlebot meta must include noindex")
    if meta_content(html, "referrer") != "no-referrer":
        errors.append(f"{where}: referrer meta must be no-referrer")

# Served files outside public/p/ must not point at pages.
for path in public.rglob("*"):
    if not path.is_file() or pages_dir in path.parents or path.name in ("_headers", "_redirects"):
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    if "/p/" in text or any(page_id in text for page_id in ids):
        errors.append(f"{rel(path)}: a file outside public/p/ mentions a page path")

for message in warnings:
    print(f"warning: {message}")
for message in errors:
    print(f"error: {message}")
if errors:
    sys.exit(1)
print(f"ok: {len(ids)} page(s), public/ follows the rules")
