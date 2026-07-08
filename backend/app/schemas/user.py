"""
用户 Schema

Pydantic 模型，用于 API 请求和响应的数据验证。
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ============ 基础 Schema ============
class UserBase(BaseModel):
    """用户基础 Schema"""
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    role: str = Field(default="项目经理", max_length=50)


class UserCreate(UserBase):
    """用户创建 Schema"""
    password: str = Field(..., min_length=8, max_length=50)


class UserUpdate(BaseModel):
    """用户更新 Schema"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8, max_length=50)


class UserInDB(UserBase):
    """用户数据库 Schema"""
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class User(UserInDB):
    """用户响应 Schema"""
    pass


# ============ 认证 Schema ============
class Token(BaseModel):
    """Token 响应 Schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Token 载荷 Schema"""
    sub: Optional[UUID] = None
    exp: Optional[int] = None


class LoginRequest(BaseModel):
    """登录请求 Schema"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=50)
