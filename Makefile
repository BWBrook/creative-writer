.PHONY: init-story check epub pdf test

KIND ?= original

init-story:
	uv run creative-writer init-story --story "$(STORY)" --kind "$(KIND)"

check:
	uv run creative-writer check --story "$(STORY)"

epub:
	uv run creative-writer epub --story "$(STORY)"

pdf:
	uv run creative-writer pdf --story "$(STORY)"

test:
	uv run --group dev pytest
