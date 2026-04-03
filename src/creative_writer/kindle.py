"""Send-to-Kindle delivery helpers."""

from __future__ import annotations

import os
import smtplib
import ssl
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr
from getpass import getpass
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from creative_writer.building import build_story
from creative_writer.exceptions import CreativeWriterError
from creative_writer.files import ensure_directory, load_yaml_model
from creative_writer.models import StoryConfig

LOCAL_CONFIG_ENV_VAR = "CREATIVE_WRITER_LOCAL_CONFIG"
DEFAULT_LOCAL_CONFIG_NAME = ".creative-writer.local.yml"
DEFAULT_KEYCHAIN_SERVICE = "creative-writer/gmail-smtp"


class KindleConfig(BaseModel):
    """Local Send-to-Kindle settings."""

    model_config = ConfigDict(extra="forbid")

    send_to: str = Field(min_length=1)
    sender: str = Field(min_length=1)
    sender_name: str = "Creative Writer"
    subject_prefix: str = ""


class SmtpConfig(BaseModel):
    """Local SMTP delivery settings."""

    model_config = ConfigDict(extra="forbid")

    host: str = "smtp.gmail.com"
    port: int = Field(default=465, ge=1, le=65535)
    security: Literal["ssl", "starttls"] = "ssl"
    username: str = Field(min_length=1)
    password_env: str = "CREATIVE_WRITER_SMTP_PASSWORD"
    keychain_service: str | None = DEFAULT_KEYCHAIN_SERVICE
    keychain_account: str | None = None


class LocalDeliveryConfig(BaseModel):
    """Untracked repo-local delivery config."""

    model_config = ConfigDict(extra="forbid")

    kindle: KindleConfig
    smtp: SmtpConfig


@dataclass(slots=True)
class KindleDeliveryResult:
    """Result metadata for a Kindle preflight or send."""

    story_slug: str
    story_title: str
    attachment_path: Path
    config_path: Path
    report_path: Path
    recipient: str
    sender: str
    smtp_host: str
    smtp_port: int
    smtp_security: str
    password_source: str
    sent: bool


def local_delivery_config_path(root: Path) -> Path:
    """Return the path for the repo-local delivery config."""

    override = os.environ.get(LOCAL_CONFIG_ENV_VAR)
    if override:
        path = Path(override).expanduser()
        if not path.is_absolute():
            path = root / path
        return path.resolve()
    return (root / DEFAULT_LOCAL_CONFIG_NAME).resolve()


def _example_config_path(root: Path) -> Path:
    return root / "config" / "kindle.example.yml"


def load_local_delivery_config(root: Path) -> tuple[Path, LocalDeliveryConfig]:
    """Load the untracked local delivery config."""

    path = local_delivery_config_path(root)
    if not path.exists():
        raise CreativeWriterError(
            "Missing local Kindle delivery config.\n"
            f"Expected: {path}\n"
            f"Start from: {_example_config_path(root)}"
        )

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise CreativeWriterError(f"Invalid YAML in {path}: {exc}") from exc

    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise CreativeWriterError(
            f"YAML in {path} must parse to a mapping, not {type(raw).__name__}."
        )

    try:
        return path, LocalDeliveryConfig.model_validate(raw)
    except ValidationError as exc:
        raise CreativeWriterError(f"Schema validation failed for {path}:\n{exc}") from exc


def _keychain_account(config: SmtpConfig) -> str:
    return config.keychain_account or config.username


def _read_keychain_password(service: str, account: str) -> str | None:
    command = [
        "security",
        "find-generic-password",
        "-w",
        "-s",
        service,
        "-a",
        account,
    ]
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise CreativeWriterError("The macOS `security` tool is not available.") from exc
    except subprocess.CalledProcessError:
        return None

    password = completed.stdout.strip()
    return password or None


def resolve_smtp_password(config: SmtpConfig) -> tuple[str, str]:
    """Resolve the SMTP password from env or macOS Keychain."""

    env_name = config.password_env.strip()
    if env_name:
        env_value = os.environ.get(env_name)
        if env_value:
            return env_value, f"env:{env_name}"

    if config.keychain_service:
        account = _keychain_account(config)
        password = _read_keychain_password(config.keychain_service, account)
        if password:
            return password, f"keychain:{config.keychain_service}:{account}"

    keychain_hint = ""
    if config.keychain_service:
        keychain_hint = (
            "\nOr store it in the macOS Keychain with:\n"
            f"  security add-generic-password -U -a \"{_keychain_account(config)}\" "
            f"-s \"{config.keychain_service}\" -w '<app-password>'"
        )

    raise CreativeWriterError(
        "No SMTP password is configured for Kindle delivery.\n"
        f"Set {env_name} in the environment{keychain_hint}\n"
        "Or run `make kindle-store-password` to add it interactively."
    )


