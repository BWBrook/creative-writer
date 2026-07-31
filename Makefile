.PHONY: init-story new-story style-cards check style-lint style-reference epub pdf stats ai-audit review-pack source-admission source-analysis novellas-path import-novella export-novella clear-ingested kindle-preflight kindle kindle-store-password test

KIND ?= original
STYLE_CARD_ARG :=
ifeq ($(strip $(STYLE_CARD)),)
STYLE_CARD_ARG :=
else
STYLE_CARD_ARG := --style-card "$(STYLE_CARD)"
endif

EXPORT_OUTPUT_ARG :=
ifeq ($(strip $(OUTPUT)),)
EXPORT_OUTPUT_ARG :=
else
EXPORT_OUTPUT_ARG := --output-name "$(OUTPUT)"
endif

override RAW_STORY := $(value STORY)
override RAW_PACK := $(value PACK)
override RAW_PROFILE := $(value PROFILE)
override RAW_CHAPTER := $(value CHAPTER)
export RAW_STORY RAW_PACK RAW_PROFILE RAW_CHAPTER

style-lint style-reference: override STORY := $(value STORY)
style-lint style-reference: override PACK := $(value PACK)
style-lint style-reference: override PROFILE := $(value PROFILE)
style-lint style-reference: override CHAPTER := $(value CHAPTER)

init-story:
	uv run creative-writer init-story --story "$(STORY)" --kind "$(KIND)" $(STYLE_CARD_ARG)

new-story: init-story

style-cards:
	uv run creative-writer style-cards

check:
	uv run creative-writer check --story "$(STORY)"

style-lint:
	@case "$${RAW_STORY}" in *[![:space:]]*) ;; *) printf '%s\n' 'STORY is required for style-lint' >&2; exit 2 ;; esac; \
	set -- uv run creative-writer style-lint "--story=$${RAW_STORY}"; \
	case "$${RAW_PROFILE}" in *[![:space:]]*) set -- "$$@" "--profile=$${RAW_PROFILE}" ;; esac; \
	case "$${RAW_CHAPTER}" in *[![:space:]]*) set -- "$$@" "--chapter=$${RAW_CHAPTER}" ;; esac; \
	exec "$$@"

style-reference:
	@case "$${RAW_STORY}" in *[![:space:]]*) ;; *) printf '%s\n' 'STORY is required for style-reference' >&2; exit 2 ;; esac; \
	case "$${RAW_PACK}" in *[![:space:]]*) ;; *) printf '%s\n' 'PACK is required for style-reference' >&2; exit 2 ;; esac; \
	set -- uv run creative-writer style-reference "--story=$${RAW_STORY}" "--pack=$${RAW_PACK}"; \
	case "$${RAW_PROFILE}" in *[![:space:]]*) set -- "$$@" "--profile=$${RAW_PROFILE}" ;; esac; \
	exec "$$@"

epub:
	uv run creative-writer epub --story "$(STORY)"

pdf:
	uv run creative-writer pdf --story "$(STORY)"

stats:
	uv run creative-writer stats --story "$(STORY)"

ai-audit:
	uv run creative-writer ai-audit --story "$(STORY)"

review-pack:
	uv run creative-writer review-pack --story "$(STORY)" --pack "$(PACK)"

source-admission:
	uv run creative-writer source-admission --story "$(STORY)"

source-analysis:
	uv run creative-writer source-analysis --story "$(STORY)" --stage "$(STAGE)"

novellas-path:
	uv run creative-writer novellas-path

import-novella:
	uv run creative-writer import-novella --source "$(FILE)"

export-novella:
	uv run creative-writer export-novella --input "$(INPUT)" $(EXPORT_OUTPUT_ARG)

clear-ingested:
	uv run creative-writer clear-ingested --story "$(STORY)"

kindle-preflight:
	uv run creative-writer kindle-preflight --story "$(STORY)"

kindle:
	uv run creative-writer kindle --story "$(STORY)"

kindle-store-password:
	uv run creative-writer kindle-store-password

test:
	uv run --group dev pytest
