# Changelog

All notable changes to cubby are recorded here. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.2.0] - 2026-10-30

### Added

- `make fix ID=<id>` adds the doctype and any missing meta tags to a page after you overwrite its files by hand, such as replacing `index.html` with a new version. Without `ID`, it goes through every page. Files that already have the tags are left unchanged.

### Changed

- The meta tag step of `make new` moved from `scripts/new-page.sh` to `scripts/add-meta.py`, which `make fix` also uses.

## [1.1.0] - 2026-10-27

### Added

- `make pull` downloads pages from the site back into `public/p/`: `ID=<id>` for one page, or `IDS=<file>` for every page listed in a file, such as saved `make list` output. It follows the relative links in each page's HTML and CSS, so files that nothing links to aren't downloaded.
- `make pull` skips pages that already exist locally. `FORCE=1` overwrites them with the version on the site, and keeps local files that the site didn't return.

### Changed

- `make remove` moves the page folder to `.trash/<id>/` instead of deleting it. Git ignores `.trash/` and deploys never include it. Restore a page with `mv .trash/<id> public/p/`.

## [1.0.0] - 2026-10-20

### Added

- Unlisted pages on Cloudflare Pages at `/p/<id>/`, where `<id>` is 128 random bits. Every path sends `noindex` and `no-referrer` headers, every HTML page carries matching meta tags, and the root and unknown paths show a plain 404.
- `make` targets to add, list, preview, check and deploy pages, remove a page, list and delete deployments, sign in to Cloudflare, and create the Pages project.
- README in English and Traditional Chinese.

[1.2.0]: https://github.com/g761007/cubby/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/g761007/cubby/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/g761007/cubby/releases/tag/v1.0.0
