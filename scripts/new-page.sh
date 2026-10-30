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

# Every HTML page gets a doctype and the noindex / no-referrer meta tags.
find "$dest" -name '*.html' -exec python3 "$root/scripts/add-meta.py" {} +

echo "Created public/p/$id/"
echo "URL path: /p/$id/"
echo "Deploy the public/ folder to publish it."
