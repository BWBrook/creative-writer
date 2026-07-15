# Wells Phase 2A Reference Corpus Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retain, fingerprint, and validate the closed twelve-source *Time Expedition* reference corpus while recording *The Lost World* as an unacquired Tier 5 diagnostic and stopping before detailed Wells analysis.

**Architecture:** Extend the retained-source model so full works and bounded omnibus selections have mutually exclusive, fingerprinted derived-text interfaces. Harden the existing `source-admission` command to validate those interfaces, require exact declared-versus-physical EPUB and `original/text` Markdown sets, and report them, then acquire and deterministically convert the approved editions into the story-local corpus. Keep publication commands unchanged and use the admission report as the sole corpus trust surface.

**Tech Stack:** Python 3.12, Pydantic 2, PyYAML, pytest, Pandoc 3.10, Lua filters, ZIP/EPUB, GNU Make, Git.

## Global Constraints

- The completed admission boundary is exactly twelve `admitted`, zero `approved`, zero `proposed`, and one `excluded` record.
- *The Time Machine* remains the sole Tier 1 continuity canon and primary style authority.
- All five Tier 4 sources are negative or comparative controls and never positive style or continuity authorities.
- *King Solomon's Mines* is restricted to adventure architecture and motivation control; it supplies no style, phrase, character, place, incident, ideology, or continuity material.
- *The Lost World* remains Tier 5, `status: excluded`, `style_authority: none`, and has no downloaded, retained, converted, or analysed artifact.
- The selected Wells omnibus retains exactly four derived witnesses: `the-plattner-story`, `the-sea-raiders`, `the-crystal-egg`, and `the-star`.
- Every retained EPUB and every derived Markdown witness has a committed SHA-256 fingerprint.
- Derived Markdown is generated from explicitly named literary XHTML inputs, never by whole-EPUB conversion or manual prose editing.
- Reference sources remain under `stories/time-expedition/original/` and remain excluded from manuscript statistics, publication builds, review packs, AI-writing audits, and Kindle output.
- No quantitative Wells profile, close reading, findings document, evidence-ledger claim, style-guide revision, Permian research, story planning, or manuscript prose is permitted in this plan.
- `make source-admission STORY=time-expedition` remains the public corpus-validation command; no new top-level CLI command is added.
- Phase 2A ends after the completed corpus is verified, committed, and pushed; detailed Wells study requires a new human authorisation.

---

## File Map

- `src/creative_writer/models.py`: retained full-work and selected-witness schemas and invariants.
- `src/creative_writer/source_admission.py`: archive-member, derived-text, fingerprint, parity, excluded-artifact, and report validation.
- `tests/test_source_models.py`: schema-shape and path-invariant tests.
- `tests/test_source_admission.py`: admission checker and report behavior tests.
- `stories/time-expedition/source-study/admission.yml`: final thirteen-record authority and admission boundary.
- `stories/time-expedition/original/sources.yml`: exact metadata for the twelve retained artifacts.
- `stories/time-expedition/original/filters/remove-project-gutenberg-boilerplate.lua`: deterministic removal of Project Gutenberg boilerplate containers, images, cover headings, and terminal transcriber notes while preserving non-empty literary `pgmonospaced` blocks.
- `stories/time-expedition/original/README.md`: final corpus inventory and exact regeneration instructions.
- `stories/time-expedition/source-study/README.md`: final admission-gate state and stop condition.
- `stories/time-expedition/source-study/method.md`: final corpus boundary and continued prohibition on detailed analysis.
- `stories/time-expedition/original/*.epub`: eight newly retained approved source archives.
- `stories/time-expedition/original/text/*.md`: seven new full-work derived texts.
- `stories/time-expedition/original/text/selected-short-fiction/*.md`: four bounded Wells story witnesses.

---

### Task 1: Model Fingerprinted Full Works and Omnibus Selections

**Files:**
- Modify: `src/creative_writer/models.py:255-302`
- Modify: `tests/test_source_models.py`
- Modify: `tests/test_source_admission.py` (fixture migration only)

**Interfaces:**
- Consumes: existing `Slug`, `NonEmptyStr`, `SourceWork`, and `SourcesRegistry` models.
- Produces: `RetainedSourceSelection`; paired `RetainedSourceFiles.markdown` and `markdown_sha256`; `RetainedSourceRecord.selections`; model-level full-work-versus-omnibus invariants.

- [ ] **Step 1: Add complete valid model fixtures and failing shape tests**

Add a helper that writes one complete retained record, allowing its derived-text block to be replaced without duplicating unrelated metadata:

```python
def _retained_record_yaml(derived: str) -> str:
    return f"""sources:
  - id: the-time-machine
    role:
      tier: 1
      story_world_canon: true
      style_authority: primary
      primary_style_anchor: true
      secondary_style_anchor: false
      focus: Canonical frame.
      analytical_roles: [canonical frame]
      permitted_uses: [continuity]
      prohibited_uses: [none]
    work: {{title: The Time Machine, author: H. G. Wells, first_published: 1895}}
    edition:
      publisher: Standard Ebooks
      homepage: https://example.test/book
      download_url: https://example.test/book.epub
      upstream_release: test-release
      upstream_revision: test-revision
    retrieved: 2026-07-14
    files:
      epub: book.epub
      epub_sha256: {'a' * 64}
{derived}
    derivation:
      tool: Pandoc 3.10
      input: Explicit XHTML inputs.
      writer: gfm-raw_html
      wrap: none
      filter: filters/remove-excluded-packaging-links.lua
    provenance: {{transcription: Test transcription, page_scans: Test scans}}
    rights: {{source_text: Public domain test fixture., edition_contributions: Test edition statement.}}
"""
```

