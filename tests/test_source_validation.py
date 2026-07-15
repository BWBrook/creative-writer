from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading

import pytest

from creative_writer.exceptions import CreativeWriterError
from creative_writer.source_analysis_models import ValidationExpectation, ValidationTarget
from creative_writer.source_validation import (
    VerifiedFreeze,
    open_tier4_controls,
    publish_validation_generation,
    read_current_validation_generation,
)


def _expectation() -> ValidationExpectation:
    return ValidationExpectation.model_validate(
        {
            "heldout_targets": [
                {"id": "heldout-a", "witness_id": "wells-alpha", "role": "observation"}
            ],
            "control_targets": [
                {"id": "control-a", "witness_id": "period-alpha", "role": "comparison"}
            ],
            "heldout_tendency": "The tendency recurs in the held-out target.",
            "disconfirming_result": "The held-out target does not show the tendency.",
            "control_expectation": "The control is comparative only.",
        }
    )


def test_validation_expectation_uses_nonempty_unique_structured_targets() -> None:
    expectation = _expectation()

    assert all(isinstance(target, ValidationTarget) for target in expectation.heldout_targets)
    assert [target.id for target in expectation.control_targets] == ["control-a"]

    with pytest.raises(ValueError, match="unique"):
        ValidationExpectation.model_validate(
            {
                **expectation.model_dump(),
                "heldout_targets": [
                    {"id": "heldout-a", "witness_id": "wells-alpha", "role": "observation"},
                    {"id": "heldout-a", "witness_id": "wells-beta", "role": "observation"},
                ],
            }
        )


def test_forged_freeze_cannot_open_controls() -> None:
    forged = object.__new__(VerifiedFreeze)

    with pytest.raises(CreativeWriterError, match="capability|seal"):
        open_tier4_controls(forged)


