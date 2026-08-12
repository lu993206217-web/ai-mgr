"""
项目活动日报同步服务

负责调用外部日报接口、自动匹配本地项目、导入日报事实为活动日志。
"""
from __future__ import annotations

import hashlib
import re
import json
import ssl
import time as time_module
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from difflib import SequenceMatcher
from typing import Any, Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.activity_log import ActivityLog
from app.models.customer import Customer
from app.models.daily_report import (
    DailyReportActivityMapping,
    DailyReportBinding,
    DailyReportProjectAlias,
    DailyReportRawEntry,
    DailyReportSyncRun,
    DailyReportUnmatchedProject,
)
from app.models.enums import ActivitySource, ActivityType, NextAction
from app.models.project import Project
from app.models.user import User


STAGE_LABELS = {
    "pre_sales": "售前",
    "implementation": "实施",
    "service": "服务",
    "unassigned": "未分类",
}

@dataclass
class MatchResult:
    project: Optional[Project]
    score: float
    method: str


class DailyReportClient:
    """外部项目活动日报接口客户端。"""

    def __init__(self) -> None:
        self.base_url = settings.DAILY_REPORT_API_BASE_URL.rstrip("/")
        self.headers = {}
        if settings.DAILY_REPORT_API_KEY:
            self.headers[settings.DAILY_REPORT_API_KEY_HEADER] = settings.DAILY_REPORT_API_KEY

    def _request(self, method: str, path: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        query = f"?{urllib.parse.urlencode(params)}" if params else ""
        url = f"{self.base_url}{path}{query}"
        return self._normalize_payload(self._open_json(method, url))

    def _open_json(self, method: str, url: str, allow_http_fallback: bool = True) -> dict[str, Any]:
        context = self._ssl_context(url)
        request = urllib.request.Request(url, method=method, headers=self.headers)
        try:
            with urllib.request.urlopen(
                request,
                timeout=settings.DAILY_REPORT_API_TIMEOUT,
                context=context,
            ) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload) if payload else {}
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code == 403 and "FORBIDDEN_SCOPE" in body:
                raise RuntimeError(
                    f"日报接口鉴权通过但权限不足：{body[:300]}"
                ) from exc
            raise RuntimeError(f"日报接口返回 HTTP {exc.code}: {body[:300]}") from exc
        except (ssl.SSLError, URLError) as exc:
            if (
                allow_http_fallback
                and settings.DAILY_REPORT_API_ALLOW_HTTP_FALLBACK
                and url.startswith("https://")
                and self._is_tls_handshake_failure(exc)
            ):
                fallback_url = "http://" + url[len("https://") :]
                return self._open_json(method, fallback_url, allow_http_fallback=False)
            raise RuntimeError(f"日报接口连接失败: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"日报接口返回内容不是有效 JSON: {exc}") from exc

    def _ssl_context(self, url: str) -> Optional[ssl.SSLContext]:
        if url.startswith("https://") and not settings.DAILY_REPORT_API_VERIFY_SSL:
            context = ssl._create_unverified_context()
            context.check_hostname = False
            return context
        return None

    def _is_tls_handshake_failure(self, exc: BaseException) -> bool:
        reason = exc.reason if isinstance(exc, URLError) else exc
        message = str(reason).lower()
        return any(
            marker in message
            for marker in (
                "unexpected_eof",
                "wrong version number",
                "ssl",
                "eof occurred in violation of protocol",
            )
        )

    def trigger_ingestion(self) -> dict[str, Any]:
        return {"skipped": True, "message": "北向 API Key 不触发内部日报摄入任务"}

    def get_project_options(self, month: str, limit: int = 2000) -> dict[str, Any]:
        return self._request(
            "GET",
            "/api/northbound/v1/project-tracking",
            {"view": "options", "month": month, "limit": limit},
        )

    def get_project_timeline(self, month: str, project_key: str) -> dict[str, Any]:
        return self._request(
            "GET",
            "/api/northbound/v1/project-tracking",
            {"view": "detail", "month": month, "project_key": project_key},
        )

    def get_rd_dynamics(self, target_date: date) -> dict[str, Any]:
        return self._request(
            "GET",
            "/api/northbound/v1/rd-dynamics",
            {"date": target_date.isoformat()},
        )

    def _normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if isinstance(payload.get("data"), dict):
            return payload["data"]
        return payload


class DeepSeekDailyReportAnalyzer:
    """使用 DeepSeek 对已落库的原始日报做结构化分析。"""

    def analyze(
        self,
        item: dict[str, Any],
        projects: list[Project],
        source_date: date,
        bound_project: Optional[Project] = None,
        project_aliases: Optional[dict[UUID, list[str]]] = None,
    ) -> dict[str, Any]:
        if not settings.DAILY_REPORT_AI_ENABLED:
            raise RuntimeError("日报 AI 分析未启用")
        if not settings.DEEPSEEK_API_KEY:
            raise RuntimeError("DeepSeek API Key 未配置")

        candidates = [
            {
                "project_id": str(project.id),
                "project_name": project.project_name,
                "country": project.country,
                "customer": project.customer.customer_name if project.customer else None,
                "channel": project.channel.channel_name if project.channel else None,
                "known_daily_report_aliases": (project_aliases or {}).get(project.id, []),
            }
            for project in projects
        ]
        payload = {
            "source_date": source_date.isoformat(),
            "bound_project_id": str(bound_project.id) if bound_project else None,
            "raw_log": item,
            "candidate_projects": candidates,
        }
        system_prompt = (
            "你是项目日报情报分析器。只返回一个 JSON 对象，不要返回 Markdown。"
            "必须从 candidate_projects 中选择 project_id；无法可靠判断时返回 null。"
            "bound_project_id 非空时必须沿用该项目。"
            "一个本地项目可以对应多个日报名称、简称和历史名称；known_daily_report_aliases 是人工确认或历史可靠绑定沉淀的别名，"
            "应结合日报正文、客户、国家和产品语境判断，不要因为日报名称与正式项目名不同就直接判为无关。"
            "activity_time 必须优先采用 raw_log 中日志实际发生、创建或业务日期时间，"
            "绝不能使用当前同步时间；只有原文完全没有时间时才使用 source_date 12:00:00。"
            "activity_type 只能是：进展更新、风险上报、里程碑完成、阻塞等待、其他。"
            "next_action 只能是：等待客户反馈、等待内部审批、等待合同签订、等待验收、其他，"
            "原文没有明确下一步时返回 null；next_action_deadline 必须是 YYYY-MM-DD，无法确定时返回 null。"
            "waiting_party 表示当前等待的客户、渠道或内部对象；blocker_flag 只能是 true 或 false；"
            "risk_reason 必须给出原文中的简短风险依据，没有风险时返回 null。"
            "返回字段：project_id, confidence(0到1), reason, summary, activity_type, activity_time, "
            "next_action, next_action_deadline, waiting_party, blocker_flag, risk_reason。"
        )
        request_body = {
            "model": settings.DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)[:30000]},
            ],
            "temperature": settings.DEEPSEEK_TEMPERATURE,
            "max_tokens": min(settings.DEEPSEEK_MAX_TOKENS, 2048),
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            f"{settings.DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions",
            data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            context = None if settings.DEEPSEEK_VERIFY_SSL else ssl._create_unverified_context()
            with urllib.request.urlopen(
                request,
                timeout=settings.DEEPSEEK_TIMEOUT,
                context=context,
            ) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"DeepSeek 返回 HTTP {exc.code}: {body[:300]}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"DeepSeek 调用失败: {exc}") from exc

        try:
            content = response_payload["choices"][0]["message"]["content"].strip()
            content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content)
            result = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError("DeepSeek 返回的分析结果不是有效结构化 JSON") from exc
        result["_response_meta"] = {
            "id": response_payload.get("id"),
            "model": response_payload.get("model"),
            "usage": response_payload.get("usage"),
        }
        return result


