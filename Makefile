.PHONY: init-story new-story style-cards check style-lint style-reference epub pdf stats ai-audit review-pack novellas-path import-novella export-novella clear-ingested kindle-preflight kindle kindle-store-password test

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

init-story:
	uv run creative-writer init-story --story "$(STORY)" --kind "$(KIND)" $(STYLE_CARD_ARG)

new-story: init-story

style-cards:
	uv run creative-writer style-cards

check:
	uv run creative-writer check --story "$(STORY)"

style-lint:
	uv run creative-writer style-lint --story "$(STORY)"$(if $(strip $(PROFILE)), --profile "$(PROFILE)")$(if $(strip $(CHAPTER)), --chapter "$(CHAPTER)")

style-reference:
	uv run creative-writer style-reference --story "$(STORY)" --pack "$(PACK)"$(if $(strip $(PROFILE)), --profile "$(PROFILE)")

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
