from __future__ import annotations

from pathlib import Path

from creative_writer.kindle import kindle_preflight, send_to_kindle, store_smtp_password
from creative_writer.scaffold import create_story


def _write_local_config(root: Path) -> None:
    (root / ".creative-writer.local.yml").write_text(
        """kindle:
  send_to: "device@kindle.com"
  sender: "author@example.com"
  sender_name: "Creative Writer"
  subject_prefix: ""
smtp:
  host: "smtp.gmail.com"
  port: 465
  security: "ssl"
  username: "author@example.com"
  password_env: "CREATIVE_WRITER_SMTP_PASSWORD"
  keychain_service: "creative-writer/gmail-smtp"
  keychain_account: "author@example.com"
""",
        encoding="utf-8",
    )


def test_kindle_preflight_builds_epub_and_writes_report(
    tmp_path: Path,
    monkeypatch,
) -> None:
    create_story(tmp_path, "kindle-test", "original")
    _write_local_config(tmp_path)
    monkeypatch.setenv("CREATIVE_WRITER_SMTP_PASSWORD", "secret")

    result = kindle_preflight(tmp_path, "kindle-test")

    assert result.attachment_path.exists()
    assert result.report_path.exists()
    assert result.password_source == "env:CREATIVE_WRITER_SMTP_PASSWORD"
    report_text = result.report_path.read_text(encoding="utf-8")
    assert "READY" in report_text
    assert "kindle-test.epub" in report_text


def test_send_to_kindle_uses_smtp_ssl(monkeypatch, tmp_path: Path) -> None:
    create_story(tmp_path, "kindle-send", "original")
    _write_local_config(tmp_path)
    monkeypatch.setenv("CREATIVE_WRITER_SMTP_PASSWORD", "secret")

    attachment = tmp_path / "build" / "kindle-send" / "kindle-send.epub"
    attachment.parent.mkdir(parents=True, exist_ok=True)
    attachment.write_text("fake epub payload", encoding="utf-8")

    sent: dict[str, object] = {}

    class FakeSMTP:
        def __init__(self, host: str, port: int, context=None) -> None:
            sent["host"] = host
            sent["port"] = port
            sent["context"] = context

        def __enter__(self) -> "FakeSMTP":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def login(self, username: str, password: str) -> None:
            sent["username"] = username
            sent["password"] = password

        def send_message(self, message) -> None:
            sent["message"] = message

    monkeypatch.setattr(
        "creative_writer.kindle.build_story",
        lambda root, story_slug, target: attachment,
    )
    monkeypatch.setattr("creative_writer.kindle.smtplib.SMTP_SSL", FakeSMTP)

    result = send_to_kindle(tmp_path, "kindle-send")

    assert result.sent
    assert sent["host"] == "smtp.gmail.com"
    assert sent["port"] == 465
    assert sent["username"] == "author@example.com"
    assert sent["password"] == "secret"
    message = sent["message"]
    assert message["To"] == "device@kindle.com"
    assert message["Subject"] == "Kindle Send"
    assert len(list(message.iter_attachments())) == 1


def test_store_smtp_password_uses_security_command(monkeypatch, tmp_path: Path) -> None:
    create_story(tmp_path, "keychain-test", "original")
    _write_local_config(tmp_path)

    commands: list[list[str]] = []

    def fake_run(command: list[str], check: bool, capture_output: bool, text: bool):
        commands.append(command)

        class Completed:
            stdout = ""
            stderr = ""

        return Completed()

    monkeypatch.setattr("creative_writer.kindle.getpass", lambda prompt: "app-secret")
    monkeypatch.setattr("creative_writer.kindle.subprocess.run", fake_run)

    key = store_smtp_password(tmp_path)

    assert key == "creative-writer/gmail-smtp:author@example.com"
    assert commands == [
        [
            "security",
            "add-generic-password",
            "-U",
            "-a",
            "author@example.com",
            "-s",
            "creative-writer/gmail-smtp",
            "-w",
            "app-secret",
        ]
    ]
