"""钉钉企业邮箱（阿里企业邮）IMAP 采集与 SMTP 连通性服务。"""
from __future__ import annotations

import hashlib
import imaplib
import json
import re
import smtplib
import ssl
from datetime import datetime, timezone
from email import policy
from email.header import decode_header
from email.message import Message
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
from html import unescape
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.email_intelligence import EmailAttachment, EmailMessage
from app.services.email_intelligence import analyze_and_match_email, create_project_activity
from app.services.mail_runtime_config import get_dingtalk_mail_config


def _decode_header(value: Optional[str]) -> str:
    if not value:
        return ""
    parts: list[str] = []
    for fragment, charset in decode_header(value):
        if isinstance(fragment, bytes):
            try:
                parts.append(fragment.decode(charset or "utf-8", errors="replace"))
            except (LookupError, UnicodeDecodeError):
                parts.append(fragment.decode("utf-8", errors="replace"))
        else:
            parts.append(fragment)
    return "".join(parts).strip()


def _decode_payload(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        value = part.get_payload()
        return value if isinstance(value, str) else ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def _html_to_text(value: str) -> str:
    value = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value or "")
    value = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>", "\n", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    value = unescape(value)
    return re.sub(r"[ \t]+", " ", re.sub(r"\n{3,}", "\n\n", value)).strip()


def _extract_bodies(message: Message) -> tuple[str, Optional[str]]:
    plain_parts: list[str] = []
    html_parts: list[str] = []
    parts = message.walk() if message.is_multipart() else [message]
    for part in parts:
        if part.is_multipart() or part.get_content_disposition() == "attachment":
            continue
        content_type = part.get_content_type()
        if content_type == "text/plain":
            plain_parts.append(_decode_payload(part))
        elif content_type == "text/html":
            html_parts.append(_decode_payload(part))
    html = "\n".join(value for value in html_parts if value).strip() or None
    plain = "\n".join(value for value in plain_parts if value).strip()
    if not plain and html:
        plain = _html_to_text(html)
    return plain, html


def _received_at(message: Message) -> datetime:
    try:
        parsed = parsedate_to_datetime(message.get("Date"))
        if parsed:
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError, OverflowError):
        pass
    return datetime.now(timezone.utc)


def _safe_filename(value: str) -> str:
    name = Path(value or "attachment").name
    return re.sub(r"[^\w.()（）\-\u4e00-\u9fff]+", "_", name)[:180] or "attachment"


