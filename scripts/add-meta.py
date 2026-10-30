#!/usr/bin/env python3
"""Give each HTML file a doctype and the noindex / no-referrer meta tags, as a
fallback for the _headers rules. Tags already present are left alone, so running
it again on the same file changes nothing.

Usage: scripts/add-meta.py file.html [file.html ...]
"""
import os
import re
import sys

public = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "public")

for path in sys.argv[1:]:
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

    if added:
        open(path, "w", encoding="utf-8").write(html)
    print(f"  {os.path.relpath(path, public)}: " + (("added " + ", ".join(added)) if added else "ok"))
