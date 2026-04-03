.PHONY: init-story new-story check epub pdf novellas-path import-novella export-novella clear-ingested test

KIND ?= original

EXPORT_OUTPUT_ARG :=
ifeq ($(strip $(OUTPUT)),)
EXPORT_OUTPUT_ARG :=
else
EXPORT_OUTPUT_ARG := --output-name "$(OUTPUT)"
endif

init-story:
	uv run creative-writer init-story --story "$(STORY)" --kind "$(KIND)"

new-story: init-story

check:
	uv run creative-writer check --story "$(STORY)"

epub:
	uv run creative-writer epub --story "$(STORY)"

pdf:
	uv run creative-writer pdf --story "$(STORY)"

novellas-path:
	uv run creative-writer novellas-path

import-novella:
	uv run creative-writer import-novella --source "$(FILE)"

export-novella:
	uv run creative-writer export-novella --input "$(INPUT)" $(EXPORT_OUTPUT_ARG)

clear-ingested:
	uv run creative-writer clear-ingested --story "$(STORY)"

test:
	uv run --group dev pytest