def store_smtp_password(root: Path, password: str | None = None) -> str:
    """Store the SMTP password in the macOS Keychain."""

    _, config = load_local_delivery_config(root)
    service = config.smtp.keychain_service or DEFAULT_KEYCHAIN_SERVICE
    account = _keychain_account(config.smtp)

    secret = password if password is not None else getpass(
        f"Gmail SMTP password for {account}: "
    )
    if not secret.strip():
        raise CreativeWriterError("No SMTP password was provided.")

    command = [
        "security",
        "add-generic-password",
        "-U",
        "-a",
        account,
        "-s",
        service,
        "-w",
        secret,
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise CreativeWriterError("The macOS `security` tool is not available.") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() or exc.stdout.strip() or "unknown security error"
        raise CreativeWriterError(
            f"Could not store the SMTP password in Keychain: {stderr}"
        ) from exc

    return f"{service}:{account}"


def _delivery_report_path(root: Path, story_slug: str) -> Path:
    report_dir = root / "build" / story_slug / "reports"
    ensure_directory(report_dir)
    return report_dir / "kindle-delivery.md"


def _write_delivery_report(
    root: Path,
    result: KindleDeliveryResult,
    status: str,
    note: str,
) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    report = "\n".join(
        [
            f"# Kindle Delivery: {result.story_title}",
            "",
            f"- Story slug: `{result.story_slug}`",
            f"- Status: **{status}**",
            f"- Timestamp (UTC): `{timestamp}`",
            f"- Attachment: `{result.attachment_path}`",
            f"- Local config: `{result.config_path}`",
            f"- Recipient: `{result.recipient}`",
            f"- Sender: `{result.sender}`",
            f"- SMTP: `{result.smtp_host}:{result.smtp_port}` (`{result.smtp_security}`)",
            f"- Password source: `{result.password_source}`",
            f"- Note: {note}",
            "",
        ]
    )
    result.report_path.write_text(report, encoding="utf-8")


def _story_title(root: Path, story_slug: str) -> str:
    story_path = root / "stories" / story_slug / "story.yml"
    story = load_yaml_model(story_path, StoryConfig)
    return story.title


def _prepare_delivery(root: Path, story_slug: str) -> tuple[LocalDeliveryConfig, str, KindleDeliveryResult]:
    config_path, config = load_local_delivery_config(root)
    attachment_path = build_story(root, story_slug, "epub")
    password, password_source = resolve_smtp_password(config.smtp)
    title = _story_title(root, story_slug)
    result = KindleDeliveryResult(
        story_slug=story_slug,
        story_title=title,
        attachment_path=attachment_path,
        config_path=config_path,
        report_path=_delivery_report_path(root, story_slug),
        recipient=config.kindle.send_to,
        sender=config.kindle.sender,
        smtp_host=config.smtp.host,
        smtp_port=config.smtp.port,
        smtp_security=config.smtp.security,
        password_source=password_source,
        sent=False,
    )
    return config, password, result


def kindle_preflight(root: Path, story_slug: str) -> KindleDeliveryResult:
    """Validate Kindle delivery end to end without sending the email."""

    _, _, result = _prepare_delivery(root, story_slug)
    _write_delivery_report(
        root,
        result,
        "READY",
        "EPUB built successfully and SMTP credentials resolved. No email sent.",
    )
    return result


def send_to_kindle(root: Path, story_slug: str) -> KindleDeliveryResult:
    """Build a story EPUB and email it to the configured Kindle address."""

    config, password, result = _prepare_delivery(root, story_slug)

    subject = f"{config.kindle.subject_prefix}{result.story_title}"
    message = EmailMessage()
    message["From"] = formataddr((config.kindle.sender_name, config.kindle.sender))
    message["To"] = config.kindle.send_to
    message["Subject"] = subject
    message.set_content(
        f"Creative Writer is sending '{result.story_title}' to Kindle as an EPUB attachment."
    )
    message.add_attachment(
        result.attachment_path.read_bytes(),
        maintype="application",
        subtype="epub+zip",
        filename=result.attachment_path.name,
    )

    context = ssl.create_default_context()
    try:
        if config.smtp.security == "ssl":
            with smtplib.SMTP_SSL(
                config.smtp.host,
                config.smtp.port,
                context=context,
            ) as smtp:
                smtp.login(config.smtp.username, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(config.smtp.host, config.smtp.port) as smtp:
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.ehlo()
                smtp.login(config.smtp.username, password)
                smtp.send_message(message)
    except OSError as exc:
        raise CreativeWriterError(
            f"SMTP connection failed while sending to Kindle: {exc}"
        ) from exc
    except smtplib.SMTPException as exc:
        raise CreativeWriterError(
            f"SMTP rejected the Kindle delivery attempt: {exc}"
        ) from exc

    result.sent = True
    _write_delivery_report(
        root,
        result,
        "SENT",
        "EPUB emailed to the configured Send-to-Kindle address.",
    )
    return result