class DingTalkMailService:
    provider = "dingtalk_mail"

    def __init__(self) -> None:
        self.runtime_config = get_dingtalk_mail_config()
        self.account = self.runtime_config.account_email
        self.password = self.runtime_config.app_password
        self.data_root = Path(__file__).resolve().parents[2] / "data" / "email_intelligence"

    @property
    def configured(self) -> bool:
        return self.runtime_config.configured

    @property
    def enabled(self) -> bool:
        return self.runtime_config.enabled

    def _require_configured(self) -> None:
        if not self.configured:
            raise RuntimeError("请先配置钉钉企业邮箱账号和客户端专用密码/授权码")
        if not self.enabled:
            raise RuntimeError("钉钉企业邮箱接入尚未启用")

    def _ssl_context(self) -> ssl.SSLContext:
        context = ssl.create_default_context()
        # python.org 安装的 macOS Python 可能没有绑定系统 CA；补充系统证书包但保持严格校验。
        system_ca = Path("/etc/ssl/cert.pem")
        if system_ca.exists():
            context.load_verify_locations(cafile=str(system_ca))
        return context

    def _imap(self) -> imaplib.IMAP4_SSL:
        self._require_configured()
        if not settings.DINGTALK_MAIL_IMAP_SSL:
            raise RuntimeError("当前钉钉邮箱接入只允许 IMAP SSL")
        client = imaplib.IMAP4_SSL(
            settings.DINGTALK_MAIL_IMAP_HOST,
            settings.DINGTALK_MAIL_IMAP_PORT,
            ssl_context=self._ssl_context(),
            timeout=settings.DINGTALK_MAIL_TIMEOUT,
        )
        try:
            client.login(self.account, self.password)
        except imaplib.IMAP4.error as exc:
            try:
                client.logout()
            except Exception:
                pass
            raise RuntimeError(
                "邮箱认证失败：请确认 IMAP/SMTP 已开启，并填写第三方客户端专用密码/授权码（不是网页登录密码）"
            ) from exc
        return client

    @staticmethod
    def _folder_name(list_item: bytes | str) -> str:
        """从 IMAP LIST 响应中取目录名；目录本身仍交由服务端原样解析。"""
        value = list_item.decode(errors="replace") if isinstance(list_item, bytes) else list_item
        quoted = re.search(r'"([^"]+)"\s*$', value)
        if quoted:
            return quoted.group(1)
        return value.rsplit(" ", 1)[-1].strip('"')

    def _sync_folders(self, client: imaplib.IMAP4_SSL) -> list[str]:
        """收件箱 + 已发送；配置优先，其次使用 IMAP Special-Use 标记自动发现。"""
        inbox = self.runtime_config.inbox_folder
        configured_sent = (self.runtime_config.sent_folder or "").strip()
        folders = [inbox]
        if configured_sent:
            if configured_sent.casefold() != inbox.casefold():
                folders.append(configured_sent)
            return folders

        status, payload = client.list()
        if status != "OK":
            return folders
        candidates: list[str] = []
        for item in payload or []:
            if not item:
                continue
            raw = item.decode(errors="replace") if isinstance(item, bytes) else item
            name = self._folder_name(item)
            if re.search(r"\\Sent(?:\s|\))", raw, re.IGNORECASE):
                candidates.insert(0, name)
            elif name.casefold() in {"sent", "sent messages", "sent items"}:
                candidates.append(name)
        if candidates and candidates[0].casefold() != inbox.casefold():
            folders.append(candidates[0])
        return folders

    def test_connections(self) -> dict[str, Any]:
        self._require_configured()
        result: dict[str, Any] = {"imap": False, "smtp": False}
        imap_client = self._imap()
        try:
            status, _ = imap_client.select(self.runtime_config.inbox_folder, readonly=True)
            if status != "OK":
                raise RuntimeError(f"无法打开邮箱目录 {self.runtime_config.inbox_folder}")
            result["imap"] = True
        finally:
            try:
                imap_client.logout()
            except Exception:
                pass

        if not settings.DINGTALK_MAIL_SMTP_SSL:
            raise RuntimeError("当前钉钉邮箱接入只允许 SMTP SSL")
        with smtplib.SMTP_SSL(
            settings.DINGTALK_MAIL_SMTP_HOST,
            settings.DINGTALK_MAIL_SMTP_PORT,
            timeout=settings.DINGTALK_MAIL_TIMEOUT,
            context=self._ssl_context(),
        ) as smtp:
            try:
                smtp.login(self.account, self.password)
            except smtplib.SMTPAuthenticationError as exc:
                raise RuntimeError(
                    "邮箱认证失败：请确认 IMAP/SMTP 已开启，并填写第三方客户端专用密码/授权码（不是网页登录密码）"
                ) from exc
            smtp.noop()
            result["smtp"] = True
        return result

    def sync(self, db: Session, max_messages: int, unseen_only: bool = False) -> dict[str, Any]:
        self._require_configured()
        stats: dict[str, Any] = {
            "folders": [],
            "scanned_count": 0,
            "imported_count": 0,
            "duplicate_count": 0,
            "matched_count": 0,
            "activity_count": 0,
            "failed_count": 0,
            "errors": [],
        }
        client = self._imap()
        try:
            folders = self._sync_folders(client)
            for mailbox in folders:
                status, _ = client.select(mailbox, readonly=True)
                if status != "OK":
                    stats["failed_count"] += 1
                    stats["errors"].append(f"无法打开邮箱目录 {mailbox}")
                    continue
                stats["folders"].append(mailbox)
                # 已发送目录不存在“未读”的业务含义，始终扫描其最近邮件。
                criteria = "UNSEEN" if unseen_only and mailbox == self.runtime_config.inbox_folder else "ALL"
                status, payload = client.uid("search", None, criteria)
                if status != "OK":
                    stats["failed_count"] += 1
                    stats["errors"].append(f"邮箱目录 {mailbox} 检索失败")
                    continue
                uids = (payload[0] or b"").split()
                for uid in uids[-max_messages:]:
                    stats["scanned_count"] += 1
                    try:
                        fetch_status, fetched = client.uid("fetch", uid, "(RFC822)")
                        if fetch_status != "OK":
                            raise RuntimeError(f"{mailbox} UID {uid.decode(errors='ignore')} 拉取失败")
                        raw_bytes = next(
                            (part[1] for part in fetched if isinstance(part, tuple) and isinstance(part[1], bytes)),
                            None,
                        )
                        if not raw_bytes:
                            raise RuntimeError("邮件原文为空")
                        imported, matched, activity = self._ingest_raw_message(
                            db, uid.decode(), raw_bytes, mailbox
                        )
                        if imported:
                            stats["imported_count"] += 1
                            stats["matched_count"] += matched
                            stats["activity_count"] += activity
                        else:
                            stats["duplicate_count"] += 1
                        db.commit()
                    except Exception as exc:
                        db.rollback()
                        stats["failed_count"] += 1
                        if len(stats["errors"]) < 10:
                            stats["errors"].append(str(exc)[:300])
        finally:
            try:
                client.logout()
            except Exception:
                pass
        return stats

    def _ingest_raw_message(
        self, db: Session, uid: str, raw_bytes: bytes, mailbox: str
    ) -> tuple[int, int, int]:
        message = BytesParser(policy=policy.default).parsebytes(raw_bytes)
        message_id = str(message.get("Message-ID") or "").strip()
        identity = message_id or f"mailbox:{mailbox}|uid:{uid}"
        external_id = hashlib.sha256(f"{self.account.casefold()}|{identity}".encode()).hexdigest()
        existing = (
            db.query(EmailMessage)
            .filter(EmailMessage.provider == self.provider, EmailMessage.external_id == external_id)
            .first()
        )
        if existing:
            return 0, 0, 0

        subject = _decode_header(message.get("Subject")) or "（无主题）"
        sender_addresses = getaddresses(message.get_all("From", []))
        sender = sender_addresses[0][1] if sender_addresses else _decode_header(message.get("From"))
        recipients = [address for _, address in getaddresses(message.get_all("To", [])) if address]
        cc = [address for _, address in getaddresses(message.get_all("Cc", [])) if address]
        body_text, body_html = _extract_bodies(message)
        references = str(message.get("References") or "").split()
        thread_id = references[0] if references else str(message.get("In-Reply-To") or message_id or "") or None
        received_at = _received_at(message)
        headers = {key: _decode_header(str(value)) for key, value in message.items()}
        item = EmailMessage(
            provider=self.provider,
            external_id=external_id,
            thread_id=thread_id,
            internet_message_id=message_id or None,
            subject=subject,
            sender=sender or "unknown",
            recipients_json=json.dumps(recipients, ensure_ascii=False),
            cc_json=json.dumps(cc, ensure_ascii=False),
            received_at=received_at,
            raw_headers_json=json.dumps(headers, ensure_ascii=False),
            raw_body_text=body_text,
            raw_body_html=body_html,
            match_status="待确认",
            analysis_status="待分析",
        )
        db.add(item)
        db.flush()
        message_dir = self.data_root / str(item.id)
        message_dir.mkdir(parents=True, exist_ok=True)
        eml_path = message_dir / "original.eml"
        eml_path.write_bytes(raw_bytes)
        item.raw_payload_json = json.dumps(
            {"imap_uid": uid, "mailbox": mailbox, "eml_path": str(eml_path)},
            ensure_ascii=False,
        )
        self._save_attachments(db, item, message, message_dir)
        # 原始邮件和附件先独立落库；之后即使外部 AI 暂时不可用，原文也不会丢失。
        db.commit()
        db.refresh(item)

        intelligence = analyze_and_match_email(
            db,
            subject=subject,
            sender=sender or "unknown",
            recipients=recipients,
            cc=cc,
            body=body_text,
            received_at=received_at,
            thread_id=thread_id,
        )
        project = intelligence["project"]
        method = intelligence["match_method"]
        score = intelligence["match_score"]
        analysis = intelligence["analysis"]
        item.project_id = project.id if project else None
        item.match_status = "已自动关联" if project else "待确认"
        item.match_method = method
        item.match_score = score
        item.analysis_status = intelligence["analysis_status"]
        if not intelligence["should_create_activity"]:
            item.analysis_status += "（无需入活动）"
        item.summary = analysis["summary"]
        item.customer_request = analysis["customer_request"]
        item.customer_attitude = analysis["customer_attitude"]
        item.action_items_json = json.dumps(analysis["action_items"], ensure_ascii=False)
        item.risks_json = json.dumps(analysis["risks"], ensure_ascii=False)
        item.analysis_version = intelligence["analysis_version"]
        activity = (
            create_project_activity(db, item)
            if project and intelligence["should_create_activity"]
            else None
        )
        return 1, 1 if project else 0, 1 if activity else 0

    def _save_attachments(self, db: Session, item: EmailMessage, message: Message, message_dir: Path) -> None:
        for index, part in enumerate(message.iter_attachments(), start=1):
            payload = part.get_payload(decode=True) or b""
            filename = _safe_filename(_decode_header(part.get_filename()) or f"attachment-{index}")
            digest = hashlib.sha256(payload).hexdigest()
            path = message_dir / f"{index:03d}-{filename}"
            path.write_bytes(payload)
            db.add(
                EmailAttachment(
                    email_id=item.id,
                    provider_attachment_id=str(part.get("Content-ID") or "") or None,
                    file_name=filename,
                    mime_type=part.get_content_type(),
                    size_bytes=len(payload),
                    storage_path=str(path),
                    sha256=digest,
                    extraction_status="待提取",
                )
            )