Add tests for the two valid shapes and all model-level failures:

```python
def test_retained_full_work_requires_markdown_fingerprint(tmp_path: Path) -> None:
    path = tmp_path / "sources.yml"
    path.write_text(_retained_record_yaml("""      markdown: text/book.md
      markdown_sha256: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
    selections: []"""), encoding="utf-8")
    registry = load_yaml_model(path, SourcesRegistry)
    assert registry.sources[0].files.markdown == "text/book.md"
    assert registry.sources[0].selections == []


def test_retained_omnibus_parses_fingerprinted_selections(tmp_path: Path) -> None:
    path = tmp_path / "sources.yml"
    path.write_text(_retained_record_yaml("""    selections:
      - id: the-star
        title: The Star
        first_published: 1897
        input: epub/text/the-star.xhtml
        markdown: text/selected-short-fiction/the-star.md
        markdown_sha256: cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"""), encoding="utf-8")
    registry = load_yaml_model(path, SourcesRegistry)
    assert registry.sources[0].files.markdown is None
    assert registry.sources[0].selections[0].input == "epub/text/the-star.xhtml"


@pytest.mark.parametrize(
    ("derived", "message"),
    [
        ("    selections: []", "exactly one derived-text shape"),
        ("""      markdown: text/book.md
    selections: []""", "markdown and markdown_sha256 must be supplied together"),
        ("""      markdown_sha256: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
    selections: []""", "markdown and markdown_sha256 must be supplied together"),
        ("""      markdown: text/book.md
      markdown_sha256: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
    selections:
      - id: the-star
        title: The Star
        first_published: 1897
        input: epub/text/the-star.xhtml
        markdown: text/selected-short-fiction/the-star.md
        markdown_sha256: cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc""", "exactly one derived-text shape"),
    ],
)
def test_retained_source_rejects_invalid_derived_shape(
    tmp_path: Path, derived: str, message: str
) -> None:
    path = tmp_path / "sources.yml"
    path.write_text(_retained_record_yaml(derived), encoding="utf-8")
    with pytest.raises(CreativeWriterError, match=message):
        load_yaml_model(path, SourcesRegistry)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("input", "../the-star.xhtml", "selection input must be a relative XHTML member"),
        ("input", "/epub/text/the-star.xhtml", "selection input must be a relative XHTML member"),
        ("input", "epub/text/the-star.md", "selection input must be a relative XHTML member"),
        ("markdown", "../the-star.md", "selection markdown must be below text/"),
        ("markdown", "other/the-star.md", "selection markdown must be below text/"),
    ],
)
def test_retained_selection_rejects_invalid_paths(
    tmp_path: Path, field: str, value: str, message: str
) -> None:
    derived = """    selections:
      - id: the-star
        title: The Star
        first_published: 1897
        input: epub/text/the-star.xhtml
        markdown: text/selected-short-fiction/the-star.md
        markdown_sha256: cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"""
    derived = derived.replace(f"{field}: " + ("epub/text/the-star.xhtml" if field == "input" else "text/selected-short-fiction/the-star.md"), f"{field}: {value}")
    path = tmp_path / "sources.yml"
    path.write_text(_retained_record_yaml(derived), encoding="utf-8")
    with pytest.raises(CreativeWriterError, match=message):
        load_yaml_model(path, SourcesRegistry)
```

Add a parameterized duplicate test:

```python
@pytest.mark.parametrize(
    ("second_id", "second_markdown", "message"),
    [
        ("the-star", "text/selected-short-fiction/second.md", "retained selection IDs must be unique"),
        ("second-story", "text/selected-short-fiction/the-star.md", "retained selection Markdown paths must be unique"),
    ],
)
def test_retained_source_rejects_duplicate_selection_identity(
    tmp_path: Path, second_id: str, second_markdown: str, message: str
) -> None:
    derived = f"""    selections:
      - id: the-star
        title: The Star
        first_published: 1897
        input: epub/text/the-star.xhtml
        markdown: text/selected-short-fiction/the-star.md
        markdown_sha256: {'c' * 64}
      - id: {second_id}
        title: Second Story
        first_published: 1898
        input: epub/text/second-story.xhtml
        markdown: {second_markdown}
        markdown_sha256: {'d' * 64}"""
    path = tmp_path / "sources.yml"
    path.write_text(_retained_record_yaml(derived), encoding="utf-8")
    with pytest.raises(CreativeWriterError, match=message):
        load_yaml_model(path, SourcesRegistry)
```

- [ ] **Step 2: Run the new model tests and confirm RED**

Run:

```zsh
uv run pytest tests/test_source_models.py -q
```

Expected: failures because `markdown_sha256`, retained selections, and shape invariants are not yet modeled.

- [ ] **Step 3: Implement the retained selection and shape models**

Add `PurePosixPath` to the imports and implement:

