"""统一消息中心运行时配置和调用客户端。

Message Center 负责钉钉等渠道的人员路由与最终投递。本模块只保存调用凭据、
联动场景，并按文档约定提交消息。发送请求不做自动重试，避免产生重复消息。
"""

from __future__ import annotations

import json
import os
import threading
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


_CONFIG_PATH = Path(__file__).resolve().parents[2] / "data" / "message_center_config.json"
_LOCK = threading.Lock()

DEFAULT_RULES: list[dict[str, Any]] = [
    {
        "scene_key": "project_activity",
        "scene_name": "项目动态",
        "business_domain": "项目",
        "description": "项目活动、客户反馈或重要推进形成消息事件。",
        "enabled": False,
        "category": "sales",
        "source_category": "project_event",
        "priority": "normal",
        "route_mode": "ai",
        "target_id": None,
        "target_name": None,
        "rollout_status": "基础已就绪",
    },
    {
        "scene_key": "risk_alert",
        "scene_name": "风险预警",
        "business_domain": "项目",
        "description": "重大项目风险、长期停滞或承诺超时触发消息。",
        "enabled": False,
        "category": "support",
        "source_category": "risk_alert",
        "priority": "high",
        "route_mode": "ai",
        "target_id": None,
        "target_name": None,
        "rollout_status": "基础已就绪",
    },
    {
        "scene_key": "presales_event",
        "scene_name": "售前推进",
        "business_domain": "售前",
        "description": "方案澄清、技术交流、POC 等售前事项流转。",
        "enabled": False,
        "category": "requirement",
        "source_category": "presales_event",
        "priority": "normal",
        "route_mode": "ai",
        "target_id": None,
        "target_name": None,
        "rollout_status": "待业务接入",
    },
    {
        "scene_key": "implementation_event",
        "scene_name": "实施交付",
        "business_domain": "实施",
        "description": "实施排期、交付阻塞、验收等事项流转。",
        "enabled": False,
        "category": "support",
        "source_category": "implementation_event",
        "priority": "normal",
        "route_mode": "ai",
        "target_id": None,
        "target_name": None,
        "rollout_status": "待业务接入",
    },
    {
        "scene_key": "business_event",
        "scene_name": "商务进展",
        "business_domain": "商务",
        "description": "报价、合同、付款等商务节点形成消息。",
        "enabled": False,
        "category": "sales",
        "source_category": "business_event",
        "priority": "normal",
        "route_mode": "ai",
        "target_id": None,
        "target_name": None,
        "rollout_status": "待业务接入",
    },
    {
        "scene_key": "task_transition",
        "scene_name": "任务流转",
        "business_domain": "任务",
        "description": "任务创建、转交、催办和完成时联动通知。",
        "enabled": False,
        "category": "general",
        "source_category": "task_transition",
        "priority": "normal",
        "route_mode": "ai",
        "target_id": None,
        "target_name": None,
        "rollout_status": "待任务模块接入",
    },
]

DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": False,
    "base_url": "http://message.srun.local:8001",
    "api_key": "",
    "source_system": "ai_project_intelligence",
    "timeout_seconds": 10,
    "linkage_rules": DEFAULT_RULES,
    "updated_at": None,
}


def _stored_payload() -> dict[str, Any]:
    if not _CONFIG_PATH.exists():
        return {}
    try:
        payload = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _merged_rules(stored_rules: Any) -> list[dict[str, Any]]:
    stored_by_key = {
        item.get("scene_key"): item
        for item in stored_rules or []
        if isinstance(item, dict) and item.get("scene_key")
    }
    merged = []
    for default_rule in DEFAULT_RULES:
        item = deepcopy(default_rule)
        item.update(stored_by_key.get(default_rule["scene_key"], {}))
        # 名称、归属和接入状态由系统维护，避免页面把场景定义改乱。
        for immutable in ("scene_key", "scene_name", "business_domain", "description", "rollout_status"):
            item[immutable] = default_rule[immutable]
        merged.append(item)
    return merged


def get_message_center_config() -> dict[str, Any]:
    stored = _stored_payload()
    config = deepcopy(DEFAULT_CONFIG)
    config.update({key: value for key, value in stored.items() if key != "linkage_rules"})
    config["linkage_rules"] = _merged_rules(stored.get("linkage_rules"))
    return config


def get_message_center_config_view() -> dict[str, Any]:
    config = get_message_center_config()
    return {
        "enabled": bool(config["enabled"]),
        "base_url": str(config["base_url"]),
        "api_key_configured": bool(config.get("api_key")),
        "source_system": str(config["source_system"]),
        "timeout_seconds": int(config["timeout_seconds"]),
        "linkage_rules": config["linkage_rules"],
        "updated_at": config.get("updated_at"),
    }


