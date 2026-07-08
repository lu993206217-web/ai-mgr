"""
认证 API 路由

处理用户登录、Token 刷新、登出、当前用户信息查询。
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose.exceptions import JWTError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
    get_password_hash,
)
from app.db.session import get_db
from app.models.user import User as UserModel
from app.schemas.user import (
    User,
    UserCreate,
    Token,
    LoginRequest,
    TokenPayload,
)
from app.schemas.common import Response

router = APIRouter(tags=["认证"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


# ============ 依赖注入：获取当前用户 ============
async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> UserModel:
    """
    获取当前登录用户
    
    用于 FastAPI 依赖注入，保护需要认证的 API。
    """
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证凭证",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(UserModel).filter(UserModel.id == user_uuid).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已禁用",
        )
    
    return user


# ============ 登录接口 ============
@router.post("/login", response_model=Response[Token])
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
) -> Any:
    """
    用户登录
    
    验证用户名和密码，返回 access_token 和 refresh_token。
    """
    # 查找用户
    user = db.query(UserModel).filter(UserModel.username == login_data.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # 验证密码
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已禁用",
        )
    
    # 更新最后登录时间
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    # 生成 Token
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    
    return Response.success(
        data=Token(
            access_token=access_token,
            refresh_token=refresh_token,
        ),
        message="登录成功",
    )


# ============ 刷新 Token 接口 ============
@router.post("/refresh", response_model=Response[Token])
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db),
) -> Any:
    """
    刷新访问 Token
    
    使用 refresh_token 获取新的 access_token。
    """
    try:
        payload = decode_token(refresh_token)
        token_type: str = payload.get("type")
        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新 Token",
            )
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新 Token",
            )
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新 Token",
        )
    
    user = db.query(UserModel).filter(UserModel.id == UUID(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已禁用",
        )
    access_token = create_access_token(user.id)
    new_refresh_token = create_refresh_token(user.id)
    
    return Response.success(
        data=Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
        ),
        message="Token 刷新成功",
    )


# ============ 登出接口 ============
@router.post("/logout", response_model=Response)
async def logout() -> Any:
    """
    用户登出
    
    前端需要自行删除本地存储的 Token。
    """
    return Response.success(message="登出成功")


# ============ 获取当前用户接口 ============
@router.get("/me", response_model=Response[User])
async def get_me(
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """
    获取当前登录用户信息
    """
    return Response.success(data=current_user, message="获取成功")