class DailyReportSyncService:
    """项目活动日报同步编排。"""

    def __init__(self, db: Session):
        self.db = db
        self.client = DailyReportClient()
        self.ai_analyzer = DeepSeekDailyReportAnalyzer()

    def sync_month(
        self,
        month: Optional[str] = None,
        lookback_days: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        project_ids: Optional[list[UUID]] = None,
        trigger_type: str = "manual",
        created_by: Optional[UUID] = None,
        trigger_ingestion: bool = False,
    ) -> DailyReportSyncRun:
        run = self.create_sync_run(
            month=month,
            lookback_days=lookback_days,
            start_date=start_date,
            end_date=end_date,
            trigger_type=trigger_type,
            created_by=created_by,
        )
        return self.execute_sync_run(
            run_id=run.id,
            month=month,
            lookback_days=lookback_days,
            start_date=start_date,
            end_date=end_date,
            project_ids=project_ids,
            trigger_ingestion=trigger_ingestion,
        )

    def create_sync_run(
        self,
        month: Optional[str] = None,
        lookback_days: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        trigger_type: str = "manual",
        created_by: Optional[UUID] = None,
    ) -> DailyReportSyncRun:
        target_month = month or datetime.now().strftime("%Y-%m")
        days = lookback_days if lookback_days is not None else settings.DAILY_REPORT_SYNC_LOOKBACK_DAYS
        since_date, until_date = self._resolve_date_window(target_month, days, start_date, end_date)
        months = self._months_between(since_date, until_date)
        run_label = target_month if len(months) == 1 else f"{months[0]}..{months[-1]}"

        run = DailyReportSyncRun(
            month=run_label,
            trigger_type=trigger_type,
            lookback_days=days,
            created_by=created_by,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def execute_sync_run(
        self,
        run_id: UUID,
        month: Optional[str] = None,
        lookback_days: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        project_ids: Optional[list[UUID]] = None,
        trigger_ingestion: bool = False,
    ) -> DailyReportSyncRun:
        run = self.db.query(DailyReportSyncRun).filter(DailyReportSyncRun.id == run_id).first()
        if not run:
            raise ValueError("日报同步任务不存在")
        run.status = "运行中"
        run.error_message = None
        self.db.commit()

        target_month = month or datetime.now().strftime("%Y-%m")
        days = lookback_days if lookback_days is not None else run.lookback_days
        since_date, until_date = self._resolve_date_window(target_month, days, start_date, end_date)
        try:
            if trigger_ingestion:
                self.client.trigger_ingestion()

            stats = self._import_rd_dynamics(
                since_date=since_date,
                until_date=until_date,
                project_ids=project_ids,
                user_id=run.created_by,
                run_id=run.id,
            )
            run.options_count = stats["options_count"]
            run.auto_bound_count = stats["auto_bound_count"]
            run.unmatched_count = stats["unmatched_count"]
            run.imported_activity_count = stats["imported_activity_count"]
            run.skipped_duplicate_count = stats["skipped_duplicate_count"]
            if stats.get("failed_days"):
                failed_days = stats["failed_days"]
                run.error_message = f"部分日期同步跳过：{'；'.join(failed_days[:5])}"
                if len(failed_days) > 5:
                    run.error_message += f"；另有 {len(failed_days) - 5} 天"
            if stats.get("analysis_failed_count"):
                ai_message = f"AI分析失败 {stats['analysis_failed_count']} 条，原始日志已保留可重试"
                run.error_message = f"{run.error_message}；{ai_message}" if run.error_message else ai_message
            run.status = "成功"
            run.finished_at = datetime.now()
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            run = self.db.query(DailyReportSyncRun).filter(DailyReportSyncRun.id == run_id).first()
            if not run:
                raise
            run.status = "失败"
            run.error_message = str(exc)
            run.finished_at = datetime.now()
            self.db.add(run)
            self.db.commit()

        return run

    def _get_active_binding(self, project_key: str) -> Optional[DailyReportBinding]:
        return (
            self.db.query(DailyReportBinding)
            .filter(
                DailyReportBinding.project_key == project_key,
                DailyReportBinding.is_active.is_(True),
            )
            .first()
        )

    def _create_or_update_binding(
        self,
        item: dict[str, Any],
        project: Project,
        match_method: str,
        match_score: float,
        user_id: Optional[UUID],
    ) -> DailyReportBinding:
        project_key = item.get("project_key")
        name = (
            item.get("project_name_normalized")
            or item.get("project_name")
            or item.get("entity_canonical_name")
            or project_key
        )
        binding = self.db.query(DailyReportBinding).filter(DailyReportBinding.project_key == project_key).first()
        if not binding:
            binding = DailyReportBinding(project_key=project_key, created_by=user_id)
            self.db.add(binding)

        binding.project_id = project.id
        binding.external_project_name = name
        binding.match_method = match_method
        binding.match_score = match_score
        binding.is_active = True
        binding.raw_payload = item
        binding.updated_by = user_id
        binding.updated_at = datetime.now()
        self._remember_project_alias(
            project=project,
            alias_name=name,
            project_key=project_key,
            method=match_method,
            confidence=match_score,
        )
        self.db.flush()
        return binding

    def _remember_project_alias(
        self,
        project: Project,
        alias_name: str,
        project_key: Optional[str],
        method: str,
        confidence: float,
    ) -> None:
        normalized = self._normalize_name(alias_name or "")
        if not normalized:
            return
        alias = (
            self.db.query(DailyReportProjectAlias)
            .filter(
                DailyReportProjectAlias.project_id == project.id,
                DailyReportProjectAlias.normalized_alias == normalized,
            )
            .first()
        )
        if not alias:
            alias = DailyReportProjectAlias(
                project_id=project.id,
                normalized_alias=normalized,
            )
            self.db.add(alias)
        alias.alias_name = alias_name
        alias.source_project_key = project_key
        alias.source_method = method
        alias.confidence = confidence
        alias.is_active = True
        alias.updated_at = datetime.now()

    def _project_alias_map(self) -> dict[UUID, list[str]]:
        aliases: dict[UUID, list[str]] = {}
        for project in self.db.query(Project).filter(Project.status != "ARCHIVED").all():
            aliases.setdefault(project.id, []).append(project.project_name)
        for alias in self.db.query(DailyReportProjectAlias).filter(DailyReportProjectAlias.is_active.is_(True)).all():
            names = aliases.setdefault(alias.project_id, [])
            if alias.alias_name not in names:
                names.append(alias.alias_name)
        # 兼容历史数据：未完成别名回填时，已有绑定名称也立即参与分析。
        for binding in self.db.query(DailyReportBinding).filter(DailyReportBinding.is_active.is_(True)).all():
            names = aliases.setdefault(binding.project_id, [])
            if binding.external_project_name and binding.external_project_name not in names:
                names.append(binding.external_project_name)
        return aliases

    def _match_confirmed_alias(
        self,
        item: dict[str, Any],
        projects: list[Project],
        alias_map: dict[UUID, list[str]],
    ) -> Optional[Project]:
        external_name = (
            item.get("project_name_normalized")
            or item.get("project_name")
            or item.get("entity_canonical_name")
            or ""
        )
        normalized = self._normalize_name(str(external_name))
        if not normalized:
            return None
        matched_ids = {
            project_id
            for project_id, names in alias_map.items()
            if any(self._normalize_name(name) == normalized for name in names)
        }
        if len(matched_ids) != 1:
            return None
        matched_id = next(iter(matched_ids))
        return next((project for project in projects if project.id == matched_id), None)

    def _upsert_unmatched(
        self,
        item: dict[str, Any],
        month: str,
        match: MatchResult,
        user_id: Optional[UUID],
    ) -> DailyReportUnmatchedProject:
        project_key = item.get("project_key")
        name = (
            item.get("project_name_normalized")
            or item.get("project_name")
            or item.get("entity_canonical_name")
            or project_key
        )
        record = (
            self.db.query(DailyReportUnmatchedProject)
            .filter(
                DailyReportUnmatchedProject.month == month,
                DailyReportUnmatchedProject.project_key == project_key,
            )
            .first()
        )
        if not record:
            record = DailyReportUnmatchedProject(month=month, project_key=project_key)
            self.db.add(record)

        record.external_project_name = name
        record.active_days = int(item.get("active_days") or 1)
        record.last_active_date = self._parse_date(item.get("last_active_date") or item.get("target_date"))
        record.pre_sales_entry_count = int(item.get("pre_sales_entry_count") or 0)
        record.implementation_entry_count = int(item.get("implementation_entry_count") or 0)
        record.service_entry_count = int(item.get("service_entry_count") or 0)
        suggested_project = match.project if self._can_suggest(match) else None
        record.suggested_project_id = suggested_project.id if suggested_project else None
        record.suggested_project_name = suggested_project.project_name if suggested_project else None
        record.suggested_score = match.score if suggested_project else 0
        record.raw_payload = item
        if record.status == "已绑定":
            record.status = "待处理"
        record.updated_at = datetime.now()
        record.handled_by = user_id if record.status != "待处理" else record.handled_by
        self.db.flush()
        return record

    def _match_project(self, item: dict[str, Any]) -> MatchResult:
        external_names = [
            item.get("project_name_normalized"),
            item.get("project_name"),
            item.get("entity_canonical_name"),
            item.get("customer_entity_id"),
            item.get("project_entity_id"),
        ]
        external_names = [name for name in external_names if name]
        if not external_names:
            return MatchResult(project=None, score=0, method="none")

        projects = (
            self.db.query(Project)
            .outerjoin(Customer, Project.customer_id == Customer.id)
            .filter(Project.status != "ARCHIVED")
            .all()
        )

        best_project = None
        best_score = 0.0
        best_method = "similarity"
        for project in projects:
            local_names = [
                project.project_name,
                project.customer.customer_name if project.customer else None,
                project.channel.channel_name if project.channel else None,
            ]
            local_names = [name for name in local_names if name]
            for external_name in external_names:
                for local_name in local_names:
                    score, method = self._score_name(local_name, external_name)
                    if score > best_score:
                        best_project = project
                        best_score = score
                        best_method = method

        return MatchResult(project=best_project, score=best_score, method=best_method)

    def _score_name(self, local_name: str, external_name: str) -> tuple[float, str]:
        local = self._normalize_name(local_name)
        external = self._normalize_name(external_name)
        if not local or not external:
            return 0, "empty"
        if local == external:
            return 1.0, "exact"
        if local in external or external in local:
            coverage = min(len(local), len(external)) / max(len(local), len(external))
            return max(0.9, coverage), "contains"
        return SequenceMatcher(None, local, external).ratio(), "similarity"

    def _normalize_name(self, value: str) -> str:
        value = value.lower().strip()
        value = re.sub(r"[\s\-_（）()【】\\[\\]，,。.·]", "", value)
        value = re.sub(r"(有限公司|有限责任公司|股份有限公司|集团|公司|项目)$", "", value)
        return value

    def _import_rd_dynamics(
        self,
        since_date: date,
        until_date: date,
        project_ids: Optional[list[UUID]] = None,
        user_id: Optional[UUID] = None,
        run_id: Optional[UUID] = None,
    ) -> dict[str, Any]:
        stats = {
            "options_count": 0,
            "auto_bound_count": 0,
            "unmatched_count": 0,
            "imported_activity_count": 0,
            "skipped_duplicate_count": 0,
            "analysis_failed_count": 0,
            "failed_days": [],
        }
        raw_entry_ids: list[UUID] = []

        # 第一阶段：完整拉取并保存原始日志。此阶段不做项目匹配、不写活动。
        cursor = since_date
        while cursor <= until_date:
            payload = self._get_rd_dynamics_with_retry(cursor, stats["failed_days"])
            if payload is None:
                cursor += timedelta(days=1)
                continue

            for item in payload.get("projects", []) or []:
                item = dict(item)
                item["target_date"] = cursor.isoformat()
                stats["options_count"] += 1

                project_key = item.get("project_key") or f"rd_project_{item.get('id')}"
                if not project_key:
                    continue
                item["project_key"] = project_key
                raw_entry = self._store_raw_entry(item, cursor, run_id)
                raw_entry_ids.append(raw_entry.id)

            # 每天拉取完成即提交，后续 AI 故障不会回滚原始日志。
            self.db.commit()

            cursor += timedelta(days=1)

        # 第二阶段：对已落库的原始条目逐条分析、匹配并导入。
        for raw_entry_id in raw_entry_ids:
            raw_entry = (
                self.db.query(DailyReportRawEntry)
                .filter(DailyReportRawEntry.id == raw_entry_id)
                .first()
            )
            if not raw_entry:
                continue
            if raw_entry.activity_log_id:
                stats["skipped_duplicate_count"] += 1
                continue
            try:
                self._analyze_and_import_raw_entry(raw_entry, project_ids, user_id, stats)
                self.db.commit()
            except Exception as exc:
                self.db.rollback()
                raw_entry = (
                    self.db.query(DailyReportRawEntry)
                    .filter(DailyReportRawEntry.id == raw_entry_id)
                    .first()
                )
                if raw_entry:
                    raw_entry.analysis_status = "分析失败"
                    raw_entry.error_message = str(exc)[:1000]
                    raw_entry.analyzed_at = datetime.now()
                    self.db.commit()
                stats["analysis_failed_count"] += 1

        return stats

    def _store_raw_entry(
        self,
        item: dict[str, Any],
        source_date: date,
        run_id: Optional[UUID],
    ) -> DailyReportRawEntry:
        canonical = json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)
        source_hash = hashlib.sha256(
            f"rd-dynamics|{source_date.isoformat()}|{canonical}".encode("utf-8")
        ).hexdigest()
        existing = (
            self.db.query(DailyReportRawEntry)
            .filter(DailyReportRawEntry.source_hash == source_hash)
            .first()
        )
        if existing:
            return existing

        name = (
            item.get("project_name_normalized")
            or item.get("project_name")
            or item.get("entity_canonical_name")
            or item.get("project_key")
        )
        raw_entry = DailyReportRawEntry(
            sync_run_id=run_id,
            source_date=source_date,
            source_hash=source_hash,
            project_key=item.get("project_key"),
            external_project_name=str(name or "未知项目"),
            creator_name=(item.get("creator_name") or "").strip() or None,
            original_summary=(item.get("summary") or "").strip(),
            source_occurred_at=self._extract_log_datetime(item, source_date),
            raw_payload=item,
        )
        self.db.add(raw_entry)
        self.db.flush()
        return raw_entry

    def _analyze_and_import_raw_entry(
        self,
        raw_entry: DailyReportRawEntry,
        project_ids: Optional[list[UUID]],
        user_id: Optional[UUID],
        stats: dict[str, Any],
    ) -> None:
        projects = (
            self.db.query(Project)
            .outerjoin(Customer, Project.customer_id == Customer.id)
            .filter(Project.status != "ARCHIVED")
            .all()
        )
        binding = self._get_active_binding(raw_entry.project_key)
        alias_map = self._project_alias_map()
        alias_project = None if binding else self._match_confirmed_alias(raw_entry.raw_payload, projects, alias_map)
        analysis = self.ai_analyzer.analyze(
            item=raw_entry.raw_payload,
            projects=projects,
            source_date=raw_entry.source_date,
            bound_project=binding.project if binding else alias_project,
            project_aliases=alias_map,
        )
        raw_entry.ai_raw_response = analysis
        raw_entry.ai_confidence = self._safe_confidence(analysis.get("confidence"))
        raw_entry.ai_reason = str(analysis.get("reason") or "")[:2000] or None
        raw_entry.ai_summary = str(analysis.get("summary") or raw_entry.original_summary).strip()[:4000]
        raw_entry.ai_activity_type = str(analysis.get("activity_type") or "进展更新")
        raw_entry.ai_occurred_at = self._parse_ai_datetime(
            analysis.get("activity_time"),
            raw_entry.source_occurred_at,
            raw_entry.source_date,
        )
        raw_entry.analyzed_at = datetime.now()
        raw_entry.error_message = None

        if not binding:
            selected_project = alias_project or self._validated_ai_project(projects, analysis.get("project_id"))
            if alias_project:
                raw_entry.ai_confidence = 1.0
                alias_reason = f"命中已确认项目别名：{raw_entry.external_project_name}"
                raw_entry.ai_reason = f"{alias_reason}；{raw_entry.ai_reason}" if raw_entry.ai_reason else alias_reason
            match = MatchResult(
                project=selected_project,
                score=1.0 if alias_project else (raw_entry.ai_confidence or 0),
                method="alias" if alias_project else "ai",
            )
            raw_entry.ai_project_id = selected_project.id if selected_project else None
            if self._can_auto_bind(match):
                binding = self._create_or_update_binding(
                    item=raw_entry.raw_payload,
                    project=selected_project,
                    match_method=match.method,
                    match_score=match.score,
                    user_id=user_id,
                )
                self._mark_unmatched_bound(
                    month=raw_entry.source_date.strftime("%Y-%m"),
                    project_key=raw_entry.project_key,
                    project=selected_project,
                    score=match.score,
                    user_id=user_id,
                )
                stats["auto_bound_count"] += 1
            else:
                unmatched_payload = dict(raw_entry.raw_payload)
                unmatched_payload["ai_reason"] = raw_entry.ai_reason
                unmatched_payload["ai_confidence"] = raw_entry.ai_confidence
                self._upsert_unmatched(
                    unmatched_payload,
                    raw_entry.source_date.strftime("%Y-%m"),
                    MatchResult(
                        project=selected_project,
                        score=raw_entry.ai_confidence or 0,
                        method="ai_unconfirmed",
                    ),
                    user_id,
                )
                raw_entry.analysis_status = "待人工匹配"
                stats["unmatched_count"] += 1
                return
        else:
            self._mark_unmatched_bound(
                month=raw_entry.source_date.strftime("%Y-%m"),
                project_key=raw_entry.project_key,
                project=binding.project,
                score=float(binding.match_score or 1),
                user_id=user_id,
            )

        if project_ids and binding.project_id not in project_ids:
            raw_entry.analysis_status = "已分析未导入"
            return

        project = self.db.query(Project).filter(Project.id == binding.project_id).first()
        if not project:
            raise RuntimeError("AI 匹配的本地项目不存在")
        raw_entry.ai_project_id = project.id
        imported, skipped = self._import_analyzed_raw_entry(project, binding, raw_entry)
        stats["imported_activity_count"] += imported
        stats["skipped_duplicate_count"] += skipped
        binding.last_sync_month = raw_entry.source_date.strftime("%Y-%m")
        binding.last_sync_at = datetime.now()

    def _import_analyzed_raw_entry(
        self,
        project: Project,
        binding: DailyReportBinding,
        raw_entry: DailyReportRawEntry,
    ) -> tuple[int, int]:
        fact = (raw_entry.ai_summary or raw_entry.original_summary or "").strip()
        if not fact:
            raw_entry.analysis_status = "无有效内容"
            return 0, 0
        occurred_at = raw_entry.ai_occurred_at or raw_entry.source_occurred_at or datetime.combine(
            raw_entry.source_date, time(hour=12)
        )
        employee = raw_entry.creator_name or ""
        analysis = raw_entry.ai_raw_response or {}
        next_action = self._validated_next_action(analysis.get("next_action"))
        next_action_deadline = self._safe_date(analysis.get("next_action_deadline"))
        blocker_flag = self._safe_bool(analysis.get("blocker_flag")) or self._infer_blocker(fact)
        risk_reason = str(analysis.get("risk_reason") or "").strip()
        waiting_party = str(analysis.get("waiting_party") or "").strip()
        content = f"【AI分析/日报】{employee + '：' if employee else ''}{fact}"
        if waiting_party and next_action:
            content += f"\n【等待对象】{waiting_party}"
        if blocker_flag and risk_reason:
            content += f"\n【风险依据】{risk_reason[:500]}"
        legacy_hash = self._fact_hash(
            project.id,
            binding.project_key,
            raw_entry.source_date,
            "rd_project",
            employee,
            raw_entry.original_summary,
        )
        legacy_mapping = (
            self.db.query(DailyReportActivityMapping)
            .filter(DailyReportActivityMapping.fact_hash == legacy_hash)
            .first()
        )
        if legacy_mapping and legacy_mapping.activity:
            legacy_activity = legacy_mapping.activity
            legacy_activity.activity_type = self._validated_activity_type(raw_entry.ai_activity_type, fact)
            legacy_activity.activity_content = content[:2000]
            legacy_activity.next_action = next_action
            legacy_activity.next_action_deadline = next_action_deadline
            legacy_activity.blocker_flag = blocker_flag
            legacy_activity.occurred_at = occurred_at
            legacy_mapping.report_date = occurred_at.date()
            legacy_mapping.stage = "rd_ai_migrated"
            raw_entry.activity_log_id = legacy_activity.id
            raw_entry.analysis_status = "已更新历史活动"
            self.db.flush()
            project.last_activity_at = (
                self.db.query(func.max(ActivityLog.occurred_at))
                .filter(ActivityLog.project_id == project.id)
                .scalar()
            )
            project.updated_at = datetime.now()
            return 0, 1

        fact_hash = self._fact_hash(
            project.id,
            binding.project_key,
            occurred_at.date(),
            "rd_ai",
            employee,
            fact,
        )
        exists = (
            self.db.query(DailyReportActivityMapping)
            .filter(DailyReportActivityMapping.fact_hash == fact_hash)
            .first()
        )
        if exists:
            raw_entry.activity_log_id = exists.activity_log_id
            raw_entry.analysis_status = "重复已跳过"
            return 0, 1

        activity_type = self._validated_activity_type(raw_entry.ai_activity_type, fact)
        activity = ActivityLog(
            project_id=project.id,
            activity_type=activity_type,
            activity_content=content[:2000],
            next_action=next_action,
            next_action_deadline=next_action_deadline,
            blocker_flag=blocker_flag,
            owner_id=project.owner_id,
            source=ActivitySource.DAILY_REPORT,
            occurred_at=occurred_at,
        )
        self.db.add(activity)
        self.db.flush()
        self.db.add(
            DailyReportActivityMapping(
                project_id=project.id,
                activity_log_id=activity.id,
                project_key=binding.project_key,
                report_date=occurred_at.date(),
                stage="rd_ai",
                employee=employee or None,
                fact_hash=fact_hash,
                raw_payload=raw_entry.raw_payload,
            )
        )
        raw_entry.activity_log_id = activity.id
        raw_entry.analysis_status = "已导入"
        if not project.last_activity_at or occurred_at > project.last_activity_at:
            project.last_activity_at = occurred_at
            project.updated_at = datetime.now()
        # 新日报活动作为流程证据；没有行动项或阻塞时不会生成事项。
        from app.services.workflow_center import ingest_activity_evidence

        ingest_activity_evidence(
            self.db,
            activity,
            source_object_id=raw_entry.id,
            confidence=float(raw_entry.ai_confidence or 1),
            reason=raw_entry.ai_reason,
        )
        return 1, 0

    def _mark_unmatched_bound(
        self,
        month: str,
        project_key: str,
        project: Optional[Project],
        score: float,
        user_id: Optional[UUID],
    ) -> None:
        if not project:
            return
        record = (
            self.db.query(DailyReportUnmatchedProject)
            .filter(
                DailyReportUnmatchedProject.month == month,
                DailyReportUnmatchedProject.project_key == project_key,
            )
            .first()
        )
        if not record or record.status == "已绑定":
            return
        record.status = "已绑定"
        record.suggested_project_id = project.id
        record.suggested_project_name = project.project_name
        record.suggested_score = score
        record.handled_by = user_id
        record.handled_at = datetime.now()
        record.updated_at = datetime.now()

    def _get_rd_dynamics_with_retry(
        self,
        target_date: date,
        failed_days: list[str],
        attempts: int = 3,
    ) -> Optional[dict[str, Any]]:
        last_error = ""
        for attempt in range(1, attempts + 1):
            try:
                return self.client.get_rd_dynamics(target_date)
            except RuntimeError as exc:
                last_error = str(exc)
                if not self._is_transient_daily_report_error(last_error) or attempt == attempts:
                    break
                time_module.sleep(min(attempt, 2))
        failed_days.append(f"{target_date.isoformat()}: {last_error[:120]}")
        return None

    def _is_transient_daily_report_error(self, message: str) -> bool:
        return any(
            marker in message
            for marker in (
                "HTTP 500",
                "HTTP 502",
                "HTTP 503",
                "HTTP 504",
                "timed out",
                "连接失败",
            )
        )

    def _import_rd_project_item(
        self,
        project: Project,
        binding: DailyReportBinding,
        item: dict[str, Any],
        report_date: date,
    ) -> tuple[int, int]:
        fact = (item.get("summary") or "").strip()
        employee = (item.get("creator_name") or "").strip()
        if not fact:
            return 0, 0

        fact_hash = self._fact_hash(project.id, binding.project_key, report_date, "rd_project", employee, fact)
        exists = (
            self.db.query(DailyReportActivityMapping)
            .filter(DailyReportActivityMapping.fact_hash == fact_hash)
            .first()
        )
        if exists:
            return 0, 1

        activity = ActivityLog(
            project_id=project.id,
            activity_type=self._infer_activity_type(fact),
            activity_content=f"【RD日报】{employee + '：' if employee else ''}{fact}",
            blocker_flag=self._infer_blocker(fact),
            owner_id=project.owner_id,
            source=ActivitySource.DAILY_REPORT,
            occurred_at=datetime.combine(report_date, time(hour=12)),
        )
        self.db.add(activity)
        self.db.flush()

        mapping = DailyReportActivityMapping(
            project_id=project.id,
            activity_log_id=activity.id,
            project_key=binding.project_key,
            report_date=report_date,
            stage="rd_project",
            employee=employee or None,
            fact_hash=fact_hash,
            raw_payload=item,
        )
        self.db.add(mapping)

        if not project.last_activity_at or activity.occurred_at > project.last_activity_at:
            project.last_activity_at = activity.occurred_at
            project.updated_at = datetime.now()

        return 1, 0

    def _import_bound_timelines(
        self,
        months: list[str] | str,
        since_date: date,
        until_date: Optional[date] = None,
        project_ids: Optional[list[UUID]] = None,
    ) -> tuple[int, int]:
        imported = 0
        skipped = 0
        month_list = [months] if isinstance(months, str) else months
        until = until_date or date.today()
        query = self.db.query(DailyReportBinding).filter(DailyReportBinding.is_active.is_(True))
        if project_ids:
            query = query.filter(DailyReportBinding.project_id.in_(project_ids))
        bindings = query.all()

        for binding in bindings:
            project = self.db.query(Project).filter(Project.id == binding.project_id).first()
            if not project:
                continue

            for month in month_list:
                timeline = self.client.get_project_timeline(month, binding.project_key)
                for day_item in timeline.get("items", []):
                    report_date = self._parse_date(day_item.get("date"))
                    if not report_date or report_date < since_date or report_date > until:
                        continue
                    for stage in ("pre_sales", "implementation", "service", "unassigned"):
                        for entry in day_item.get(stage, []) or []:
                            fact = (entry.get("fact") or "").strip()
                            employee = (entry.get("employee") or "").strip()
                            if not fact:
                                continue
                            fact_hash = self._fact_hash(project.id, binding.project_key, report_date, stage, employee, fact)
                            exists = (
                                self.db.query(DailyReportActivityMapping)
                                .filter(DailyReportActivityMapping.fact_hash == fact_hash)
                                .first()
                            )
                            if exists:
                                skipped += 1
                                continue

                            activity = ActivityLog(
                                project_id=project.id,
                                activity_type=self._infer_activity_type(fact),
                                activity_content=f"【日报/{STAGE_LABELS.get(stage, stage)}】{employee + '：' if employee else ''}{fact}",
                                blocker_flag=self._infer_blocker(fact),
                                owner_id=project.owner_id,
                                source=ActivitySource.DAILY_REPORT,
                                occurred_at=datetime.combine(report_date, time(hour=12)),
                            )
                            self.db.add(activity)
                            self.db.flush()

                            mapping = DailyReportActivityMapping(
                                project_id=project.id,
                                activity_log_id=activity.id,
                                project_key=binding.project_key,
                                report_date=report_date,
                                stage=stage,
                                employee=employee or None,
                                fact_hash=fact_hash,
                                raw_payload=entry,
                            )
                            self.db.add(mapping)
                            imported += 1

                            if not project.last_activity_at or activity.occurred_at > project.last_activity_at:
                                project.last_activity_at = activity.occurred_at
                                project.updated_at = datetime.now()

                binding.last_sync_month = month
                binding.last_sync_at = datetime.now()

        self.db.flush()
        return imported, skipped

    def _resolve_date_window(
        self,
        month: str,
        lookback_days: int,
        start_date: Optional[date],
        end_date: Optional[date],
    ) -> tuple[date, date]:
        if start_date and end_date and start_date > end_date:
            raise ValueError("开始日期不能晚于结束日期")
        if start_date or end_date:
            start = start_date or end_date
            end = end_date or start_date
            return start, end

        today = date.today()
        month_start = datetime.strptime(f"{month}-01", "%Y-%m-%d").date()
        if month_start.year != today.year or month_start.month != today.month:
            if month_start.month == 12:
                next_month = date(month_start.year + 1, 1, 1)
            else:
                next_month = date(month_start.year, month_start.month + 1, 1)
            return month_start, next_month - timedelta(days=1)

        since = today - timedelta(days=max(lookback_days - 1, 0))
        if since.strftime("%Y-%m") != month:
            since = month_start
        return since, today

    def _extract_log_datetime(self, item: dict[str, Any], source_date: date) -> datetime:
        """从原始日志提取实际时间；无时间字段时才回退到查询日期中午。"""
        for field in (
            "occurred_at",
            "activity_time",
            "log_time",
            "report_time",
            "created_at",
            "create_time",
            "updated_at",
            "timestamp",
            "report_date",
            "date",
        ):
            parsed = self._parse_datetime_value(item.get(field))
            if parsed:
                return parsed
        return datetime.combine(source_date, time(hour=12))

    def _parse_datetime_value(self, value: Any) -> Optional[datetime]:
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, time(hour=12))
        if isinstance(value, (int, float)):
            timestamp = float(value)
            if timestamp > 10_000_000_000:
                timestamp /= 1000
            try:
                return datetime.fromtimestamp(timestamp)
            except (ValueError, OSError, OverflowError):
                return None
        text = str(value).strip()
        if not text:
            return None
        normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
        try:
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo:
                parsed = parsed.astimezone(ZoneInfo("Asia/Shanghai")).replace(tzinfo=None)
            if parsed.hour == 0 and parsed.minute == 0 and len(text) <= 10:
                return datetime.combine(parsed.date(), time(hour=12))
            return parsed
        except ValueError:
            pass
        for pattern in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(text, pattern)
                return datetime.combine(parsed.date(), time(hour=12)) if pattern == "%Y-%m-%d" else parsed
            except ValueError:
                continue
        return None

    def _parse_ai_datetime(
        self,
        value: Any,
        source_occurred_at: Optional[datetime],
        source_date: date,
    ) -> datetime:
        return (
            self._parse_datetime_value(value)
            or source_occurred_at
            or datetime.combine(source_date, time(hour=12))
        )

    def _safe_confidence(self, value: Any) -> float:
        try:
            return min(1.0, max(0.0, float(value)))
        except (TypeError, ValueError):
            return 0.0

    def _validated_ai_project(self, projects: list[Project], project_id: Any) -> Optional[Project]:
        if not project_id:
            return None
        try:
            selected_id = UUID(str(project_id))
        except (TypeError, ValueError):
            return None
        return next((project for project in projects if project.id == selected_id), None)

    def _validated_activity_type(self, value: Optional[str], fact: str) -> ActivityType:
        try:
            return ActivityType(value)
        except (ValueError, TypeError):
            return self._infer_activity_type(fact)

    def _validated_next_action(self, value: Any) -> Optional[NextAction]:
        if value in (None, "", "null"):
            return None
        try:
            return NextAction(str(value).strip())
        except (ValueError, TypeError):
            return NextAction.OTHER

    def _safe_date(self, value: Any) -> Optional[date]:
        if not value:
            return None
        try:
            if isinstance(value, datetime):
                return value.date()
            if isinstance(value, date):
                return value
            return datetime.fromisoformat(str(value).strip()[:10]).date()
        except (TypeError, ValueError):
            return None

    def _safe_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return str(value or "").strip().lower() in {"1", "true", "yes", "是"}

    def _can_auto_bind(self, match: MatchResult) -> bool:
        if not match.project:
            return False
        if match.method == "ai":
            return match.score >= settings.DAILY_REPORT_AI_AUTO_MATCH_SCORE
        if match.method == "alias":
            return match.score >= 1
        if match.method not in ("exact", "contains"):
            return False
        return match.score >= settings.DAILY_REPORT_SYNC_AUTO_MATCH_SCORE

    def _can_suggest(self, match: MatchResult) -> bool:
        return bool(match.project and match.score >= 0.8)

    def _item_text(self, item: dict[str, Any]) -> str:
        text = "".join(
            str(item.get(field) or "")
            for field in (
                "project_name",
                "project_name_normalized",
                "entity_canonical_name",
                "customer_entity_id",
                "project_entity_id",
            )
        )
        return text

    def _months_between(self, start_date: date, end_date: date) -> list[str]:
        months = []
        cursor = date(start_date.year, start_date.month, 1)
        end_cursor = date(end_date.year, end_date.month, 1)
        while cursor <= end_cursor:
            months.append(cursor.strftime("%Y-%m"))
            if cursor.month == 12:
                cursor = date(cursor.year + 1, 1, 1)
            else:
                cursor = date(cursor.year, cursor.month + 1, 1)
        return months

    def bind_unmatched(
        self,
        unmatched_id: UUID,
        project_id: UUID,
        user_id: Optional[UUID],
        sync_after_bind: bool = True,
    ) -> DailyReportUnmatchedProject:
        record = self.db.query(DailyReportUnmatchedProject).filter(DailyReportUnmatchedProject.id == unmatched_id).first()
        if not record:
            raise ValueError("未匹配日报项目不存在")
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError("项目不存在")

        binding = self._create_or_update_binding(
            item=record.raw_payload or {
                "project_key": record.project_key,
                "project_name_normalized": record.external_project_name,
            },
            project=project,
            match_method="manual",
            match_score=1,
            user_id=user_id,
        )
        record.status = "已绑定"
        record.suggested_project_id = project.id
        record.suggested_project_name = project.project_name
        record.suggested_score = 1
        record.handled_by = user_id
        record.handled_at = datetime.now()
        imported = 0
        skipped = 0
        if sync_after_bind:
            imported, skipped = self._import_existing_raw_entries_for_binding(record, project, binding)
        record.imported_activity_count = imported
        record.skipped_duplicate_count = skipped
        self.db.commit()
        return record

    def _import_existing_raw_entries_for_binding(
        self,
        record: DailyReportUnmatchedProject,
        project: Project,
        binding: DailyReportBinding,
    ) -> tuple[int, int]:
        """人工绑定后直接导入已落库原始日志，不再重拉整月或重复调用 AI。"""
        month_start = datetime.strptime(f"{record.month}-01", "%Y-%m-%d").date()
        if month_start.month == 12:
            next_month = date(month_start.year + 1, 1, 1)
        else:
            next_month = date(month_start.year, month_start.month + 1, 1)
        raw_entries = (
            self.db.query(DailyReportRawEntry)
            .filter(
                DailyReportRawEntry.project_key == record.project_key,
                DailyReportRawEntry.source_date >= month_start,
                DailyReportRawEntry.source_date < next_month,
                DailyReportRawEntry.activity_log_id.is_(None),
            )
            .order_by(DailyReportRawEntry.source_date.asc(), DailyReportRawEntry.created_at.asc())
            .all()
        )
        imported = 0
        skipped = 0
        for raw_entry in raw_entries:
            self._remember_project_alias(
                project=project,
                alias_name=raw_entry.external_project_name,
                project_key=raw_entry.project_key,
                method="manual",
                confidence=1,
            )
            raw_entry.ai_project_id = project.id
            raw_entry.ai_summary = raw_entry.ai_summary or raw_entry.original_summary
            raw_entry.ai_occurred_at = (
                raw_entry.ai_occurred_at
                or raw_entry.source_occurred_at
                or datetime.combine(raw_entry.source_date, time(hour=12))
            )
            entry_imported, entry_skipped = self._import_analyzed_raw_entry(project, binding, raw_entry)
            imported += entry_imported
            skipped += entry_skipped

        binding.last_sync_month = record.month
        binding.last_sync_at = datetime.now()
        return imported, skipped

    def ignore_unmatched(self, unmatched_id: UUID, user_id: Optional[UUID]) -> DailyReportUnmatchedProject:
        record = self.db.query(DailyReportUnmatchedProject).filter(DailyReportUnmatchedProject.id == unmatched_id).first()
        if not record:
            raise ValueError("未匹配日报项目不存在")
        record.status = "已忽略"
        record.handled_by = user_id
        record.handled_at = datetime.now()
        self.db.commit()
        return record

    def _infer_activity_type(self, fact: str) -> ActivityType:
        if self._infer_blocker(fact):
            return ActivityType.BLOCKER_WAITING
        if any(word in fact for word in ("风险", "延期", "异常", "问题")):
            return ActivityType.RISK_REPORT
        if any(word in fact for word in ("完成", "验收", "上线", "交付")):
            return ActivityType.MILESTONE_COMPLETE
        return ActivityType.PROGRESS_UPDATE

    def _infer_blocker(self, fact: str) -> bool:
        return any(word in fact for word in ("阻塞", "卡住", "等待", "延期", "无法", "风险"))

    def _fact_hash(
        self,
        project_id: UUID,
        project_key: str,
        report_date: date,
        stage: str,
        employee: str,
        fact: str,
    ) -> str:
        raw = f"{project_id}|{project_key}|{report_date.isoformat()}|{stage}|{employee}|{fact}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _parse_date(self, value: Any) -> Optional[date]:
        if not value:
            return None
        if isinstance(value, date):
            return value
        return datetime.strptime(str(value), "%Y-%m-%d").date()