def test_wrong_capability_is_rejected_before_any_partition_read(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_reader(*args: object, **kwargs: object) -> bytes:
        raise AssertionError("partition reader must not run for an invalid capability")

    monkeypatch.setattr("creative_writer.source_validation._read_bytes", fail_reader)
    with pytest.raises(CreativeWriterError, match="capability|seal"):
        open_tier4_controls(object())


def test_generation_publication_and_pinned_reader_return_complete_snapshot(tmp_path: Path) -> None:
    validation_root = tmp_path / "validation"
    payloads = {
        "validation-metrics.json": b'{"ok":true}\n',
        "validation-packet.md": b"# packet\n",
        "analysis-report.md": b"# report\n",
    }

    published = publish_validation_generation(validation_root, payloads)
    snapshot = read_current_validation_generation(validation_root)

    assert snapshot.generation_id == published.generation_id
    assert snapshot.bytes == payloads
    assert set(snapshot.paths) == set(payloads)


def test_publication_rejects_symlinked_validation_root(tmp_path: Path) -> None:
    validation_root = tmp_path / "validation"
    validation_root.symlink_to(tmp_path / "outside", target_is_directory=False)
    payloads = {
        "validation-metrics.json": b'{}\n',
        "validation-packet.md": b"# packet\n",
        "analysis-report.md": b"# report\n",
    }

    with pytest.raises(CreativeWriterError, match="symlink|regular directory"):
        publish_validation_generation(validation_root, payloads)


def test_post_swap_parent_fsync_reports_committed_state_and_keeps_new_pointer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    validation_root = tmp_path / "validation"
    old_payloads = {
        "validation-metrics.json": b"old metrics\n",
        "validation-packet.md": b"# old packet\n",
        "analysis-report.md": b"# old report\n",
    }
    new_payloads = {
        "validation-metrics.json": b"new metrics\n",
        "validation-packet.md": b"# new packet\n",
        "analysis-report.md": b"# new report\n",
    }
    publish_validation_generation(validation_root, old_payloads)

    import creative_writer.source_analysis_common as common

    real_fsync = common._fsync_directory

    def fail_after_swap(path: Path) -> None:
        if path == validation_root:
            raise OSError("injected parent fsync failure")
        real_fsync(path)

    monkeypatch.setattr(common, "_fsync_directory", fail_after_swap)
    with pytest.raises(CreativeWriterError) as caught:
        publish_validation_generation(validation_root, new_payloads)

    assert "current advanced" in str(caught.value)
    assert "durability" in str(caught.value)
    assert read_current_validation_generation(validation_root).bytes == new_payloads


def test_unmanaged_current_path_is_rejected(tmp_path: Path) -> None:
    validation_root = tmp_path / "validation"
    validation_root.mkdir(parents=True)
    (validation_root / "current").symlink_to(tmp_path, target_is_directory=True)

    with pytest.raises(CreativeWriterError, match="current|managed|generation"):
        read_current_validation_generation(validation_root)


def test_generation_reuse_is_deterministic_and_pinned_snapshots_remain_stable(tmp_path: Path) -> None:
    validation_root = tmp_path / "validation"
    old_payloads = {
        "validation-metrics.json": b'{"generation":"old"}\n',
        "validation-packet.md": b"# old\n",
        "analysis-report.md": b"# old report\n",
    }
    new_payloads = {
        "validation-metrics.json": b'{"generation":"new"}\n',
        "validation-packet.md": b"# new\n",
        "analysis-report.md": b"# new report\n",
    }

    old = publish_validation_generation(validation_root, old_payloads)
    pinned_old = read_current_validation_generation(validation_root)
    new = publish_validation_generation(validation_root, new_payloads)
    reused_old = publish_validation_generation(validation_root, old_payloads)

    assert new.generation_id != old.generation_id
    assert reused_old.generation_id == old.generation_id
    assert read_current_validation_generation(validation_root).bytes == old_payloads
    assert pinned_old.bytes == old_payloads
    assert len(list((validation_root / "generations").glob("[0-9a-f]" * 64))) == 2


def test_concurrent_readers_observe_only_complete_old_or_new_generations(
    tmp_path: Path,
) -> None:
    validation_root = tmp_path / "validation"
    old_payloads = {
        "validation-metrics.json": b'{"generation":"old"}\n',
        "validation-packet.md": b"# old packet\n",
        "analysis-report.md": b"# old report\n",
    }
    new_payloads = {
        "validation-metrics.json": b'{"generation":"new"}\n' * 4096,
        "validation-packet.md": b"# new packet\n" * 4096,
        "analysis-report.md": b"# new report\n" * 4096,
    }
    publish_validation_generation(validation_root, old_payloads)
    reader_count = 4
    start = threading.Barrier(reader_count + 1)
    old_observed = threading.Barrier(reader_count + 1)
    publisher_done = threading.Event()
    observations: list[dict[str, bytes]] = []
    observations_lock = threading.Lock()

    def observe() -> None:
        snapshot = read_current_validation_generation(validation_root)
        with observations_lock:
            observations.append(snapshot.bytes)

    def read_while_publishing() -> None:
        start.wait(timeout=10)
        observe()
        old_observed.wait(timeout=10)
        while not publisher_done.is_set():
            observe()
        observe()

    def publish_new() -> object:
        start.wait(timeout=10)
        old_observed.wait(timeout=10)
        try:
            return publish_validation_generation(validation_root, new_payloads)
        finally:
            publisher_done.set()

    with ThreadPoolExecutor(max_workers=reader_count + 1) as executor:
        reader_futures = [
            executor.submit(read_while_publishing) for _ in range(reader_count)
        ]
        publisher_future = executor.submit(publish_new)
        published = publisher_future.result(timeout=30)
        for future in reader_futures:
            future.result(timeout=30)

    assert published.bytes == new_payloads
    assert old_payloads in observations
    assert new_payloads in observations
    assert all(item == old_payloads or item == new_payloads for item in observations)


def test_existing_generation_current_swap_failure_preserves_old_pointer_and_retries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    validation_root = tmp_path / "validation"
    old_payloads = {
        "validation-metrics.json": b"old metrics\n",
        "validation-packet.md": b"# old packet\n",
        "analysis-report.md": b"# old report\n",
    }
    new_payloads = {
        "validation-metrics.json": b"new metrics\n",
        "validation-packet.md": b"# new packet\n",
        "analysis-report.md": b"# new report\n",
    }
    publish_validation_generation(validation_root, old_payloads)
    verified_new = publish_validation_generation(validation_root, new_payloads)
    publish_validation_generation(validation_root, old_payloads)

    import creative_writer.source_analysis_common as common

    real_replace = common.os.replace
    failed = False

    def fail_first_current_swap(
        source: str | bytes | Path, destination: str | bytes | Path
    ) -> None:
        nonlocal failed
        if (
            not failed
            and Path(source).name.startswith(".current-")
            and Path(destination) == validation_root / "current"
        ):
            failed = True
            raise OSError("injected current swap failure")
        real_replace(source, destination)

    monkeypatch.setattr(common.os, "replace", fail_first_current_swap)

    with pytest.raises(CreativeWriterError, match="publish validation generation"):
        publish_validation_generation(validation_root, new_payloads)

    assert failed
    assert read_current_validation_generation(validation_root).bytes == old_payloads
    assert not list(validation_root.glob(".current-*"))
    assert (validation_root / "generations" / verified_new.generation_id).is_dir()

    retried = publish_validation_generation(validation_root, new_payloads)

    assert retried.generation_id == verified_new.generation_id
    assert retried.bytes == new_payloads
    assert read_current_validation_generation(validation_root).bytes == new_payloads


def test_publication_failure_before_pointer_swap_preserves_current_and_cleans_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    validation_root = tmp_path / "validation"
    old_payloads = {
        "validation-metrics.json": b"old metrics\n",
        "validation-packet.md": b"old packet\n",
        "analysis-report.md": b"old report\n",
    }
    new_payloads = {
        "validation-metrics.json": b"new metrics\n",
        "validation-packet.md": b"new packet\n",
        "analysis-report.md": b"new report\n",
    }
    publish_validation_generation(validation_root, old_payloads)

    import creative_writer.source_analysis_common as common

    real_replace = common.os.replace

    def fail_generation_rename(source: str | bytes | Path, destination: str | bytes | Path) -> None:
        if ".staging-" in str(source):
            raise OSError("injected publication failure")
        real_replace(source, destination)

    monkeypatch.setattr(common.os, "replace", fail_generation_rename)
    with pytest.raises(CreativeWriterError, match="publish validation generation"):
        publish_validation_generation(validation_root, new_payloads)

    assert read_current_validation_generation(validation_root).bytes == old_payloads
    assert not list((validation_root / "generations").glob(".staging-*"))
