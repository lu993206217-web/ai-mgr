"""海外管理绩效汇报自动汇总服务。"""

from __future__ import annotations

import calendar
import re
from collections import defaultdict
from copy import deepcopy
from datetime import date, datetime, time, timedelta
from typing import Any, Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog
from app.models.email_intelligence import EmailAttachment, EmailMessage
from app.models.enums import ActivitySource, ActivityType, ProjectStatus
from app.models.overseas_performance import OverseasPerformanceConfig, OverseasPerformanceReport
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.user import User
from app.services.activity_presentation import _email_flow, _internal_domains


DEFAULT_CRITERIA: list[dict[str, Any]] = [
    {
        "code": "c1",
        "title": "项目交付与质量达标",
        "required": True,
        "requirement": "季度内海外项目交付任务按时完成，交付文档完整、准确、易用。",
        "evidence_requirements": ["项目交付清单", "计划/实际完成日期", "延期说明", "交付文档及审核结果"],
        "enabled": True,
        "thresholds": {"on_time_rate": 100},
    },
    {
        "code": "c2",
        "title": "技术问题响应与解决",
        "required": True,
        "requirement": "跨时区技术问题响应不超过2小时，紧急问题响应不超过30分钟。",
        "evidence_requirements": ["响应时间统计表", "跨时区与紧急案例", "客户反馈或工单记录"],
        "enabled": True,
        "thresholds": {"normal_response_minutes": 120, "emergency_response_minutes": 30},
    },
    {
        "code": "c3",
        "title": "团队任务分配与协调",
        "required": True,
        "requirement": "每月合理分配团队任务，职责清晰、衔接顺畅，无分配不当导致的延误。",
        "evidence_requirements": ["月度任务分配表", "成员进度反馈", "团队会议纪要或沟通记录"],
        "enabled": True,
        "thresholds": {"assignment_frequency_months": 1},
    },
    {
        "code": "c4",
        "title": "客户满意度达标",
        "required": True,
        "requirement": "季度客户满意度不低于90分，无服务态度或交付质量投诉。",
        "evidence_requirements": ["满意度评分表", "反馈邮件", "投诉及处理记录"],
        "enabled": True,
        "thresholds": {"satisfaction_score": 90},
    },
    {
        "code": "c5",
        "title": "项目复盘与改进追踪",
        "required": False,
        "requirement": "每个结束项目提交交付总结并建立改进追踪表，确保问题闭环。",
        "evidence_requirements": ["交付总结报告", "改进追踪表", "问题关闭状态"],
        "enabled": True,
        "thresholds": {"retrospective_rate": 100},
    },
    {
        "code": "c6",
        "title": "组织季度培训与复盘",
        "required": False,
        "requirement": "每季度至少组织一次海外业务沟通或海外注意事项培训。",
        "evidence_requirements": ["培训计划", "签到表", "培训材料", "参训人员反馈"],
        "enabled": True,
        "thresholds": {"quarterly_training_count": 1},
    },
    {
        "code": "c7",
        "title": "宣传资料输出",
        "required": False,
        "requirement": "每季度输出至少3份海外宣传文档或视频，内容和质量达标。",
        "evidence_requirements": ["宣传资料清单", "成品链接或文件", "客户或销售反馈"],
        "enabled": True,
        "thresholds": {"quarterly_material_count": 3},
    },
]


def _value(value: Any) -> str:
    return str(getattr(value, "value", value) or "")


def _merge_criteria(stored: Optional[list]) -> list[dict[str, Any]]:
    by_code = {
        item.get("code"): item
        for item in (stored or [])
        if isinstance(item, dict) and item.get("code")
    }
    merged = []
    for default in DEFAULT_CRITERIA:
        item = deepcopy(default)
        configured = by_code.get(default["code"], {})
        item["enabled"] = bool(configured.get("enabled", item["enabled"]))
        if isinstance(configured.get("thresholds"), dict):
            item["thresholds"].update(configured["thresholds"])
        merged.append(item)
    return merged


