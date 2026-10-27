# cubby

English | [繁體中文](README.zh_TW.md)

Unlisted static pages on Cloudflare Pages, like a private gist for HTML. Anyone with the full URL can open a page. Nothing links to it, and search engines are told not to index it.

> This is obscurity, not access control. Anyone who has a URL can open it and forward it. Don't publish secrets here.

## How it works

- Each page lives at `/p/<id>/`. The `<id>` is 32 hex characters (128 bits) from a cryptographically secure random generator.
- `public/_headers` sends these headers on every path:
  - `X-Robots-Tag: noindex, nofollow, noarchive`
  - `Referrer-Policy: no-referrer`
  - `X-Content-Type-Options: nosniff`
- Every HTML page also carries `robots`, `googlebot` and `referrer` meta tags, in case the headers are missing.
- `robots.txt` allows crawling on purpose. A crawler has to fetch a page to see its `noindex`.
- The root page and `404.html` both show a plain "404 Not Found", so the site reveals nothing about its purpose.
- There is no sitemap and no list of pages on the site. `make list` shows them locally.

## Commands

Everything goes through `make`. Run `make` on its own to list the targets.

| Command | What it does |
|---|---|
| `make new SRC=page.html` | Add a page from an HTML file, or from a folder with `index.html` |
| `make list` | List pages with the date added, title and URL |
| `make preview` | Serve `public/` on localhost (`PORT=8000`) |
| `make check` | Check `public/` against the noindex and privacy rules |
| `make deploy` | Run `check`, then deploy `public/` to Cloudflare Pages |
| `make pull ID=<id>` | Download a page from the site into `public/p/`, or every page listed in a file with `IDS=<file>` |
| `make remove ID=<id>` | Move a page folder to `.trash/` |
| `make deployments` | List the project's deployments on Cloudflare |
| `make delete-deployment DEPLOYMENT=<id>` | Delete one deployment |
| `make login` | Sign Wrangler in to Cloudflare, once per machine |
| `make create-project` | Create the Pages project, once, with `main` as the production branch |

## Layout

```text
Makefile           the entry point
.env.example       settings template; copy it to .env.local
.trash/            pages moved out by `make remove`, ignored by git
public/            deploy root: everything in here is publicly reachable
  _headers
  robots.txt
  index.html       neutral "404 Not Found" placeholder
  404.html         returned for unknown paths
  p/<id>/          one folder per page, ignored by git
scripts/
  new-page.sh      used by `make new`
  check.py         used by `make check`
  deploy.sh        used by `make deploy`
  pull.py          used by `make pull`
```

Never keep a list of page URLs, or notes about them, inside `public/`.

## Requirements

- macOS or Linux with `bash`, `make`, `python3`, `openssl` and `rsync`. On macOS, the Xcode Command Line Tools provide `make`.
- Node.js 22 or later, for Wrangler
- A Cloudflare Pages project that uses Direct Upload

## Installation

There is no build step. Clone the repository, make the scripts executable, and create your settings file:

```bash
chmod +x scripts/*.sh scripts/*.py
```

```bash
cp .env.example .env.local
```

Set `CUBBY_PAGES_PROJECT` in `.env.local`, then sign in to Cloudflare:

```bash
make login
```

If the Pages project doesn't exist yet, create it once:

```bash
make create-project
```

