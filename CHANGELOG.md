# Changelog

All notable changes to cubby are recorded here. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased

### Added

- `make pull` downloads pages from the site back into `public/p/`: `ID=<id>` for one page, or `IDS=<file>` for every page listed in a file, such as saved `make list` output. It follows the relative links in each page's HTML and CSS, so files that nothing links to aren't downloaded.
- `make pull` skips pages that already exist locally. `FORCE=1` overwrites them with the version on the site, and keeps local files that the site didn't return.

### Changed

- `make remove` moves the page folder to `.trash/<id>/` instead of deleting it. Git ignores `.trash/` and deploys never include it. Restore a page with `mv .trash/<id> public/p/`.