def get_or_create_config(db: Session, user_id: UUID) -> OverseasPerformanceConfig:
    config = db.query(OverseasPerformanceConfig).filter(OverseasPerformanceConfig.user_id == user_id).first()
    if config:
        config.criteria_json = _merge_criteria(config.criteria_json)
        return config
    config = OverseasPerformanceConfig(user_id=user_id, criteria_json=deepcopy(DEFAULT_CRITERIA))
    db.add(config)
    db.flush()
    return config


def config_view(config: OverseasPerformanceConfig) -> dict[str, Any]:
    return {
        "enabled": config.enabled,
        "scope": config.scope,
        "schedule_frequency": config.schedule_frequency,
        "schedule_day": config.schedule_day,
        "schedule_hour": config.schedule_hour,
        "schedule_minute": config.schedule_minute,
        "criteria": _merge_criteria(config.criteria_json),
        "last_run_at": config.last_run_at,
    }


def save_config(db: Session, user_id: UUID, payload: dict[str, Any]) -> OverseasPerformanceConfig:
    config = get_or_create_config(db, user_id)
    config.enabled = bool(payload["enabled"])
    config.scope = payload["scope"]
    config.schedule_frequency = payload["schedule_frequency"]
    config.schedule_day = int(payload["schedule_day"])
    config.schedule_hour = int(payload["schedule_hour"])
    config.schedule_minute = int(payload["schedule_minute"])
    config.criteria_json = _merge_criteria(payload["criteria"])
    db.flush()
    return config