def _normalize_base_url(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    parsed = urlsplit(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("消息中心地址必须是有效的 http 或 https 地址")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("消息中心地址不能包含账号、密码、查询参数或锚点")
    return normalized


def save_message_center_config(
    *,
    enabled: bool,
    base_url: str,
    api_key: Optional[str],
    clear_api_key: bool,
    source_system: str,
    timeout_seconds: int,
    linkage_rules: list[dict[str, Any]],
) -> dict[str, Any]:
    existing = get_message_center_config()
    normalized_url = _normalize_base_url(base_url)
    secret = "" if clear_api_key else ((api_key or "").strip() or existing.get("api_key", ""))
    if enabled and not secret:
        raise ValueError("启用消息联动前，请配置 Message Center Token")

    allowed_scene_keys = {rule["scene_key"] for rule in DEFAULT_RULES}
    received_scene_keys = {rule.get("scene_key") for rule in linkage_rules}
    if received_scene_keys != allowed_scene_keys or len(linkage_rules) != len(DEFAULT_RULES):
        raise ValueError("联动场景不完整，请刷新页面后重新保存")

    rule_payload = _merged_rules(linkage_rules)
    for rule in rule_payload:
        if rule["enabled"] and rule["route_mode"] != "ai" and not rule.get("target_id"):
            raise ValueError(f"{rule['scene_name']}使用指定接收人时必须填写目标 ID")

    payload = {
        "enabled": bool(enabled),
        "base_url": normalized_url,
        "api_key": secret,
        "source_system": source_system.strip(),
        "timeout_seconds": int(timeout_seconds),
        "linkage_rules": rule_payload,
        "updated_at": datetime.now().astimezone().isoformat(),
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
            temp_path.unlink(missing_ok=True)
    return get_message_center_config_view()


def check_message_center_health() -> dict[str, Any]:
    config = get_message_center_config()
    base_url = _normalize_base_url(str(config["base_url"]))
    started = time.monotonic()
    try:
        request = Request(f"{base_url}/health", method="GET")
        with urlopen(request, timeout=float(config["timeout_seconds"])) as response:
            status_code = response.status
            raw_body = response.read().decode("utf-8", errors="replace")
        elapsed = round((time.monotonic() - started) * 1000)
        if status_code < 200 or status_code >= 300:
            raise RuntimeError(f"健康接口返回 HTTP {status_code}")
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            payload = {}
        remote_status = str(payload.get("status", "unknown"))
        is_healthy = remote_status.casefold() in {"ok", "healthy", "up"}
        return {
            "success": is_healthy,
            "message": "Message Center 连接正常" if is_healthy else "接口可访问，但健康状态异常",
            "base_url": base_url,
            "response_time_ms": elapsed,
            "remote_status": remote_status,
        }
    except (HTTPError, URLError, OSError, RuntimeError) as exc:
        return {
            "success": False,
            "message": f"连接失败：{str(exc)}",
            "base_url": base_url,
            "response_time_ms": round((time.monotonic() - started) * 1000),
            "remote_status": None,
        }


def send_scene_message(
    *,
    scene_key: str,
    text: str,
    target_user: Optional[str] = None,
    tags: Optional[list[str]] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """按场景提交消息。调用失败直接抛错，调用方决定是否人工重发。"""
    config = get_message_center_config()
    if not config["enabled"]:
        raise RuntimeError("消息联动尚未启用")
    if not config.get("api_key"):
        raise RuntimeError("Message Center Token 尚未配置")
    rule = next((item for item in config["linkage_rules"] if item["scene_key"] == scene_key), None)
    if not rule or not rule["enabled"]:
        raise RuntimeError("该联动场景尚未启用")

    payload: dict[str, Any] = {
        "text": text,
        "source_system": config["source_system"],
        "priority": rule["priority"],
        "category": rule["category"],
        "tags": tags or [],
        "metadata": {**(metadata or {}), "source_category": rule["source_category"]},
    }
    if target_user:
        payload["target_user"] = target_user
    if rule["route_mode"] != "ai" and rule.get("target_id"):
        target_type = "dingtalk_user" if rule["route_mode"] == "user" else "dingtalk_employee_group"
        payload["suggested_recipients"] = [
            {
                "target_type": target_type,
                "target_id": rule["target_id"],
                "target_name": rule.get("target_name"),
                "reason": f"由 {rule['scene_name']} 联动规则指定",
            }
        ]

    request = Request(
        f"{_normalize_base_url(config['base_url'])}/messages",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "X-API-Key": config["api_key"],
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=float(config["timeout_seconds"])) as response:
        raw_body = response.read().decode("utf-8", errors="replace")
    return json.loads(raw_body)
