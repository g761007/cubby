# cubby: one entry point for adding, checking and deploying unlisted pages.
# Run `make` to list the targets.

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Local settings: copy .env.example to .env.local. Its values override exported
# variables, and the make command line overrides both.
-include .env.local

# Cloudflare Pages project. Set CUBBY_PAGES_PROJECT, or pass PROJECT=<name>.
PROJECT := $(CUBBY_PAGES_PROJECT)
# Base URL printed by `make list`. Set CUBBY_BASE_URL, or pass BASE_URL=...
BASE_URL := $(or $(CUBBY_BASE_URL),$(if $(PROJECT),https://$(PROJECT).pages.dev))
PORT ?= 8000
WRANGLER := npx --yes wrangler@4

.PHONY: help new list preview check deploy remove deployments delete-deployment login create-project

help: ## Show this help
	@awk 'BEGIN {FS = ":.*## "} /^[a-z-]+:.*## / {printf "  make %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo
	@echo "  PROJECT=$(PROJECT)  BASE_URL=$(BASE_URL)"

new: ## Add a page: SRC=page.html, or SRC=folder containing index.html
	@test -n "$(SRC)" || { echo "usage: make new SRC=path/to/page.html" >&2; exit 2; }
	@scripts/new-page.sh "$(SRC)"

list: ## List pages with date added, title and URL
	@for dir in public/p/*/; do \
	  [ -d "$$dir" ] || continue; \
	  id=$$(basename "$$dir"); \
	  title=$$(sed -n 's:.*<title>\(.*\)</title>.*:\1:p' "$$dir/index.html" | head -n 1); \
	  added=$$(date -r "$$dir" +%F); \
	  printf '%-11s %s\n            %s\n' "$$added" "$${title:-(no title)}" "$(BASE_URL)/p/$$id/"; \
	done

preview: ## Serve public/ on localhost (PORT=8000; no _headers or Pages routing)
	@echo "Serving public/ at http://localhost:$(PORT) (Ctrl-C to stop)"
	@python3 -m http.server $(PORT) --bind 127.0.0.1 --directory public

check: ## Check public/ against the noindex and privacy rules
	@python3 scripts/check.py

deploy: check ## Run check, then deploy public/ to Cloudflare Pages
	@CUBBY_PAGES_PROJECT="$(PROJECT)" scripts/deploy.sh

remove: ## Delete a page folder: ID=<page id>
	@[[ "$(ID)" =~ ^[0-9a-f]{32}$$ ]] || { echo "usage: make remove ID=<32-character page id>" >&2; exit 2; }
	@test -d "public/p/$(ID)" || { echo "error: public/p/$(ID) does not exist" >&2; exit 1; }
	@rm -rf "public/p/$(ID)"
	@echo "Removed public/p/$(ID). Next: make deploy, then delete older deployments (make deployments)."

deployments: ## List deployments on Cloudflare (older ones still serve removed pages)
	@test -n "$(PROJECT)" || { echo "error: set CUBBY_PAGES_PROJECT in .env.local, or pass PROJECT=<name>" >&2; exit 2; }
	@$(WRANGLER) pages deployment list --project-name "$(PROJECT)"

delete-deployment: ## Delete one deployment: DEPLOYMENT=<deployment id>
	@test -n "$(PROJECT)" || { echo "error: set CUBBY_PAGES_PROJECT in .env.local, or pass PROJECT=<name>" >&2; exit 2; }
	@test -n "$(DEPLOYMENT)" || { echo "usage: make delete-deployment DEPLOYMENT=<deployment id>" >&2; exit 2; }
	@$(WRANGLER) pages deployment delete "$(DEPLOYMENT)" --project-name "$(PROJECT)"

login: ## Sign Wrangler in to Cloudflare (once per machine)
	@$(WRANGLER) login

create-project: ## Create the Pages project on Cloudflare (once), with main as production branch
	@test -n "$(PROJECT)" || { echo "error: set CUBBY_PAGES_PROJECT in .env.local, or pass PROJECT=<name>" >&2; exit 2; }
	@$(WRANGLER) pages project create "$(PROJECT)" --production-branch main