```python
SHA256_PATTERN = r"^[0-9a-f]{64}$"


def _is_safe_relative_path(value: str) -> bool:
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and "." not in path.parts


class RetainedSourceFiles(BaseModel):
    model_config = ConfigDict(extra="forbid")

    epub: NonEmptyStr
    epub_sha256: str = Field(pattern=SHA256_PATTERN)
    markdown: NonEmptyStr | None = None
    markdown_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_markdown_pair(self) -> "RetainedSourceFiles":
        if (self.markdown is None) != (self.markdown_sha256 is None):
            raise ValueError("markdown and markdown_sha256 must be supplied together")
        return self


class RetainedSourceSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Slug
    title: NonEmptyStr
    first_published: int = Field(ge=1800, le=2100)
    input: NonEmptyStr
    markdown: NonEmptyStr
    markdown_sha256: str = Field(pattern=SHA256_PATTERN)

    @field_validator("input")
    @classmethod
    def validate_input(cls, value: str) -> str:
        if not _is_safe_relative_path(value) or not value.endswith(".xhtml"):
            raise ValueError("selection input must be a relative XHTML member")
        return value

    @field_validator("markdown")
    @classmethod
    def validate_markdown(cls, value: str) -> str:
        if not _is_safe_relative_path(value) or not value.startswith("text/") or not value.endswith(".md"):
            raise ValueError("selection markdown must be below text/ and end in .md")
        return value
```

Extend `RetainedSourceRecord`:

```python
    selections: list[RetainedSourceSelection] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_derived_shape(self) -> "RetainedSourceRecord":
        has_full_work = self.files.markdown is not None
        has_selections = bool(self.selections)
        if has_full_work == has_selections:
            raise ValueError("retained source must use exactly one derived-text shape")
        ids = [selection.id for selection in self.selections]
        if len(ids) != len(set(ids)):
            raise ValueError("retained selection IDs must be unique")
        markdown_paths = [selection.markdown for selection in self.selections]
        if len(markdown_paths) != len(set(markdown_paths)):
            raise ValueError("retained selection Markdown paths must be unique")
        return self
```

- [ ] **Step 4: Run model tests and the existing suite**

Run:

```zsh
uv run pytest tests/test_source_models.py -q
uv run pytest -q
```

Expected: model tests pass. Do not weaken the model to accept unpinned
full-work Markdown.

Before the full-suite run, migrate `_write_fixture` in
`tests/test_source_admission.py`: hash the two Markdown fixture files after
writing them and add their `markdown_sha256` values to the generated
`sources.yml`. Make no admission-check behavior changes in this task. The
full suite must then pass; do not leave a known schema-transition failure for
Task 2.

- [ ] **Step 5: Commit the model layer**

Before committing, update all test-local valid retained-source fixtures in `tests/test_source_models.py` to include `markdown_sha256`, so Task 1 is independently green.

```zsh
git add src/creative_writer/models.py tests/test_source_models.py tests/test_source_admission.py
git commit -m "Model fingerprinted source selections"
```

---

### Task 2: Validate and Report Exact Derived Witnesses

**Files:**
- Modify: `src/creative_writer/source_admission.py`
- Modify: `tests/test_source_admission.py`

**Interfaces:**
- Consumes: `RetainedSourceRecord.files.markdown`, `.markdown_sha256`, and `.selections` from Task 1.
- Produces: blocking archive-member, path, UTF-8, content, packaging, fingerprint, parity, excluded-artifact, and exact physical-inventory validation; full-work and selected-witness report rendering.

- [ ] **Step 1: Extend the admission fixture with selected-witness helpers**

Task 1 has already added the two full-work Markdown hashes to
`_write_fixture`. Extend `_write_minimal_epub` so tests can place literary
members in the archive:

```python
def _write_minimal_epub(
    path: Path,
    *,
    mimetype: str = "application/epub+zip",
    container: str | None = None,
    package_path: str | None = "EPUB/package.opf",
    members: dict[str, str] | None = None,
) -> None:
    if container is None and package_path is not None:
        container = f"""<?xml version="1.0" encoding="UTF-8"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles>
    <rootfile full-path="{package_path}" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", mimetype)
        if container is not None:
            archive.writestr("META-INF/container.xml", container)
        if package_path is not None:
            archive.writestr(
                package_path,
                """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="id">fixture</dc:identifier>
    <dc:title>Fixture</dc:title>
    <dc:language>en</dc:language>
  </metadata>
  <manifest/>
  <spine/>
</package>
""",
            )
        for member, content in (members or {}).items():
            archive.writestr(member, content)
```

Add these complete YAML mutation helpers:

