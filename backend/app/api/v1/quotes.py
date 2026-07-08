from uuid import UUID, uuid4
"""
报价管理 API 路由

软件报价单 CRUD - 支持多产品授权 + 实施服务。
"""
from datetime import datetime, date
from typing import Any, List, Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User as UserModel
from app.models.quote import Quote as QuoteModel
from app.schemas.quote import (
    Quote as QuoteSchema,
    QuoteCreate,
    QuoteUpdate,
)
from app.schemas.common import Response, PaginatedResponse

router = APIRouter(tags=["报价管理"])


def _calc_quote_amounts(quote_data: dict) -> dict:
    """计算报价单的各项金额（授权小计、服务小计、折扣、税额、总计）"""
    # 计算每项授权小计 = qty * unit_price
    license_subtotal = Decimal("0")
    for item in quote_data.get("license_items", []):
        qty = Decimal(str(item.get("qty", 1)))
        unit_price = Decimal(str(item.get("unit_price", 0)))
        item["subtotal"] = qty * unit_price
        license_subtotal += item["subtotal"]

    # 计算每项服务小计 = quantity * daily_rate
    service_subtotal = Decimal("0")
    for item in quote_data.get("service_items", []):
        quantity = Decimal(str(item.get("quantity", 0)))
        daily_rate = Decimal(str(item.get("daily_rate", 0)))
        item["subtotal"] = quantity * daily_rate
        service_subtotal += item["subtotal"]

    # 汇总计算
    base_total = license_subtotal + service_subtotal
    discount_rate = Decimal(str(quote_data.get("discount_rate", 0)))
    discount_amount = (base_total * discount_rate / Decimal("100")).quantize(Decimal("0.01"))
    after_discount = base_total - discount_amount
    tax_rate = Decimal(str(quote_data.get("tax_rate", 0)))
    tax_amount = (after_discount * tax_rate / Decimal("100")).quantize(Decimal("0.01"))
    grand_total = (after_discount + tax_amount).quantize(Decimal("0.01"))

    quote_data["license_subtotal"] = license_subtotal.quantize(Decimal("0.01"))
    quote_data["service_subtotal"] = service_subtotal.quantize(Decimal("0.01"))
    quote_data["discount_amount"] = discount_amount
    quote_data["tax_amount"] = tax_amount
    quote_data["grand_total"] = grand_total

    return quote_data


def _generate_quote_no(db: Session) -> str:
    """生成报价单号: QT-YYYYMMDD-NNN"""
    today = date.today().strftime("%Y%m%d")
    count_today = db.query(QuoteModel).filter(
        QuoteModel.quote_no.like(f"QT-{today}%")
    ).count()
    return f"QT-{today}-{count_today + 1:03d}"


@router.get("", response_model=Response[PaginatedResponse[QuoteSchema]])
async def get_quotes(
    customer_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取报价列表"""
    query = db.query(QuoteModel)

    if customer_id:
        query = query.filter(QuoteModel.customer_id == customer_id)
    if project_id:
        query = query.filter(QuoteModel.project_id == project_id)

    total = query.count()
    offset = (page - 1) * page_size
    quotes = query.order_by(QuoteModel.created_at.desc()).offset(offset).limit(page_size).all()

    quote_list = []
    for q in quotes:
        q_dict = QuoteSchema.model_validate(q)
        q_dict.customer_name = q.customer.customer_name if q.customer else None
        q_dict.project_name = q.project.project_name if q.project else None
        q_dict.owner_name = q.owner.full_name if hasattr(q, 'owner') and q.owner else None
        quote_list.append(q_dict)

    return Response.success(
        data=PaginatedResponse.create(items=quote_list, total=total, page=page, page_size=page_size),
        message="获取成功",
    )


@router.get("/{quote_id}", response_model=Response[QuoteSchema])
async def get_quote(
    quote_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """获取报价详情"""
    quote = db.query(QuoteModel).filter(QuoteModel.id == quote_id).first()
    if not quote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报价不存在")

    q_dict = QuoteSchema.model_validate(quote)
    q_dict.customer_name = quote.customer.customer_name if quote.customer else None
    q_dict.project_name = quote.project.project_name if quote.project else None
    q_dict.owner_name = quote.owner.full_name if hasattr(quote, 'owner') and quote.owner else None

    return Response.success(data=q_dict, message="获取成功")


@router.post("", response_model=Response[QuoteSchema])
async def create_quote(
    quote_data: QuoteCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """创建新报价单（软件授权+实施服务）"""
    create_data = quote_data.model_dump()

    # 自动生成报价单号
    if not create_data.get("quote_no"):
        create_data["quote_no"] = _generate_quote_no(db)

    # 自动设置负责人为当前用户
    create_data["owner_id"] = current_user.id

    # 计算各项金额
    create_data = _calc_quote_amounts(create_data)

    quote = QuoteModel(
        **create_data,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(quote)
    db.commit()
    db.refresh(quote)

    return Response.success(data=QuoteSchema.model_validate(quote), message="创建成功")


@router.put("/{quote_id}", response_model=Response[QuoteSchema])
async def update_quote(
    quote_id: UUID,
    quote_data: QuoteUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """更新报价信息"""
    quote = db.query(QuoteModel).filter(QuoteModel.id == quote_id).first()
    if not quote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报价不存在")

    update_data = quote_data.model_dump(exclude_unset=True)

    # 如果授权项或服务项有更新，重新计算金额
    if "license_items" in update_data or "service_items" in update_data:
        # 合并已有数据与更新数据
        merged = {
            "license_items": update_data.get("license_items", quote.license_items or []),
            "service_items": update_data.get("service_items", quote.service_items or []),
            "discount_rate": update_data.get("discount_rate", quote.discount_rate),
            "tax_rate": update_data.get("tax_rate", quote.tax_rate),
        }
        calc = _calc_quote_amounts(merged)
        update_data["license_subtotal"] = calc["license_subtotal"]
        update_data["service_subtotal"] = calc["service_subtotal"]
        update_data["discount_amount"] = calc["discount_amount"]
        update_data["tax_amount"] = calc["tax_amount"]
        update_data["grand_total"] = calc["grand_total"]
        # 更新每项的subtotal
        if "license_items" in update_data:
            update_data["license_items"] = calc["license_items"]
        if "service_items" in update_data:
            update_data["service_items"] = calc["service_items"]

    for field, value in update_data.items():
        setattr(quote, field, value)

    quote.updated_by = current_user.id
    quote.updated_at = datetime.now()

    db.commit()
    db.refresh(quote)

    return Response.success(data=QuoteSchema.model_validate(quote), message="更新成功")


@router.delete("/{quote_id}", response_model=Response)
async def delete_quote(
    quote_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """删除报价"""
    quote = db.query(QuoteModel).filter(QuoteModel.id == quote_id).first()
    if not quote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报价不存在")

    db.delete(quote)
    db.commit()

    return Response.success(message="删除成功")
