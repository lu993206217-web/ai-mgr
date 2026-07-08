"""
通用 Schema

所有模块共用的 Pydantic 模型。
"""
from typing import Generic, TypeVar, Generic, List, Optional
from pydantic import BaseModel, Field


# 泛型类型
DataT = TypeVar("DataT")


class PaginationParams(BaseModel):
    """分页参数基础 Schema"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")
    
    @property
    def offset(self) -> int:
        """计算偏移量"""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """计算限制数量"""
        return self.page_size


class PaginatedResponse(BaseModel, Generic[DataT]):
    """分页响应 Schema"""
    items: List[DataT] = Field(..., description="数据列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    total_pages: int = Field(..., description="总页数")
    
    @classmethod
    def create(cls, items: List[DataT], total: int, page: int, page_size: int):
        """创建分页响应"""
        total_pages = (total + page_size - 1) // page_size
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )


class Response(BaseModel, Generic[DataT]):
    """统一响应 Schema"""
    code: int = Field(default=200, description="响应代码")
    message: str = Field(default="success", description="响应消息")
    data: Optional[DataT] = Field(None, description="响应数据")
    
    @classmethod
    def success(cls, data: Optional[DataT] = None, message: str = "success"):
        """创建成功响应"""
        return cls(code=200, message=message, data=data)
    
    @classmethod
    def error(cls, code: int = 400, message: str = "error"):
        """创建错误响应"""
        return cls(code=code, message=message, data=None)
