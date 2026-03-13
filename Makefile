SUBDIRS := esphome backend

.PHONY: help clean hooks

# ── Help: parse ## comments from all sub-Makefiles ───────────────────────────

help:
	@for d in $(SUBDIRS); do \
		printf "\n\033[1m[$$d]\033[0m\n"; \
		grep -E '^[a-zA-Z_-]+:.*##' $$d/Makefile | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'; \
	done

# ── Clean: run in all subdirs ─────────────────────────────────────────────────

clean:
	@for d in $(SUBDIRS); do \
		echo "--- Cleaning $$d ---"; \
		$(MAKE) -C $$d clean; \
	done

# ── Hooks: install versioned git hooks from .githooks/ ───────────────────────

hooks:
	git config core.hooksPath .githooks
	@echo "Git hooks installed from .githooks/"

# ── Catch-all: delegate to whichever subdir owns this target ─────────────────
# Any target added to esphome/Makefile or backend/Makefile automatically works.

%:
	@found=0; \
	for d in $(SUBDIRS); do \
		if grep -qE '^$@[[:space:]]*:' $$d/Makefile 2>/dev/null; then \
			$(MAKE) -C $$d $@; \
			found=1; \
		fi; \
	done; \
	if [ "$$found" = "0" ]; then \
		echo "Unknown target '$@'. Run 'make help' to see available targets."; \
		exit 1; \
	fi

.DEFAULT_GOAL := help
