"""本地企业邮箱运行时配置。

第三方安全密码仅保存在后端本机、权限为 0600 的文件中；API 永不回传密码。
环境变量仍可作为初始配置，页面保存的本地配置优先。
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.core.config import settings


_CONFIG_PATH = Path(__file__).resolve().parents[2] / "data" / "mail_credentials.json"
_LOCK = threading.Lock()


@dataclass(frozen=True)
class DingTalkMailRuntimeConfig:
    enabled: bool
    account_email: str
    app_password: str
    inbox_folder: str
    sent_folder: Optional[str]

    @property
    def configured(self) -> bool:
        return bool(self.account_email and self.app_password)


def _stored_payload() -> dict:
    if not _CONFIG_PATH.exists():
        return {}
    try:
        payload = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def get_dingtalk_mail_config() -> DingTalkMailRuntimeConfig:
    payload = _stored_payload()
    return DingTalkMailRuntimeConfig(
        enabled=bool(payload.get("enabled", settings.DINGTALK_MAIL_ENABLED)),
        account_email=str(
            payload.get("account_email", settings.DINGTALK_MAIL_ACCOUNT_EMAIL or "")
        ).strip(),
        app_password=str(
            payload.get("app_password", settings.DINGTALK_MAIL_PASSWORD or "")
        ),
        inbox_folder=str(payload.get("inbox_folder", settings.DINGTALK_MAIL_FOLDER)).strip() or "INBOX",
        sent_folder=(
            str(payload.get("sent_folder")).strip()
            if payload.get("sent_folder") is not None
            else settings.DINGTALK_MAIL_SENT_FOLDER
        ) or None,
    )


def save_dingtalk_mail_config(
    *,
    enabled: bool,
    account_email: str,
    app_password: Optional[str],
    sent_folder: Optional[str],
    clear_password: bool = False,
) -> DingTalkMailRuntimeConfig:
    account_email = account_email.strip().casefold()
    if account_email and ("@" not in account_email or account_email.startswith("@")):
        raise ValueError("请输入有效的企业邮箱账号")

    existing = get_dingtalk_mail_config()
    password = "" if clear_password else (app_password.strip() if app_password else existing.app_password)
    if enabled and (not account_email or not password):
        raise ValueError("启用邮箱同步前，请填写邮箱账号和第三方安全密码")

    payload = {
        "enabled": bool(enabled),
        "account_email": account_email,
        "app_password": password,
        "inbox_folder": existing.inbox_folder or "INBOX",
        "sent_folder": (sent_folder or "").strip() or None,
    }
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = _CONFIG_PATH.with_suffix(".tmp")
    with _LOCK:
        fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_path, 0o600)
            temp_path.replace(_CONFIG_PATH)
            os.chmod(_CONFIG_PATH, 0o600)
        finally:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
    return DingTalkMailRuntimeConfig(**payload)
