#!/usr/bin/env bash
# Add an unlisted page under public/p/<id>/, where <id> is 128 random bits.
#
# Usage:
#   scripts/new-page.sh path/to/page.html   # single file -> public/p/<id>/index.html
#   scripts/new-page.sh path/to/folder      # folder with index.html (+ assets) -> public/p/<id>/
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
public="$root/public"
src="${1:-}"

if [[ -z "$src" ]]; then
  echo "usage: $0 <page.html | folder-with-index.html>" >&2
  exit 2
fi
for cmd in openssl python3 rsync; do
  command -v "$cmd" >/dev/null || { echo "error: $cmd is required" >&2; exit 1; }
done

# 32 hex chars from a CSPRNG; the loop only guards against a theoretical collision.
while :; do
  id="$(openssl rand -hex 16)"
  dest="$public/p/$id"
  [[ -e "$dest" ]] || break
done

if [[ -f "$src" && "$src" == *.html ]]; then
  mkdir -p "$dest"
  cp "$src" "$dest/index.html"
elif [[ -d "$src" && -f "$src/index.html" ]]; then
  mkdir -p "$dest"
  rsync -a --exclude '.DS_Store' "$src/" "$dest/"
else
  echo "error: '$src' is neither an .html file nor a folder containing index.html" >&2
  exit 1
fi

# Every HTML page gets a doctype and the noindex / no-referrer meta tags, as a
# fallback for the _headers rules.
while IFS= read -r -d '' file; do
  python3 - "$file" "$public" <<'PY'
import os, re, sys

path, public = sys.argv[1], sys.argv[2]
html = open(path, encoding="utf-8").read()
added = []

tags = []  # (label, tag)
if not re.search(r"<meta[^>]+charset", html, re.I):
    tags.append(("charset", '<meta charset="utf-8">'))
for name, content in (("robots", "noindex, nofollow, noarchive"),
                      ("googlebot", "noindex, nofollow"),
                      ("referrer", "no-referrer")):
    existing = re.search(r"<meta[^>]+name=[\"']?%s[\"'\s>][^>]*>" % name, html, re.I)
    if not existing:
        tags.append((name, f'<meta name="{name}" content="{content}">'))
    elif name != "referrer" and "noindex" not in existing.group(0).lower():
        print(f"warning: {os.path.relpath(path, public)} has a {name} meta without noindex", file=sys.stderr)

if tags:
    block = "\n".join(tag for _, tag in tags) + "\n"
    head = re.search(r"<head(\s[^>]*)?>", html, re.I)
    if head:
        html = html[:head.end()] + "\n" + block + html[head.end():]
    else:
        # Without <head>, the parser opens one implicitly, so tags placed right after
        # the doctype / <html> still end up in <head>.
        top = re.match(r"\s*(<!doctype[^>]*>\s*)?(<html(\s[^>]*)?>\s*)?", html, re.I)
        html = html[:top.end()] + block + html[top.end():]
    added += [label for label, _ in tags]

if not re.match(r"\s*<!doctype html", html, re.I):
    html = "<!DOCTYPE html>\n" + html.lstrip()
    added.insert(0, "doctype")

open(path, "w", encoding="utf-8").write(html)
print(f"  {os.path.relpath(path, public)}: " + (("added " + ", ".join(added)) if added else "ok"))
PY
done < <(find "$dest" -name '*.html' -print0)

echo "Created public/p/$id/"
echo "URL path: /p/$id/"
echo "Deploy the public/ folder to publish it."
