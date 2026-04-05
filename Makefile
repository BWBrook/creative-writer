.PHONY: init-story new-story style-cards check epub pdf stats novellas-path import-novella export-novella clear-ingested kindle-preflight kindle kindle-store-password test

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

epub:
	uv run creative-writer epub --story "$(STORY)"

pdf:
	uv run creative-writer pdf --story "$(STORY)"

stats:
	uv run creative-writer stats --story "$(STORY)"

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
