"""消息中心连接与业务联动配置 API。"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user
from app.models.user import User as UserModel
from app.schemas.common import Response
from app.schemas.message_linkage import (
    MessageCenterHealthResult,
    MessageLinkageConfigUpdate,
    MessageLinkageConfigView,
)
from app.services.message_center import (
    check_message_center_health,
    get_message_center_config_view,
    save_message_center_config,
)


router = APIRouter(tags=["消息联动"])


@router.get("/config", response_model=Response[MessageLinkageConfigView])
async def get_config(
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    return Response.success(
        data=MessageLinkageConfigView(**get_message_center_config_view()),
        message="获取成功",
    )


@router.put("/config", response_model=Response[MessageLinkageConfigView])
async def update_config(
    body: MessageLinkageConfigUpdate,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    try:
        data = save_message_center_config(
            enabled=body.enabled,
            base_url=body.base_url,
            api_key=body.api_key,
            clear_api_key=body.clear_api_key,
            source_system=body.source_system,
            timeout_seconds=body.timeout_seconds,
            linkage_rules=[rule.model_dump() for rule in body.linkage_rules],
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return Response.success(data=MessageLinkageConfigView(**data), message="消息联动配置已保存")


@router.post("/health-test", response_model=Response[MessageCenterHealthResult])
async def health_test(
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    result = check_message_center_health()
    return Response.success(data=MessageCenterHealthResult(**result), message=result["message"])