def _bounds(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    return datetime.combine(start_date, time.min), datetime.combine(end_date + timedelta(days=1), time.min)


def _in_period(column, start_dt: datetime, end_exclusive: datetime):
    return and_(column >= start_dt, column < end_exclusive)


def _project_scope(query, scope: str, user_id: UUID):
    return query.filter(Project.owner_id == user_id) if scope == "owned_projects" else query


def _relevant_projects(
    db: Session, start_date: date, end_date: date, scope: str, user_id: UUID
) -> list[Project]:
    start_dt, end_dt = _bounds(start_date, end_date)
    activity_ids = {
        row[0]
        for row in db.query(ActivityLog.project_id)
        .filter(ActivityLog.project_id.isnot(None), _in_period(ActivityLog.occurred_at, start_dt, end_dt))
        .all()
    }
    file_ids = {
        row[0]
        for row in db.query(ProjectFile.project_id)
        .filter(_in_period(ProjectFile.created_at, start_dt, end_dt))
        .all()
    }
    query = db.query(Project).filter(
        or_(
            Project.id.in_(activity_ids | file_ids) if activity_ids or file_ids else False,
            _in_period(Project.created_at, start_dt, end_dt),
            and_(Project.planned_go_live >= start_date, Project.planned_go_live <= end_date),
            and_(Project.planned_acceptance >= start_date, Project.planned_acceptance <= end_date),
        )
    )
    return _project_scope(query, scope, user_id).order_by(Project.project_name).all()


def _criterion1(
    db: Session,
    projects: list[Project],
    start_date: date,
    end_date: date,
    threshold: dict[str, Any],
) -> dict[str, Any]:
    start_dt, end_dt = _bounds(start_date, end_date)
    records = []
    evaluable = 0
    on_time = 0
    overdue = 0
    doc_total = 0
    for project in projects:
        milestones = (
            db.query(ActivityLog)
            .filter(
                ActivityLog.project_id == project.id,
                ActivityLog.activity_type == ActivityType.MILESTONE_COMPLETE,
                _in_period(ActivityLog.occurred_at, start_dt, end_dt),
            )
            .order_by(ActivityLog.occurred_at.desc())
            .all()
        )
        documents = (
            db.query(ProjectFile)
            .filter(ProjectFile.project_id == project.id, _in_period(ProjectFile.created_at, start_dt, end_dt))
            .order_by(ProjectFile.created_at.desc())
            .all()
        )
        actual = milestones[0].occurred_at.date() if milestones else None
        planned = project.planned_acceptance or project.planned_go_live
        if planned and actual:
            evaluable += 1
            if actual <= planned:
                on_time += 1
            else:
                overdue += 1
        elif planned and planned <= end_date and not actual and project.status != ProjectStatus.ACCEPTED:
            overdue += 1
        doc_total += len(documents)
        records.append(
            {
                "project_id": str(project.id),
                "project_name": project.project_name,
                "country": project.country,
                "owner": project.owner.full_name or project.owner.username if project.owner else "未设置",
                "stage": _value(project.current_stage),
                "status": _value(project.status),
                "planned_date": planned.isoformat() if planned else None,
                "actual_date": actual.isoformat() if actual else None,
                "on_time": actual <= planned if actual and planned else None,
                "document_count": len(documents),
                "documents": [item.file_name for item in documents[:5]],
            }
        )
    rate = round(on_time / evaluable * 100, 1) if evaluable else None
    if overdue:
        status = "未达标"
        conclusion = f"发现 {overdue} 个可识别的逾期或到期未闭环项目。"
    elif projects and evaluable == len(projects) and doc_total >= len(projects):
        status = "达标" if rate is not None and rate >= float(threshold.get("on_time_rate", 100)) else "未达标"
        conclusion = "现有日期与交付文件证据可支持按时交付判断。"
    elif projects:
        status = "证据不足"
        conclusion = "已汇总项目推进事实，但计划/实际完成日期或交付文档记录不完整。"
    else:
        status = "无数据"
        conclusion = "所选时间段内未识别到相关项目。"
    return {
        "status": status,
        "conclusion": conclusion,
        "metrics": [
            {"label": "涉及项目", "value": len(projects), "unit": "个"},
            {"label": "可计算按时率", "value": rate if rate is not None else "--", "unit": "%" if rate is not None else ""},
            {"label": "交付文档记录", "value": doc_total, "unit": "份"},
            {"label": "逾期/未闭环", "value": overdue, "unit": "个"},
        ],
        "evidence": [f"项目主数据 {len(projects)} 个", f"本期项目文件 {doc_total} 份", f"里程碑完成记录 {sum(1 for r in records if r['actual_date'])} 条"],
        "gaps": [
            item for item in [
                "补齐每个项目的计划完成日期" if any(not r["planned_date"] for r in records) else None,
                "补齐实际完成日期或里程碑活动" if any(not r["actual_date"] for r in records) else None,
                "上传安装手册、测试报告等交付文件并记录审核结果" if doc_total < len(projects) else None,
                "系统暂无质量事故专门登记，需补充事故/投诉为零的佐证",
            ] if item
        ],
        "records": records,
    }


def _criterion2(
    db: Session, start_date: date, end_date: date, project_ids: set[UUID], threshold: dict[str, Any]
) -> dict[str, Any]:
    start_dt, end_dt = _bounds(start_date, end_date)
    query = db.query(EmailMessage).filter(_in_period(EmailMessage.received_at, start_dt, end_dt))
    if project_ids:
        query = query.filter(EmailMessage.project_id.in_(project_ids))
    messages = query.order_by(EmailMessage.received_at).all()
    domains = _internal_domains()
    inbound = [item for item in messages if _email_flow(item, domains) == "inbound"]
    all_threads: dict[str, list[EmailMessage]] = defaultdict(list)
    thread_ids = {item.thread_id for item in inbound if item.thread_id}
    if thread_ids:
        for item in db.query(EmailMessage).filter(EmailMessage.thread_id.in_(thread_ids)).order_by(EmailMessage.received_at).all():
            if item.thread_id:
                all_threads[item.thread_id].append(item)
    urgent_pattern = re.compile(r"紧急|urgent|emergency|critical|\bp[01]\b", re.I)
    records = []
    violations = 0
    responded = 0
    response_minutes: list[int] = []
    for item in inbound:
        candidates = [
            other for other in all_threads.get(item.thread_id or "", [])
            if other.received_at > item.received_at and _email_flow(other, domains) == "outbound"
        ]
        reply = candidates[0] if candidates else None
        minutes = round((reply.received_at - item.received_at).total_seconds() / 60) if reply else None
        emergency = bool(urgent_pattern.search(f"{item.subject}\n{item.summary or ''}\n{item.raw_body_text[:1000]}"))
        limit = int(threshold.get("emergency_response_minutes" if emergency else "normal_response_minutes", 30 if emergency else 120))
        met = minutes <= limit if minutes is not None else None
        if minutes is not None:
            responded += 1
            response_minutes.append(minutes)
            if not met:
                violations += 1
        records.append(
            {
                "email_id": str(item.id),
                "project_id": str(item.project_id) if item.project_id else None,
                "subject": item.subject,
                "received_at": item.received_at.isoformat(),
                "reply_at": reply.received_at.isoformat() if reply else None,
                "response_minutes": minutes,
                "emergency": emergency,
                "sla_minutes": limit,
                "met": met,
            }
        )
    if violations:
        status = "未达标"
        conclusion = f"在可计算邮件中发现 {violations} 次响应超过考核阈值。"
    elif inbound and responded == len(inbound):
        status = "达标"
        conclusion = "现有邮件线程中的客户来信均在对应响应时限内获得我方回复。"
    elif inbound:
        status = "证据不足"
        conclusion = "已识别客户来信，但部分线程缺少我方已发送邮件，无法完成响应时长判断。"
    else:
        status = "无数据"
        conclusion = "所选时间段内未识别到已绑定项目的客户来信。"
    average = round(sum(response_minutes) / len(response_minutes), 1) if response_minutes else None
    return {
        "status": status,
        "conclusion": conclusion,
        "metrics": [
            {"label": "客户来信", "value": len(inbound), "unit": "封"},
            {"label": "可计算响应", "value": responded, "unit": "封"},
            {"label": "平均响应", "value": average if average is not None else "--", "unit": "分钟" if average is not None else ""},
            {"label": "超时记录", "value": violations, "unit": "条"},
        ],
        "evidence": [f"已绑定项目客户来信 {len(inbound)} 封", f"形成响应时间对 {responded} 组"],
        "gaps": [
            item for item in [
                f"仍有 {len(inbound) - responded} 封客户来信未找到我方回复记录" if len(inbound) > responded else None,
                "跨时区属性目前按海外项目邮件识别，建议后续补客户时区字段",
                "紧急程度目前按主题和正文关键词识别，建议工单接入后采用正式优先级",
            ] if item
        ],
        "records": records[:100],
    }


def _criterion3(db: Session, start_date: date, end_date: date, project_ids: set[UUID]) -> dict[str, Any]:
    start_dt, end_dt = _bounds(start_date, end_date)
    query = db.query(ActivityLog).filter(_in_period(ActivityLog.occurred_at, start_dt, end_dt))
    if project_ids:
        query = query.filter(ActivityLog.project_id.in_(project_ids))
    activities = query.all()
    owners = {row.id: row for row in db.query(User).all()}
    grouped: dict[tuple[str, UUID], dict[str, Any]] = {}
    meeting_count = 0
    for item in activities:
        month = item.occurred_at.strftime("%Y-%m")
        key = (month, item.owner_id)
        entry = grouped.setdefault(key, {"month": month, "owner_id": str(item.owner_id), "activity_count": 0, "project_ids": set()})
        entry["activity_count"] += 1
        if item.project_id:
            entry["project_ids"].add(str(item.project_id))
        if _value(item.source) == _value(ActivitySource.MEETING):
            meeting_count += 1
    records = []
    for (_, owner_id), item in sorted(grouped.items()):
        owner = owners.get(owner_id)
        records.append({
            "month": item["month"],
            "owner": (owner.full_name or owner.username) if owner else "未知负责人",
            "activity_count": item["activity_count"],
            "project_count": len(item["project_ids"]),
        })
    return {
        "status": "证据不足" if activities else "无数据",
        "conclusion": "系统可按月份统计成员实际活动，但实际活动不能替代事前任务分配表和成员确认记录。",
        "metrics": [
            {"label": "成员活动", "value": len(activities), "unit": "条"},
            {"label": "成员/月组合", "value": len(records), "unit": "组"},
            {"label": "会议记录", "value": meeting_count, "unit": "条"},
        ],
        "evidence": [f"本期活动日志 {len(activities)} 条", f"会议来源活动 {meeting_count} 条"],
        "gaps": ["缺少正式月度任务分配表", "缺少成员进度确认字段", "会议纪要需作为项目文件上传并分类"],
        "records": records,
    }


def _criterion4(db: Session, start_date: date, end_date: date, project_ids: set[UUID], threshold: dict[str, Any]) -> dict[str, Any]:
    start_dt, end_dt = _bounds(start_date, end_date)
    query = db.query(EmailMessage).filter(_in_period(EmailMessage.received_at, start_dt, end_dt))
    if project_ids:
        query = query.filter(EmailMessage.project_id.in_(project_ids))
    positive_pattern = re.compile(r"满意|感谢|认可|thank(?:s| you)|appreciat|satisf", re.I)
    complaint_pattern = re.compile(r"投诉|complaint|dissatisf|unacceptable", re.I)
    feedback = []
    complaints = []
    for item in query.all():
        text = f"{item.subject}\n{item.summary or ''}\n{item.raw_body_text[:1500]}"
        record = {"email_id": str(item.id), "subject": item.subject, "received_at": item.received_at.isoformat()}
        if positive_pattern.search(text):
            feedback.append(record)
        if complaint_pattern.search(text):
            complaints.append(record)
    return {
        "status": "证据不足",
        "conclusion": f"系统找到 {len(feedback)} 封潜在正向反馈邮件，但没有结构化满意度评分，无法证明达到 {threshold.get('satisfaction_score', 90)} 分。",
        "metrics": [
            {"label": "目标分数", "value": threshold.get("satisfaction_score", 90), "unit": "分"},
            {"label": "已登记评分", "value": 0, "unit": "份"},
            {"label": "正向反馈候选", "value": len(feedback), "unit": "封"},
            {"label": "投诉关键词", "value": len(complaints), "unit": "封"},
        ],
        "evidence": [f"正向反馈关键词邮件 {len(feedback)} 封", f"投诉关键词邮件 {len(complaints)} 封"],
        "gaps": ["缺少客户满意度评分表及统计口径", "反馈邮件需人工确认是否可作为正式证据", "投诉关键词命中需人工核实并补处理闭环"],
        "records": {"positive_feedback": feedback[:30], "complaints": complaints[:30]},
    }


def _keyword_files(db: Session, start_date: date, end_date: date, pattern: re.Pattern, project_ids: set[UUID]) -> list[ProjectFile]:
    start_dt, end_dt = _bounds(start_date, end_date)
    query = db.query(ProjectFile).filter(_in_period(ProjectFile.created_at, start_dt, end_dt))
    if project_ids:
        query = query.filter(ProjectFile.project_id.in_(project_ids))
    return [item for item in query.all() if pattern.search(f"{item.file_name} {item.file_category} {item.description or ''}")]


def _criterion5(db: Session, projects: list[Project], start_date: date, end_date: date, project_ids: set[UUID], threshold: dict[str, Any]) -> dict[str, Any]:
    completed = [item for item in projects if item.status in {ProjectStatus.ACCEPTED, ProjectStatus.ARCHIVED, ProjectStatus.TERMINATED}]
    review_files = _keyword_files(db, start_date, end_date, re.compile(r"复盘|交付总结|总结报告|改进|关闭|close|retrospective", re.I), project_ids)
    covered = {item.project_id for item in review_files}
    rate = round(len({item.id for item in completed} & covered) / len(completed) * 100, 1) if completed else None
    if not completed:
        status = "无数据"
        conclusion = "本期相关项目中没有识别到已验收、归档或终止项目。"
    elif rate is not None and rate >= float(threshold.get("retrospective_rate", 100)):
        status = "达标"
        conclusion = "结束项目均存在复盘或交付总结文件索引。"
    else:
        status = "证据不足"
        conclusion = "存在结束项目，但交付总结、改进追踪和关闭状态记录不完整。"
    return {
        "status": status,
        "conclusion": conclusion,
        "metrics": [
            {"label": "结束项目", "value": len(completed), "unit": "个"},
            {"label": "复盘文件", "value": len(review_files), "unit": "份"},
            {"label": "复盘覆盖率", "value": rate if rate is not None else "--", "unit": "%" if rate is not None else ""},
        ],
        "evidence": [f"结束状态项目 {len(completed)} 个", f"复盘/总结/改进文件 {len(review_files)} 份"],
        "gaps": ["为每个结束项目上传交付总结报告", "建立改进项责任人、截止时间、关闭状态字段"],
        "records": [
            {"project_id": str(item.id), "project_name": item.project_name, "status": _value(item.status), "has_review_file": item.id in covered}
            for item in completed
        ],
    }


def _criterion6(db: Session, start_date: date, end_date: date, project_ids: set[UUID], threshold: dict[str, Any]) -> dict[str, Any]:
    pattern = re.compile(r"培训|training|英语表达|文化差异|海外注意", re.I)
    files = _keyword_files(db, start_date, end_date, pattern, project_ids)
    start_dt, end_dt = _bounds(start_date, end_date)
    activities = db.query(ActivityLog).filter(_in_period(ActivityLog.occurred_at, start_dt, end_dt)).all()
    candidate_activities = [item for item in activities if pattern.search(item.activity_content or "")]
    target = int(threshold.get("quarterly_training_count", 1))
    completed_count = len({item.project_id for item in files}) if files else 0
    # 项目内的客户培训不能直接替代“面向团队组织季度培训”的正式证据。
    status = "证据不足" if files or candidate_activities else "无数据"
    return {
        "status": status,
        "conclusion": "已找到培训相关材料候选，但仍需计划、签到、课件和反馈共同构成完整证据链。" if files or candidate_activities else "未找到培训活动或培训材料记录。",
        "metrics": [
            {"label": "季度目标", "value": target, "unit": "次"},
            {"label": "培训材料候选", "value": len(files), "unit": "份"},
            {"label": "培训活动候选", "value": len(candidate_activities), "unit": "条"},
        ],
        "evidence": [f"培训关键词文件 {len(files)} 份", f"培训关键词活动 {len(candidate_activities)} 条"],
        "gaps": ["补齐培训计划、签到表、培训材料和参训反馈", "确认候选记录是否为面向团队的正式季度培训"],
        "records": [{"file_name": item.file_name, "category": item.file_category, "project_id": str(item.project_id)} for item in files[:30]],
    }


def _criterion7(db: Session, start_date: date, end_date: date, project_ids: set[UUID], threshold: dict[str, Any]) -> dict[str, Any]:
    pattern = re.compile(r"宣传|产品资料|介绍|视频|video|PPT|演示|brochure|方案", re.I)
    files = _keyword_files(db, start_date, end_date, pattern, project_ids)
    start_dt, end_dt = _bounds(start_date, end_date)
    attachment_query = (
        db.query(EmailAttachment, EmailMessage)
        .join(EmailMessage, EmailAttachment.email_id == EmailMessage.id)
        .filter(_in_period(EmailMessage.received_at, start_dt, end_dt))
    )
    if project_ids:
        attachment_query = attachment_query.filter(EmailMessage.project_id.in_(project_ids))
    attachments = [
        (attachment, email) for attachment, email in attachment_query.all()
        if pattern.search(f"{attachment.file_name} {attachment.document_type or ''}")
    ]
    candidates = len(files) + len(attachments)
    target = int(threshold.get("quarterly_material_count", 3))
    status = "部分达标" if candidates >= target else ("证据不足" if candidates else "无数据")
    return {
        "status": status,
        "conclusion": f"已找到 {candidates} 份宣传/方案/演示候选材料；是否达到正式宣传资料口径及质量要求仍需人工确认。",
        "metrics": [
            {"label": "季度目标", "value": target, "unit": "份"},
            {"label": "项目文件候选", "value": len(files), "unit": "份"},
            {"label": "邮件附件候选", "value": len(attachments), "unit": "份"},
        ],
        "evidence": [f"项目文件候选 {len(files)} 份", f"邮件附件候选 {len(attachments)} 份"],
        "gaps": ["确认至少3份材料的最终版本与成品链接", "补充客户或销售反馈", "区分项目方案与正式对外宣传资料"],
        "records": (
            [{"name": item.file_name, "source": "项目文件", "project_id": str(item.project_id)} for item in files]
            + [{"name": item.file_name, "source": "邮件附件", "email_id": str(email.id)} for item, email in attachments]
        )[:50],
    }


def build_summary(
    db: Session,
    *,
    user_id: UUID,
    start_date: date,
    end_date: date,
    period_label: str,
    period_type: str,
    scope: str,
    criteria: list[dict[str, Any]],
) -> dict[str, Any]:
    projects = _relevant_projects(db, start_date, end_date, scope, user_id)
    project_ids = {item.id for item in projects}
    start_dt, end_dt = _bounds(start_date, end_date)
    activity_query = db.query(ActivityLog).filter(_in_period(ActivityLog.occurred_at, start_dt, end_dt))
    email_query = db.query(EmailMessage).filter(_in_period(EmailMessage.received_at, start_dt, end_dt))
    file_query = db.query(ProjectFile).filter(_in_period(ProjectFile.created_at, start_dt, end_dt))
    if project_ids:
        activity_query = activity_query.filter(ActivityLog.project_id.in_(project_ids))
        email_query = email_query.filter(EmailMessage.project_id.in_(project_ids))
        file_query = file_query.filter(ProjectFile.project_id.in_(project_ids))
    elif scope == "owned_projects":
        activity_query = activity_query.filter(False)
        email_query = email_query.filter(False)
        file_query = file_query.filter(False)

    criterion_builders = {
        "c1": lambda t: _criterion1(db, projects, start_date, end_date, t),
        "c2": lambda t: _criterion2(db, start_date, end_date, project_ids, t),
        "c3": lambda t: _criterion3(db, start_date, end_date, project_ids),
        "c4": lambda t: _criterion4(db, start_date, end_date, project_ids, t),
        "c5": lambda t: _criterion5(db, projects, start_date, end_date, project_ids, t),
        "c6": lambda t: _criterion6(db, start_date, end_date, project_ids, t),
        "c7": lambda t: _criterion7(db, start_date, end_date, project_ids, t),
    }
    results = []
    for criterion in _merge_criteria(criteria):
        if not criterion["enabled"]:
            continue
        result = criterion_builders[criterion["code"]](criterion["thresholds"])
        results.append({**criterion, **result})
    status_counts = defaultdict(int)
    for item in results:
        status_counts[item["status"]] += 1
    return {
        "period": {
            "label": period_label,
            "type": period_type,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "scope": scope,
        },
        "source_summary": {
            "projects": len(projects),
            "activities": activity_query.count(),
            "emails": email_query.count(),
            "files": file_query.count(),
        },
        "status_summary": dict(status_counts),
        "criteria": results,
        "generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "notice": "本汇报只依据系统内已入库且已绑定的数据生成；证据不足不等同于工作未完成。",
    }


def generate_report(
    db: Session,
    *,
    user_id: UUID,
    start_date: date,
    end_date: date,
    period_label: str,
    period_type: str,
    scope: Optional[str] = None,
    trigger_type: str = "manual",
) -> OverseasPerformanceReport:
    config = get_or_create_config(db, user_id)
    actual_scope = scope or config.scope
    report = OverseasPerformanceReport(
        user_id=user_id,
        period_label=period_label,
        period_type=period_type,
        start_date=start_date,
        end_date=end_date,
        scope=actual_scope,
        trigger_type=trigger_type,
        status="生成中",
        summary_json={},
        generated_at=datetime.now(ZoneInfo("Asia/Shanghai")),
    )
    db.add(report)
    db.flush()
    try:
        report.summary_json = build_summary(
            db,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            period_label=period_label,
            period_type=period_type,
            scope=actual_scope,
            criteria=config.criteria_json,
        )
        report.status = "成功"
        config.last_run_at = datetime.now(ZoneInfo("Asia/Shanghai"))
    except Exception as exc:
        report.status = "失败"
        report.error_message = str(exc)
        raise
    db.flush()
    return report


def report_view(report: OverseasPerformanceReport) -> dict[str, Any]:
    return {
        "id": report.id,
        "period_label": report.period_label,
        "period_type": report.period_type,
        "start_date": report.start_date,
        "end_date": report.end_date,
        "scope": report.scope,
        "trigger_type": report.trigger_type,
        "status": report.status,
        "generated_at": report.generated_at,
        "summary": report.summary_json,
        "error_message": report.error_message,
    }


def previous_period(frequency: str, today: date) -> tuple[date, date, str, str]:
    if frequency == "monthly":
        first_current = today.replace(day=1)
        end = first_current - timedelta(days=1)
        start = end.replace(day=1)
        return start, end, f"{start.year}年{start.month}月海外绩效汇报", "previous_month"
    current_quarter = (today.month - 1) // 3
    if current_quarter == 0:
        year, quarter = today.year - 1, 4
    else:
        year, quarter = today.year, current_quarter
    start_month = (quarter - 1) * 3 + 1
    start = date(year, start_month, 1)
    end_month = start_month + 2
    end = date(year, end_month, calendar.monthrange(year, end_month)[1])
    return start, end, f"{year}年第{quarter}季度海外绩效汇报", "previous_quarter"


def run_due_scheduled_reports(db: Session, now: Optional[datetime] = None) -> int:
    now = now or datetime.now(ZoneInfo("Asia/Shanghai"))
    created = 0
    for config in db.query(OverseasPerformanceConfig).filter(OverseasPerformanceConfig.enabled.is_(True)).all():
        if now.day != config.schedule_day:
            continue
        if (now.hour, now.minute) < (config.schedule_hour, config.schedule_minute):
            continue
        if config.schedule_frequency == "quarterly" and now.month not in {1, 4, 7, 10}:
            continue
        start, end, label, period_type = previous_period(config.schedule_frequency, now.date())
        exists = db.query(OverseasPerformanceReport).filter(
            OverseasPerformanceReport.user_id == config.user_id,
            OverseasPerformanceReport.start_date == start,
            OverseasPerformanceReport.end_date == end,
            OverseasPerformanceReport.trigger_type == "scheduled",
        ).first()
        if exists:
            continue
        generate_report(
            db,
            user_id=config.user_id,
            start_date=start,
            end_date=end,
            period_label=label,
            period_type=period_type,
            scope=config.scope,
            trigger_type="scheduled",
        )
        created += 1
    return created