```python
def _write_yaml(path: Path, data: object) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _make_witness_omnibus(story: Path) -> None:
    epub = story / "original" / "witness.epub"
    _write_minimal_epub(
        epub,
        members={"epub/text/the-star.xhtml": "<html><body><p>Star source.</p></body></html>"},
    )
    markdown = story / "original" / "text" / "selected-short-fiction" / "the-star.md"
    markdown.parent.mkdir(parents=True)
    markdown.write_text("The selected star witness.\n", encoding="utf-8")

    admission_path = story / "source-study" / "admission.yml"
    admission = yaml.safe_load(admission_path.read_text(encoding="utf-8"))
    planned = next(item for item in admission["sources"] if item["id"] == "witness")
    planned["selections"] = [
        {
            "id": "the-star",
            "title": "The Star",
            "first_published": 1897,
            "analytical_roles": ["catastrophe"],
        }
    ]
    _write_yaml(admission_path, admission)

    registry_path = story / "original" / "sources.yml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    retained = next(item for item in registry["sources"] if item["id"] == "witness")
    retained["files"] = {
        "epub": "witness.epub",
        "epub_sha256": hashlib.sha256(epub.read_bytes()).hexdigest(),
    }
    retained["selections"] = [
        {
            "id": "the-star",
            "title": "The Star",
            "first_published": 1897,
            "input": "epub/text/the-star.xhtml",
            "markdown": "text/selected-short-fiction/the-star.md",
            "markdown_sha256": hashlib.sha256(markdown.read_bytes()).hexdigest(),
        }
    ]
    _write_yaml(registry_path, registry)


def _mutate_omnibus_fixture(story: Path, mutation: str) -> None:
    admission_path = story / "source-study" / "admission.yml"
    registry_path = story / "original" / "sources.yml"
    admission = yaml.safe_load(admission_path.read_text(encoding="utf-8"))
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    planned = next(item for item in admission["sources"] if item["id"] == "witness")
    retained = next(item for item in registry["sources"] if item["id"] == "witness")
    selection = retained["selections"][0]
    epub = story / "original" / "witness.epub"
    markdown = story / "original" / selection["markdown"]

    if mutation == "missing-retained-selection":
        full_markdown = story / "original" / "text" / "witness.md"
        retained["files"]["markdown"] = "text/witness.md"
        retained["files"]["markdown_sha256"] = hashlib.sha256(full_markdown.read_bytes()).hexdigest()
        retained["selections"] = []
    elif mutation == "extra-retained-selection":
        second_markdown = markdown.parent / "second-story.md"
        second_markdown.write_text("Second selected witness.\n", encoding="utf-8")
        _write_minimal_epub(
            epub,
            members={
                "epub/text/the-star.xhtml": "<html><body><p>Star source.</p></body></html>",
                "epub/text/second-story.xhtml": "<html><body><p>Second source.</p></body></html>",
            },
        )
        retained["files"]["epub_sha256"] = hashlib.sha256(epub.read_bytes()).hexdigest()
        retained["selections"].append(
            {
                "id": "second-story",
                "title": "Second Story",
                "first_published": 1898,
                "input": "epub/text/second-story.xhtml",
                "markdown": "text/selected-short-fiction/second-story.md",
                "markdown_sha256": hashlib.sha256(second_markdown.read_bytes()).hexdigest(),
            }
        )
    elif mutation == "changed-title":
        selection["title"] = "Changed Title"
    elif mutation == "changed-year":
        selection["first_published"] = 1898
    elif mutation == "missing-input-member":
        _write_minimal_epub(epub)
        retained["files"]["epub_sha256"] = hashlib.sha256(epub.read_bytes()).hexdigest()
    elif mutation == "missing-markdown":
        markdown.unlink()
    elif mutation == "bad-markdown-hash":
        selection["markdown_sha256"] = "0" * 64
    elif mutation == "packaging-link":
        markdown.write_text("Text.[1](endnotes.xhtml#note-1)\n", encoding="utf-8")
        selection["markdown_sha256"] = hashlib.sha256(markdown.read_bytes()).hexdigest()
    else:
        raise AssertionError(f"Unknown mutation: {mutation}")

    _write_yaml(admission_path, admission)
    _write_yaml(registry_path, registry)
```

- [ ] **Step 2: Add failing checker and report tests**

Add tests with exact assertions:

```python
def test_source_admission_accepts_and_reports_selected_witness(tmp_path: Path) -> None:
    story = _write_fixture(tmp_path)
    _make_witness_omnibus(story)
    result = check_source_admission(tmp_path, "source-test")
    assert result.ok
    report = result.report_path.read_text(encoding="utf-8")
    assert "- Derived Markdown path: `original/text/selected-short-fiction/the-star.md`" in report
    assert "- Derived Markdown SHA-256: `" in report
    assert "- Derivation input: `epub/text/the-star.xhtml`" in report


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("missing-retained-selection", "selection parity differs"),
        ("extra-retained-selection", "selection parity differs"),
        ("changed-title", "selection parity differs"),
        ("changed-year", "selection parity differs"),
        ("missing-input-member", "selection input member is missing"),
        ("missing-markdown", "Missing or empty derived Markdown"),
        ("bad-markdown-hash", "Markdown SHA-256 mismatch"),
        ("packaging-link", "excluded packaging link"),
    ],
)
def test_source_admission_blocks_invalid_selected_witness(
    tmp_path: Path, mutation: str, expected: str
) -> None:
    story = _write_fixture(tmp_path)
    _make_witness_omnibus(story)
    _mutate_omnibus_fixture(story, mutation)
    result = check_source_admission(tmp_path, "source-test")
    assert not result.ok
    assert any(expected in issue for issue in result.errors)


def test_source_admission_blocks_full_work_markdown_hash_mismatch(tmp_path: Path) -> None:
    story = _write_fixture(tmp_path)
    (story / "original" / "text" / "canonical.md").write_text("Changed.\n", encoding="utf-8")
    result = check_source_admission(tmp_path, "source-test")
    assert not result.ok
    assert any("Markdown SHA-256 mismatch" in issue for issue in result.errors)


def test_source_admission_blocks_undeclared_epub(tmp_path: Path) -> None:
    story = _write_fixture(tmp_path)
    _write_minimal_epub(story / "original" / "undeclared.epub")
    result = check_source_admission(tmp_path, "source-test")
    assert not result.ok
    assert any("Undeclared retained EPUB" in issue for issue in result.errors)


