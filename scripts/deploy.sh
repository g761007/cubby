#!/usr/bin/env bash
# Deploy public/ to Cloudflare Pages with Wrangler.
#
# Usage:
#   CUBBY_PAGES_PROJECT=<project> scripts/deploy.sh
#
# Wrangler must be signed in first: run `npx wrangler login` once, or export
# CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
public="$root/public"
project="${CUBBY_PAGES_PROJECT:-}"

if [[ -z "$project" ]]; then
  echo "error: set CUBBY_PAGES_PROJECT to the Cloudflare Pages project name" >&2
  echo "  e.g. CUBBY_PAGES_PROJECT=<project> $0" >&2
  exit 2
fi
for cmd in npx git rsync; do
  command -v "$cmd" >/dev/null || { echo "error: $cmd is required" >&2; exit 1; }
done

# Refuse to publish a site that search engines may index, or that would serve
# the root page for every unknown path.
grep -Eqi '^[[:space:]]+X-Robots-Tag:.*noindex' "$public/_headers" 2>/dev/null \
  || { echo "error: public/_headers must send X-Robots-Tag: noindex" >&2; exit 1; }
[[ -f "$public/404.html" ]] || { echo "error: public/404.html is missing" >&2; exit 1; }

branch="$(git -C "$root" rev-parse --abbrev-ref HEAD)"
dirty=false
if [[ -n "$(git -C "$root" status --porcelain -- public)" ]]; then
  dirty=true
  echo "warning: public/ has uncommitted changes; deploying them anyway" >&2
fi
if [[ "$branch" != main ]]; then
  echo "note: deploying as branch '$branch'; unless it is the project's production branch, this is a preview" >&2
fi

# Upload a clean copy: Finder's .DS_Store files list file names, which are page ids.
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
rsync -a --exclude '.DS_Store' --exclude '._*' "$public/" "$stage/"

cd "$root"
npx --yes wrangler@4 pages deploy "$stage" \
  --project-name "$project" \
  --branch "$branch" \
  --commit-hash "$(git rev-parse HEAD)" \
  --commit-message "$(git log -1 --format=%s)" \
  --commit-dirty="$dirty"
