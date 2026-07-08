"""
用户管理 API 路由

用户 CRUD 操作。
"""
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user, get_password_hash
from app.db.session import get_db
from app.models.user import User as UserModel
from app.schemas.user import (
    User as UserSchema,
    UserCreate,
    UserUpdate,
)
from app.schemas.common import Response, PaginatedResponse

router = APIRouter(tags=["用户管理"])


@router.get("", response_model=Response[PaginatedResponse[UserSchema]])
async def get_users(
    username: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取用户列表"""
    query = db.query(UserModel)

    if username:
        query = query.filter(UserModel.username.ilike(f"%{username}%"))
    if role:
        query = query.filter(UserModel.role == role)

    total = query.count()
    offset = (page - 1) * page_size
    users = query.order_by(UserModel.created_at.desc()).offset(offset).limit(page_size).all()

    return Response.success(
        data=PaginatedResponse.create(items=users, total=total, page=page, page_size=page_size),
        message="获取成功",
    )


@router.get("/{user_id}", response_model=Response[UserSchema])
async def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取用户详情"""
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    return Response.success(data=user, message="获取成功")


@router.post("", response_model=Response[UserSchema])
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """创建新用户"""
    # 检查用户名是否已存在
    existing = db.query(UserModel).filter(UserModel.username == user_data.username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")

    # 检查邮箱是否已存在
    if user_data.email:
        existing_email = db.query(UserModel).filter(UserModel.email == user_data.email).first()
        if existing_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已存在")

    user = UserModel(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role,
        hashed_password=get_password_hash(user_data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return Response.success(data=user, message="创建成功")


@router.put("/{user_id}", response_model=Response[UserSchema])
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """更新用户信息"""
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    update_data = user_data.model_dump(exclude_unset=True)
    
    # 如果更新密码，需要哈希处理
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(user, field, value)

    user.updated_at = datetime.now()

    db.commit()
    db.refresh(user)

    return Response.success(data=user, message="更新成功")


@router.delete("/{user_id}", response_model=Response)
async def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """删除用户"""
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    # 不能删除自己
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除自己")

    db.delete(user)
    db.commit()

    return Response.success(message="删除成功")