def test_source_admission_blocks_undeclared_markdown(tmp_path: Path) -> None:
    story = _write_fixture(tmp_path)
    (story / "original" / "text" / "undeclared.md").write_text(
        "Undeclared literary text.\n", encoding="utf-8"
    )
    result = check_source_admission(tmp_path, "source-test")
    assert not result.ok
    assert any("Undeclared derived Markdown" in issue for issue in result.errors)


def test_source_admission_blocks_excluded_artifact(tmp_path: Path) -> None:
    story = _write_fixture(tmp_path)
    admission_path = story / "source-study" / "admission.yml"
    admission = yaml.safe_load(admission_path.read_text(encoding="utf-8"))
    control = next(item for item in admission["sources"] if item["id"] == "control")
    control["status"] = "excluded"
    control["authority"] = {"tier": 5, "story_world_canon": False, "style_authority": "none"}
    admission_path.write_text(yaml.safe_dump(admission, sort_keys=False), encoding="utf-8")
    (story / "original" / "control.epub").write_bytes(b"must remain absent")
    result = check_source_admission(tmp_path, "source-test")
    assert not result.ok
    assert any("excluded source" in issue for issue in result.errors)
```

Also update the passing report test to assert the full-work Markdown SHA-256 is shown.
Update `test_source_admission_blocks_proposed_artifact` to expect the new
`artifact exists before corpus admission` wording.

- [ ] **Step 3: Run focused tests and confirm RED**

Run:

```zsh
uv run pytest tests/test_source_admission.py -q
```

Expected: new tests fail because selected witness validation, Markdown hashing, excluded-artifact rejection, and selected-witness reporting do not exist.

- [ ] **Step 4: Implement shared derived-text validation**

Add helpers with these signatures:

```python
def _archive_members(path: Path) -> set[str]:
    with zipfile.ZipFile(path) as archive:
        return set(archive.namelist())


def _append_markdown_errors(
    *, source_id: str, markdown_path: Path, expected_sha256: str, errors: list[str]
) -> None:
    if not markdown_path.is_file():
        errors.append(f"Missing or empty derived Markdown for `{source_id}`: {markdown_path}")
        return
    try:
        markdown = markdown_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"Unable to read derived Markdown for `{source_id}`: {exc}")
        return
    if not markdown.strip():
        errors.append(f"Missing or empty derived Markdown for `{source_id}`: {markdown_path}")
    elif EXCLUDED_PACKAGING_LINK_PATTERN.search(markdown):
        errors.append(f"Derived Markdown for `{source_id}` contains an excluded packaging link.")
    try:
        digest = _sha256(markdown_path)
    except OSError as exc:
        errors.append(f"Unable to hash derived Markdown for `{source_id}`: {exc}")
    else:
        if digest != expected_sha256:
            errors.append(f"Markdown SHA-256 mismatch for `{source_id}`: {markdown_path}")
```

In `_append_parity_errors`, compare planned and retained selection identity as ordered tuples:

```python
planned_selections = [
    (item.id, item.title, item.first_published) for item in source.selections
]
retained_selections = [
    (item.id, item.title, item.first_published) for item in retained.selections
]
if planned_selections != retained_selections:
    errors.append(
        f"`{source.id}` selection parity differs between admission.yml and original/sources.yml."
    )
```

Before the existing EPUB existence branch, initialise
`integrity_error: str | None = None`; assign the result of
`_epub_integrity_error(epub_path)` to it when the EPUB exists. After EPUB
integrity and hash validation, branch on the retained shape:

```python
if retained_source.files.markdown is not None:
    assert retained_source.files.markdown_sha256 is not None
    markdown_path = _story_path(story_dir / "original", retained_source.files.markdown)
    _append_markdown_errors(
        source_id=source.id,
        markdown_path=markdown_path,
        expected_sha256=retained_source.files.markdown_sha256,
        errors=result.errors,
    )
else:
    members = _archive_members(epub_path) if epub_path.is_file() and not integrity_error else set()
    for selection in retained_source.selections:
        selection_id = f"{source.id}/{selection.id}"
        if selection.input not in members:
            result.errors.append(
                f"Retained selection `{selection_id}` input member is missing from EPUB: {selection.input}"
            )
        markdown_path = _story_path(story_dir / "original", selection.markdown)
        _append_markdown_errors(
            source_id=selection_id,
            markdown_path=markdown_path,
            expected_sha256=selection.markdown_sha256,
            errors=result.errors,
        )
```

Catch `_story_path` failures for every Markdown path and continue accumulating errors rather than aborting the report.

Treat every non-admitted artifact at its `planned_path` as blocking. Use status-specific messages so excluded artifacts say `Artifact exists for excluded source` and proposed or approved artifacts say `artifact exists before corpus admission`.

After record-level validation, derive the declared EPUB set from every
`registry.sources[*].files.epub` value and the declared Markdown set from every
full-work `files.markdown` plus every selected witness `selections[*].markdown`.
Require those sets to equal the regular `*.epub` files physically below
`original/` and the regular `*.md` files physically below `original/text/`,
respectively. Report both undeclared physical files and declared paths that are
not physical files as blocking issues.

- [ ] **Step 5: Render full-work and selected-witness records safely**

Replace the unconditional full-work Markdown line in `_render_report` with:

```python
if retained_source.files.markdown is not None:
    lines.extend(
        [
            f"- Derived Markdown path: `original/{retained_source.files.markdown}`",
            f"- Derived Markdown SHA-256: `{retained_source.files.markdown_sha256}`",
        ]
    )
