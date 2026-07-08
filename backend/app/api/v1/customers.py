from uuid import UUID
"""
客户管理 API 路由
"""
from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User as UserModel
from app.models.customer import Customer as CustomerModel
from app.schemas.customer import (
    Customer as CustomerSchema,
    CustomerCreate,
    CustomerUpdate,
)
from app.schemas.common import Response, PaginatedResponse

router = APIRouter(tags=["客户管理"])


@router.get("", response_model=Response[PaginatedResponse[CustomerSchema]])
async def get_customers(
    country: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取客户列表"""
    query = db.query(CustomerModel)

    if country:
        query = query.filter(CustomerModel.country == country)

    total = query.count()
    offset = (page - 1) * page_size
    customers = query.order_by(CustomerModel.created_at.desc()).offset(offset).limit(page_size).all()

    return Response.success(
        data=PaginatedResponse.create(items=customers, total=total, page=page, page_size=page_size),
        message="获取成功",
    )


@router.get("/{customer_id}", response_model=Response[CustomerSchema])
async def get_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取客户详情"""
    customer = db.query(CustomerModel).filter(CustomerModel.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="客户不存在")

    return Response.success(data=customer, message="获取成功")


@router.post("", response_model=Response[CustomerSchema])
async def create_customer(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """创建新客户"""
    existing = db.query(CustomerModel).filter(CustomerModel.customer_name == customer_data.customer_name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="客户名称已存在")

    customer = CustomerModel(
        **customer_data.model_dump(),
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)

    return Response.success(data=customer, message="创建成功")


@router.put("/{customer_id}", response_model=Response[CustomerSchema])
async def update_customer(
    customer_id: UUID,
    customer_data: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """更新客户信息"""
    customer = db.query(CustomerModel).filter(CustomerModel.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="客户不存在")

    update_data = customer_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)

    customer.updated_by = current_user.id
    customer.updated_at = datetime.now()

    db.commit()
    db.refresh(customer)

    return Response.success(data=customer, message="更新成功")


@router.delete("/{customer_id}", response_model=Response)
async def delete_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """删除客户"""
    customer = db.query(CustomerModel).filter(CustomerModel.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="客户不存在")

    if customer.projects:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="客户下有关联项目，无法删除")

    db.delete(customer)
    db.commit()

    return Response.success(message="删除成功")
