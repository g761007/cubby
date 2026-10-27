#!/usr/bin/env python3
"""Download pages from the site into public/p/<id>/.

Usage:
  scripts/pull.py [--force] [--ids-file FILE] BASE_URL [ID ...]

Cloudflare Pages can't list or download the files of a deployment, so the page
ids come from the command line or a file. Each page's files are found by
following the relative links in its HTML and CSS, starting at its index.html.
"""
import argparse
import http.client
import os
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, unquote, urljoin, urlsplit

root = Path(__file__).resolve().parent.parent
pages_dir = root / "public" / "p"

# A page URL anywhere in a line, or a line holding just an id, so `make list` output works.
ID_IN_TEXT = re.compile(r"/p/([0-9a-f]{32})(?![0-9a-f])|^\s*([0-9a-f]{32})\s*$", re.M)
CSS_URL = re.compile(r"""url\(\s*(['"]?)(.*?)\1\s*\)|@import\s+(['"])(.*?)\3""", re.I)
URL_ATTRS = {"src", "href", "poster", "data", "xlink:href"}
REDIRECTS = {301, 302, 303, 307, 308}


class PageError(Exception):
    pass


def css_urls(text):
    return [m.group(2) or m.group(4) for m in CSS_URL.finditer(text) if m.group(2) or m.group(4)]


class Links(HTMLParser):
    """Collects the URLs that an HTML document refers to."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.urls, self.in_style = [], False

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if not value:
                continue
            if name in URL_ATTRS:
                self.urls.append(value)
            elif name in ("srcset", "imagesrcset"):
                self.urls += [c.split()[0] for c in value.split(",") if c.strip()]
            elif name == "style":
                self.urls += css_urls(value)
        if tag == "style":
            self.in_style = True

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False

    def handle_data(self, data):
        if self.in_style:
            self.urls += css_urls(data)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


opener = urllib.request.build_opener(NoRedirect)
# Cloudflare answers Python's default User-Agent with 403.
opener.addheaders = [("User-Agent", "cubby-pull")]


def fetch(url):
    """GET url and return (status, final URL, content type, body).

    Redirects are followed here, because Python 3.9's urllib doesn't follow
    the 308s that Pages sends.
    """
    for _ in range(10):
        try:
            with opener.open(url, timeout=30) as resp:
                return resp.status, url, resp.headers.get_content_type(), resp.read()
        except urllib.error.HTTPError as err:
            location = err.headers.get("Location")
            if err.code not in REDIRECTS or not location:
                return err.code, url, "", b""
            url = urljoin(url, location)
    raise PageError(f"too many redirects at {url}")


def page_file(url_path, prefix, content_type):
    """Map a URL path to a file path inside the page folder, or None if it's outside."""
    if not url_path.startswith(prefix):
        return None
    rel = unquote(url_path[len(prefix):])
    if rel == "" or rel.endswith("/"):
        rel += "index.html"
    elif "." not in rel.rsplit("/", 1)[-1] and content_type == "text/html":
        rel += ".html"  # Pages serves foo.html at /foo
    if any(part in ("", ".", "..") or "\0" in part for part in rel.split("/")):
        return None
    return rel