else:
    lines.append("- Retained selections:")
    for selection in retained_source.selections:
        lines.extend(
            [
                f"  - **{selection.title}** ({selection.first_published})",
                f"    - Derivation input: `{selection.input}`",
                f"    - Derived Markdown path: `original/{selection.markdown}`",
                f"    - Derived Markdown SHA-256: `{selection.markdown_sha256}`",
            ]
        )
```

Beside the existing Tier 4 restriction rendering, add:

```python
if source.authority.tier == 5:
    lines.append(
        "- Tier 5 restriction: **Excluded influence only; no retained artifact or positive authority.**"
    )
```

Immediately after `retained_source = retained.get(source.id)`, add:

```python
if source.status == "excluded" and retained_source is None:
    lines.append("- Retained artifact: Intentionally absent.")
```

- [ ] **Step 6: Run focused and full tests**

Run:

```zsh
uv run pytest tests/test_source_models.py tests/test_source_admission.py -q
uv run pytest -q
```

Expected: all tests pass after test-local fixtures are migrated. The repository-level `test_time_expedition_admission_passes` remains on the Phase 1 counts until Task 3 changes the real corpus.

- [ ] **Step 7: Commit the validator layer**

```zsh
git add src/creative_writer/source_admission.py tests/test_source_admission.py
git commit -m "Validate fingerprinted source witnesses"
```

---

### Task 3: Retain the Closed Corpus and Prove the Stop Gate

**Files:**
- Modify: `stories/time-expedition/source-study/admission.yml`
- Modify: `stories/time-expedition/original/sources.yml`
- Create: `stories/time-expedition/original/filters/remove-project-gutenberg-boilerplate.lua`
- Modify: `stories/time-expedition/original/README.md`
- Modify: `stories/time-expedition/source-study/README.md`
- Modify: `stories/time-expedition/source-study/method.md`
- Modify: `tests/test_source_admission.py`
- Create: eight EPUBs below `stories/time-expedition/original/`
- Create: eleven Markdown witnesses below `stories/time-expedition/original/text/`

**Interfaces:**
- Consumes: the fingerprinted schema and admission validator from Tasks 1-2; approved source URLs and authority roles from `source-study/admission.yml` and the Phase 2A design.
- Produces: the exact twelve-artifact retained corpus, thirteen-record admission boundary, reproducible derivation documentation, and passing completion evidence.

- [ ] **Step 1: Change the repository-level smoke test to the final boundary and confirm RED**

Replace the Phase 1 count assertions in `test_time_expedition_admission_passes` with:

```python
assert "- Admitted: 12" in report
assert "- Approved, awaiting retention: 0" in report
assert "- Proposed: 0" in report
assert "- Excluded: 1" in report
assert "| `king-solomons-mines` | admitted | 4 | control |" in report
assert "| `the-lost-world` | excluded | 5 | none |" in report
assert report.count(
    "- Tier 4 restriction: **Negative evidence only; never positive style or continuity authority.**"
) == 5
assert report.count(
    "- Tier 5 restriction: **Excluded influence only; no retained artifact or positive authority.**"
) == 1
for selection_id in (
    "the-plattner-story",
    "the-sea-raiders",
    "the-crystal-egg",
    "the-star",
):
    assert f"text/selected-short-fiction/{selection_id}.md" in report
