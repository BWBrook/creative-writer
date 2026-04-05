from __future__ import annotations

from pathlib import Path

import pytest

from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import load_yaml_model
from creative_writer.models import PlotDevicesRegistry


def test_plot_devices_registry_parses_valid_yaml(tmp_path: Path) -> None:
    registry_path = tmp_path / "plot_devices.yml"
    registry_path.write_text(
        """plot_devices:
  - id: test-device
    name: "Test device"
    narrative_role: "Creates structural pressure."
    description: "Used for schema validation."
    status: active
""",
        encoding="utf-8",
    )

    registry = load_yaml_model(registry_path, PlotDevicesRegistry)

    assert registry.plot_devices[0].id == "test-device"
    assert registry.plot_devices[0].status == "active"


def test_plot_devices_registry_rejects_invalid_status(tmp_path: Path) -> None:
    registry_path = tmp_path / "plot_devices.yml"
    registry_path.write_text(
        """plot_devices:
  - id: test-device
    name: "Test device"
    narrative_role: "Creates structural pressure."
    description: "Used for schema validation."
    status: pending
""",
        encoding="utf-8",
    )

    with pytest.raises(CreativeWriterError):
        load_yaml_model(registry_path, PlotDevicesRegistry)


def test_plot_devices_registry_rejects_invalid_id(tmp_path: Path) -> None:
    registry_path = tmp_path / "plot_devices.yml"
    registry_path.write_text(
        """plot_devices:
  - id: "Bad Device"
    name: "Bad device"
    narrative_role: "Creates structural pressure."
    description: "Used for schema validation."
    status: active
""",
        encoding="utf-8",
    )

    with pytest.raises(CreativeWriterError):
        load_yaml_model(registry_path, PlotDevicesRegistry)