def pull(base, page_id, staging):
    """Download one page into staging; return the files written and any warnings."""
    start = f"{base}/p/{page_id}/"
    prefix = urlsplit(start).path
    queue, queued, written, warnings = [start], {start}, set(), []
    while queue:
        url = queue.pop(0)
        name = unquote(urlsplit(url).path[len(prefix):]) or "index.html"
        status, final, content_type, body = fetch(url)
        if status == 404:
            if url == start:
                raise PageError("not found on the site (HTTP 404)")
            warnings.append(f"{name}: not found on the site (HTTP 404), skipped")
            continue
        if status != 200:
            raise PageError(f"HTTP {status} for {name}")
        rel = page_file(urlsplit(final).path, prefix, content_type)
        if rel is None:
            warnings.append(f"{name}: leads outside the page folder, skipped")
            continue
        if rel in written:
            continue
        target = staging / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        written.add(rel)
        if rel.endswith((".html", ".htm")):
            links = Links()
            links.feed(body.decode("utf-8", errors="replace"))
            refs = links.urls
        elif rel.endswith(".css"):
            refs = css_urls(body.decode("utf-8", errors="replace"))
        else:
            continue
        host = urlsplit(final).netloc
        for ref in refs:
            link = urlsplit(urljoin(final, ref.strip()))
            if link.scheme not in ("http", "https") or link.netloc != host or not link.path.startswith(prefix):
                continue
            link = f"{link.scheme}://{link.netloc}{quote(unquote(link.path))}"
            if link not in queued:
                queued.add(link)
                queue.append(link)
    if "index.html" not in written:
        raise PageError("the site didn't return the page's index.html")
    return written, warnings


parser = argparse.ArgumentParser(description="Download pages from the site into public/p/<id>/.")
parser.add_argument("base_url", help="site to download from, such as https://<project>.pages.dev")
parser.add_argument("ids", nargs="*", metavar="ID", help="page id")
parser.add_argument("--ids-file", help="file with page ids or page URLs, such as saved `make list` output")
parser.add_argument("--force", action="store_true", help="overwrite pages that already exist locally")
args = parser.parse_args()

base = args.base_url.rstrip("/")
if urlsplit(base).scheme not in ("http", "https"):
    parser.error("BASE_URL must start with https:// or http://")
ids = list(args.ids)
if args.ids_file:
    try:
        text = Path(args.ids_file).read_text(encoding="utf-8", errors="replace")
    except OSError as err:
        parser.error(f"can't read {args.ids_file}: {err.strerror}")
    found = [url_id or line_id for url_id, line_id in ID_IN_TEXT.findall(text)]
    if not found:
        parser.error(f"no page ids or page URLs in {args.ids_file}")
    ids += found
if not ids:
    parser.error("give page ids, or --ids-file")
for page_id in ids:
    if not re.fullmatch(r"[0-9a-f]{32}", page_id):
        parser.error(f"not a 32-character page id: {page_id}")

counts = dict.fromkeys(("pulled", "updated", "skipped", "failed"), 0)
for page_id in dict.fromkeys(ids):
    dest = pages_dir / page_id
    if dest.exists() and not args.force:
        print(f"skipped public/p/{page_id}/: already exists (FORCE=1 overwrites it)")
        counts["skipped"] += 1
        continue
    # Download into a temporary folder first, so a failed page leaves public/p/ untouched.
    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / page_id
        staging.mkdir()
        try:
            written, warnings = pull(base, page_id, staging)
            for warning in warnings:
                print(f"warning: {page_id}: {warning}")
            if dest.exists():
                # Overwrite only the files the site returned. Files that nothing links
                # to can't be downloaded, so local files the site didn't return stay.
                stat = dest.stat()
                local_only = {f.relative_to(dest).as_posix() for f in dest.rglob("*") if f.is_file()} - written
                shutil.copytree(staging, dest, dirs_exist_ok=True)
                os.utime(dest, ns=(stat.st_atime_ns, stat.st_mtime_ns))  # `make list` shows it as the date added
                print(f"updated public/p/{page_id}/: {len(written)} file(s) from the site, "
                      f"kept {len(local_only)} local-only file(s)")
                counts["updated"] += 1
            else:
                pages_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(staging), str(dest))
                print(f"pulled public/p/{page_id}/: {len(written)} file(s)")
                counts["pulled"] += 1
        except (PageError, OSError, http.client.HTTPException) as err:
            print(f"error: {page_id}: {err}")
            counts["failed"] += 1

print(", ".join(f"{count} {result}" for result, count in counts.items()))
sys.exit(1 if counts["failed"] else 0)