```

Load both YAML records in the same integration test and additionally require:

- exactly twelve retained records, twelve physical EPUBs, and fifteen physical
  Markdown files below `original/text/`;
- no aggregate Markdown fields or physical aggregate Markdown file for
  `selected-short-fiction`;
- exactly the ordered selection IDs `the-plattner-story`, `the-sea-raiders`,
  `the-crystal-egg`, and `the-star` in both admission and retained records;
- exact Haggard permitted uses in both records and exact prohibited uses in
  both records: `style prescription`, `Time Expedition continuity`, `phrase
  borrowing`, `characters`, `places`, `incidents`, `lost-world content`,
  `imperial assumptions`, `racial ideology`, and `override of a Wells source`.

Run:

```zsh
uv run pytest tests/test_source_admission.py::test_time_expedition_admission_passes -q
```

Expected: FAIL because the actual corpus still has four admitted and seven proposed records.

- [ ] **Step 2: Download all eight approved EPUBs to a fresh temporary directory**

Use the exact URLs already stored for the seven approved records plus the fixed Haggard endpoint:

```zsh
tmpdir=$(mktemp -d /tmp/time-expedition-phase2a.XXXXXX)
curl --fail --location --silent --show-error 'https://standardebooks.org/ebooks/h-g-wells/short-fiction/downloads/h-g-wells_short-fiction.epub?source=download' --output "$tmpdir/h-g-wells_short-fiction.epub"
curl --fail --location --silent --show-error 'https://www.gutenberg.org/ebooks/17508.epub.noimages' --output "$tmpdir/h-g-wells_certain-personal-matters.epub"
curl --fail --location --silent --show-error 'https://www.gutenberg.org/ebooks/21781.epub.noimages' --output "$tmpdir/h-g-wells_text-book-of-biology-part-1.epub"
curl --fail --location --silent --show-error 'https://www.gutenberg.org/ebooks/4340.epub.images' --output "$tmpdir/grant-allen_the-british-barbarians.epub"
curl --fail --location --silent --show-error 'https://www.gutenberg.org/ebooks/21768.epub.noimages' --output "$tmpdir/arthur-conan-doyle_a-desert-drama.epub"
curl --fail --location --silent --show-error 'https://www.gutenberg.org/ebooks/2569.epub.images' --output "$tmpdir/rudyard-kipling_the-days-work.epub"
curl --fail --location --silent --show-error 'https://www.gutenberg.org/ebooks/5164.epub.noimages' --output "$tmpdir/richard-marsh_the-beetle.epub"
curl --fail --location --silent --show-error 'https://standardebooks.org/ebooks/h-rider-haggard/king-solomons-mines/downloads/h-rider-haggard_king-solomons-mines.epub?source=download' --output "$tmpdir/h-rider-haggard_king-solomons-mines.epub"
```

For every archive, run `unzip -t`, verify `mimetype`, parse `META-INF/container.xml`, verify its package document exists, and calculate `shasum -a 256`. If any fresh hash differs from a previously observed planning hash, inspect release/update metadata and record the fresh artifact honestly; never overwrite a pinned retained artifact without explaining the revision in `sources.yml`.

Use this exact structural check:

```zsh
for epub in "$tmpdir"/*.epub; do
  unzip -tq "$epub"
  test "$(unzip -p "$epub" mimetype)" = "application/epub+zip"
  rootfile=$(unzip -p "$epub" META-INF/container.xml | xmllint --xpath 'string(//*[local-name()="rootfile"]/@full-path)' -)
  test -n "$rootfile"
  unzip -Z1 "$epub" | rg -Fx "$rootfile"
  shasum -a 256 "$epub"
done
```

Do not download *The Lost World*.

- [ ] **Step 3: Add and test the Project Gutenberg boilerplate filter**

Create:

```lua
local terminal_headings = {
  ["TRANSCRIBER'S NOTES"] = true,
  ["BACK COVER"] = true,
  ["BACK COVER:"] = true,
}

local leading_note_markers = {
  ["TRANSCRIBER'S NOTE"] = true,
  ["TRANSCRIBER'S NOTE:"] = true,
}

local function normalized_text(block)
  local text = pandoc.utils.stringify(block):gsub("’", "'"):upper():gsub("%s+", " ")
  return text:match("^%s*(.-)%s*$")
end

local function has_class(div, wanted)
  for _, class in ipairs(div.classes) do
    if class == wanted then
      return true
    end
  end
  return false
end

function Div(div)
  if has_class(div, "pg-boilerplate") then
    return {}
  end
end

function Image()
  return {}
end

function Header(header)
  if normalized_text(header) == "FRONT COVER:" then
    return {}
  end
end

function Pandoc(doc)
  local kept = pandoc.List()
  local start_index = 1
  local leading_note_seen = false
  local dropping_terminal_notes = false

  for index, block in ipairs(doc.blocks) do
    if block.t == "HorizontalRule" then
      if leading_note_seen then
        start_index = index + 1
      end
      break
    elseif leading_note_markers[normalized_text(block)] then
      leading_note_seen = true
    end
  end

  for index, block in ipairs(doc.blocks) do
    if index >= start_index then
      if block.t == "Header" and terminal_headings[normalized_text(block)] then
        dropping_terminal_notes = true
      end
      if not dropping_terminal_notes then
        kept:insert(block)
      end
    end
  end

  while #kept > 0 and
      (kept[1].t == "HorizontalRule" or normalized_text(kept[1]) == "") do
    kept:remove(1)
  end
  while #kept > 0 and
      (kept[#kept].t == "HorizontalRule" or normalized_text(kept[#kept]) == "") do
    kept:remove(#kept)
  end

  return pandoc.Pandoc(kept, doc.meta)
end
```

Verify it against a synthetic HTML document containing a `pg-boilerplate`
header, `Front Cover:` heading and image, literary paragraph,
`TRANSCRIBER'S NOTES`, editorial paragraph, `Back Cover:` heading, and
`pg-boilerplate` footer. Pandoc output must contain only the literary
paragraph.

Add a durable regression fixture with literary paragraphs before and after a
non-empty mid-document `pgmonospaced` block. The block must survive intact;
the class alone is not packaging evidence.

Add a second synthetic fixture in which Project Gutenberg credits and a
singular `Transcriber's Note:` precede a horizontal rule and literary text.
The output must begin with the literary text and contain none of the leading
editorial preamble. Run both fixtures under the inherited locale; no
`LC_ALL=C` workaround may be required.

Add a third destructive-case fixture with literary text and a horizontal rule
before a mid-document singular `Transcriber's Note:` marker, followed by
another horizontal rule and more literary text. The output must retain every
block, especially all literary text preceding the later marker. This proves
that leading-note detection stops at the first horizontal rule and no later
marker can move the document start.

- [ ] **Step 4: Extract only the fixed literary inputs**

Unzip each archive beneath the temporary directory and invoke Pandoc with `--from=html --to=gfm-raw_html --wrap=none`. Use both Lua filters for Project Gutenberg sources and the existing packaging-link filter for Standard Ebooks.

The exact inputs are:

- Wells short fiction: only `epub/text/the-plattner-story.xhtml`, `the-sea-raiders.xhtml`, `the-crystal-egg.xhtml`, and `the-star.xhtml`, each to its own Markdown file.
- *Certain Personal Matters*: `OEBPS/4588169185347793760_17508-h-0.htm.html` through `-6.htm.html`.
- *Text Book of Biology, Part 1*: `OEBPS/6496333017750439206_21781-h-0.htm.html` through `-6.htm.html`; `-7` is packaging only and excluded.
- *The British Barbarians*: `OEBPS/137036109479442431_4340-h-0.htm.html` through `-4.htm.html`.
- *A Desert Drama*: `OEBPS/6605053776549637356_21768-h-0.htm.html` through `-6.htm.html` in numeric order; `-6` is the final linear literary member, and the Gutenberg filter removes the terminal licence and packaging matter within it.
- *The Day's Work*: `OEBPS/3331954580391865763_2569-h-1.htm.html` through `-13.htm.html`; title/contents fragment `-0` and packaging fragment `-14` are excluded.
- *The Beetle*: `OEBPS/5766576426201918088_5164-h-0.htm.html` through `-10.htm.html`; the boilerplate filter removes its terminal transcriber notes.
- *King Solomon's Mines*: `epub/text/chapter-1.xhtml` through `chapter-20.xhtml` in numeric order.

Write outputs to the paths fixed in the design. Verify the beginning and end
of every Markdown file manually and search all outputs for `PROJECT
GUTENBERG`, `FULL LICENSE`, `TRANSCRIBER`, `Front Cover`, `Back Cover`,
`colophon.xhtml`, `imprint.xhtml`, `uncopyright.xhtml`, and
`endnotes.xhtml`; every search must be empty.

- [ ] **Step 5: Complete admission and retained-source metadata**

In `admission.yml`:

- change all seven approved candidate records from `proposed` to `admitted`;
- add `king-solomons-mines` as Tier 4 with the exact restrictions in Global Constraints, including the explicit `Time Expedition continuity` prohibition, first publication 1885, Standard Ebooks provenance, and planned path `original/h-rider-haggard_king-solomons-mines.epub`;
- add `the-lost-world` as Tier 5, excluded, first publication 1912, metadata homepage `https://www.gutenberg.org/ebooks/139`, an unacquired planned path `original/arthur-conan-doyle_the-lost-world.epub`, permitted use `post-window negative diagnostic only`, and prohibited uses covering acquisition in Phase 2A, positive style evidence, continuity, phrase borrowing, and story architecture prescription.

In `sources.yml`:

- backfill `markdown_sha256` for the four existing Wells full-work records;
- add the eight newly retained records with observed EPUB and Markdown fingerprints, exact retrieval date, archive release/update metadata, derivation inputs, provenance, rights, and role parity with `admission.yml`;
- represent `selected-short-fiction` with no aggregate `files.markdown` and exactly four retained selections, each with its fixed input, path, and observed Markdown SHA-256;
- do not add *The Lost World*.

Copy the eight verified temporary EPUBs into `stories/time-expedition/original/` only after metadata inspection and conversion verification.

- [ ] **Step 6: Update corpus documentation without beginning analysis**

Update `original/README.md` with:

- the final twelve-source authority map;
- the five Tier 4 negative controls and their bounded roles;
- the unacquired Tier 5 diagnostic boundary;
- the final file inventory;
- exact regeneration commands using the explicit input lists above and both filters;
- a warning that the selected omnibus contains unadmitted works and only the four fingerprinted Markdown files enter analysis.

Update `source-study/README.md` and `method.md` so they state that admission is complete, the corpus is closed at twelve retained plus one excluded record, and detailed analysis remains prohibited pending human review.

Do not create findings, metrics, evidence-ledger entries, style rules, Permian plans, or manuscript prose.

- [ ] **Step 7: Run the corpus and repository completion audit**

Run:

```zsh
make source-admission STORY=time-expedition
make check STORY=time-expedition
make stats STORY=time-expedition
uv run pytest -q
git diff --check
```

Then verify directly:

```zsh
test "$(rg -c '^  - id:' stories/time-expedition/source-study/admission.yml)" -eq 13
test "$(rg -c '^  - id:' stories/time-expedition/original/sources.yml)" -eq 12
test ! -e stories/time-expedition/original/arthur-conan-doyle_the-lost-world.epub
test "$(fd -e epub . stories/time-expedition/original | wc -l | tr -d ' ')" -eq 12
test "$(fd -e md . stories/time-expedition/original/text | wc -l | tr -d ' ')" -eq 15
```

The Markdown count is fifteen: eleven full-work texts plus four selected-story
witnesses. Also require no aggregate omnibus Markdown and require exactly the
four admission/retained selection IDs in their fixed order. Confirm
`ms_statistics.md` still counts only manuscript chapters and does not mention
`original/` or any reference title.

Inspect the generated source admission report and require:

- status PASS;
- twelve admitted, zero approved, zero proposed, one excluded;
- five Tier 4 restriction notices;
- one Tier 5 restriction notice;
- twelve EPUB fingerprints;
- fifteen Markdown fingerprints;
- no blocking issues;
- explicit absence of a retained *Lost World* artifact.

- [ ] **Step 8: Commit the closed corpus foundation**

```zsh
git add tests/test_source_admission.py stories/time-expedition/source-study stories/time-expedition/original
git commit -m "Retain bounded Wells reference corpus"
```

Do not push from the task worker. The orchestrator performs the final whole-branch review, completion audit, and push to `origin/main`.