`public/p/` is in `.gitignore`, because the folder names under it are the secret URLs. Pages never go into git, so back them up yourself. As long as you still have their ids, `make pull` can download them from the site again. See [Pull pages back](#pull-pages-back).

## Configuration

The Makefile reads `.env.local`, which git ignores. Start from `.env.example`. Write plain `KEY=value` lines, without quotes or `export`.

| Variable | Purpose |
|---|---|
| `CUBBY_PAGES_PROJECT`, or `PROJECT=` on the make command line | Cloudflare Pages project name. Required by `deploy`, `deployments`, `delete-deployment` and `create-project`. |
| `CUBBY_BASE_URL`, or `BASE_URL=` | Base URL that `make list` prints and `make pull` downloads from. Defaults to `https://<project>.pages.dev`. Set it if you use a custom domain, or if Cloudflare gave the project a different pages.dev subdomain. |
| `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` | Optional. Authenticate Wrangler without `make login`, for example in CI. Export them in the shell; the Makefile doesn't pass `.env.local` values on to Wrangler. Never commit them. |

Values in `.env.local` override variables exported in the shell, and `PROJECT=` / `BASE_URL=` on the make command line override both. `make` shows the values in effect.

If the pages.dev subdomain is already taken, Cloudflare adds a suffix to it. Check the domain after `make create-project`.

The project name becomes `<name>.pages.dev` and appears in every shared URL, so pick a neutral name that doesn't describe the content.

## Add a page

```bash
make new SRC=path/to/page.html
```

- **A single HTML file** becomes `public/p/<id>/index.html`.
- **A folder** must contain `index.html`. All its files are copied into `public/p/<id>/`, except `.DS_Store`. Reference assets with relative paths, such as `style.css` or `img/logo.png`, not `/style.css`.
- **Meta tags:** a doctype and any missing `charset`, `robots`, `googlebot` and `referrer` meta tags are added to every HTML file that is copied. HTML fragments without `<html>` or `<head>` also work, such as a Claude artifact export. The browser builds those elements implicitly.
- **Warning:** if a page already has a `robots` meta tag without `noindex`, `make new` warns instead of rewriting it, and `make check` fails until you fix the tag by hand.

After adding a page, run `make deploy`. To find a page's URL later, run `make list`. It shows the page folder's modification time as the date added.

## Preview locally

```bash
make preview
```

The preview does not apply `_headers` or Cloudflare's routing rules. Use it only to check how pages look.

## Check

```bash
make check
```

`make deploy` runs this first and stops if anything fails. It checks that:

- the `/*` rule in `_headers` sends the three headers listed above
- `robots.txt` has no `Disallow: /` and no `Sitemap`
- `404.html` exists
- every folder in `public/p/` is a 32-character hex id with an `index.html`
- every HTML file has a doctype, a charset, and `noindex` / `no-referrer` meta tags
- no served file outside `public/p/` mentions a page path

It warns about `.DS_Store` files, which a dashboard upload would publish.

## Deploy

```bash
make deploy
```

After `make check` passes, `scripts/deploy.sh`:

- uploads a copy of `public/` without `.DS_Store` files
- tags the deployment with the current git branch and commit
- warns when the tracked files in `public/` have uncommitted changes

Deploying from `main` updates the live site, because `make create-project` sets `main` as the production branch. Any other branch creates a preview deployment. If you created the project in the dashboard instead, check its production branch there.

You can also upload the `public` folder in the dashboard: open the project in Workers & Pages and select **Create a new deployment**. Dashboard uploads don't filter out `.DS_Store` files, so run `make check` first.

Deploy to the same Pages project each time. A new project means a new domain, and every URL already shared stops working.

## Verify after deploying

The response should include `x-robots-tag: noindex, nofollow, noarchive` and `referrer-policy: no-referrer`:

```bash
curl -sI https://<project>.pages.dev/p/<id>/
```

Unknown paths should return 404:

```bash
curl -sI https://<project>.pages.dev/p/
```

## Remove a page

```bash
make remove ID=<page id>
```

This moves the page folder to `.trash/<id>/`, which git ignores and `make deploy` doesn't upload. Then run `make deploy`. If `.trash/<id>` already exists, `make remove` stops without changing anything.

To bring the page back, move it back and deploy again:

```bash
mv .trash/<page id> public/p/
```

Nothing empties `.trash/` for you. Delete its folders yourself once you no longer need them.

Each Pages deployment keeps its own `https://<hash>.<project>.pages.dev` URL. A deleted page is still reachable through deployments made before you removed it. To take it down completely, find those deployments and delete them:

```bash
make deployments
```

```bash
make delete-deployment DEPLOYMENT=<deployment id>
```

Cloudflare doesn't let you delete the latest deployment of a branch.

## Pull pages back

`make pull` downloads pages from the site into `public/p/`, for example on a new machine or after you lose local files:

```bash
make pull ID=<page id>
```

```bash
make pull IDS=<file>
```

Cloudflare Pages has no way to list or download the files of a deployment, so you need the page ids. `IDS=` reads every page URL in the file, and every line that holds only an id, so the output of `make list` works as is. Save it after you add pages, and keep it somewhere private, outside `public/` and out of git.

- Files are found by starting at each page's `index.html` and following the relative links in its HTML and CSS: `src`, `href`, `srcset`, `poster`, `style`, `url()` and `@import`. Only files under the page's own `/p/<id>/` path are downloaded.
- Files that nothing links to, and files that only JavaScript loads, aren't downloaded.
- A page is written to `public/p/` only after all its files have downloaded, so a failed pull leaves nothing half done.
- Pages that already exist locally are skipped. Add `FORCE=1` to overwrite their files with the version on the site. Local files that the site didn't return are kept.
- `make list` shows the day you pulled a page as its date added. With `FORCE=1`, an existing page keeps its date.
- To pull from an older deployment, such as one that still serves a page you removed, add `BASE_URL=https://<hash>.<project>.pages.dev`.

## Troubleshooting

- **Unknown paths show the root page instead of a 404.** Keep `public/404.html`. Without a top-level `404.html`, Cloudflare Pages treats the site as a single-page app and serves the root page for every unknown path.
- **A `.DS_Store` file ends up in `public/`.** Finder creates these, and they list file names, which are page ids. `make deploy` leaves them out, and `make check` warns about them before a dashboard upload.
- **An asset fails to load after deploy.** Use relative paths inside a page folder. With `X-Content-Type-Options: nosniff`, a stylesheet or script served with the wrong type is blocked.
- **A third-party script appears in your pages.** Cloudflare Web Analytics injects one when it is enabled. Keep it disabled for this project.
- **Limits.** Dashboard uploads accept up to 1,000 files, and Wrangler accepts up to 20,000. Each file can be at most 25 MiB.

## License

[MIT](LICENSE)
