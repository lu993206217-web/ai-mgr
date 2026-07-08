"""
系统配置 API 路由

驾驶舱阈值配置和预警规则配置管理。
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User as UserModel
from app.schemas.config import (
    DashboardThresholds,
    DashboardThresholdsUpdate,
)
from app.schemas.common import Response

router = APIRouter(tags=["系统配置"])

# 配置文件路径
CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "data"
CONFIG_FILE = CONFIG_DIR / "thresholds.json"

# 默认阈值配置
DEFAULT_THRESHOLDS = {
    "zombie_project_days": 30,
    "fake_progress_count": 3,
    "sunk_channel_days": 60,
    "overdue_acceptance_days": 0,
    "sunk_channel_warning_days": 90,
    "waiting_too_long_days": 0,
    "today_followup_limit": 10,
    "poc_overdue_days": 60,
    "acceptance_overdue_days": 30,
    "acceptance_plan_overdue_days": 180,
    "no_activity_warning_days": 7,
    "quote_no_progress_days": 90,
}


def _load_thresholds() -> dict:
    """加载阈值配置"""
    if not CONFIG_FILE.exists():
        # 初始化默认配置
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _save_thresholds(DEFAULT_THRESHOLDS.copy())
        return DEFAULT_THRESHOLDS.copy()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 合并默认配置（防止新增字段缺失）
        merged = DEFAULT_THRESHOLDS.copy()
        merged.update(data)
        return merged
    except Exception:
        return DEFAULT_THRESHOLDS.copy()


def _save_thresholds(data: dict) -> None:
    """保存阈值配置"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now().isoformat()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_thresholds() -> dict:
    """获取当前阈值（供其他模块调用）"""
    return _load_thresholds()


@router.get("/thresholds", response_model=Response[DashboardThresholds])
async def get_dashboard_thresholds(
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取驾驶舱阈值配置"""
    data = _load_thresholds()
    return Response.success(data=DashboardThresholds(**data), message="获取成功")


@router.put("/thresholds", response_model=Response[DashboardThresholds])
async def update_dashboard_thresholds(
    thresholds: DashboardThresholdsUpdate,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """更新驾驶舱阈值配置"""
    data = _load_thresholds()
    update_data = thresholds.model_dump(exclude_unset=True)
    data.update(update_data)
    data["updated_at"] = datetime.now().isoformat()
    _save_thresholds(data)
    return Response.success(data=DashboardThresholds(**data), message="更新成功")


@router.post("/thresholds/reset", response_model=Response[DashboardThresholds])
async def reset_dashboard_thresholds(
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """重置驾驶舱阈值为默认值"""
    data = DEFAULT_THRESHOLDS.copy()
    data["updated_at"] = datetime.now().isoformat()
    _save_thresholds(data)
    return Response.success(data=DashboardThresholds(**data), message="重置成功")
