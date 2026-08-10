"""
نقاط نهاية رموز الأسهم
Stock Symbols Endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.db.database import get_db
from app.models.symbol import Symbol
from pydantic import BaseModel

router = APIRouter()


class SymbolResponse(BaseModel):
    """نموذج استجابة الرمز"""
    id: int
    ticker: str
    name_ar: str
    name_en: Optional[str]
    sector: Optional[str]
    market_cap: Optional[str]
    currency: str
    is_active: bool
    
    class Config:
        from_attributes = True


class SymbolCreate(BaseModel):
    """نموذج إنشاء رمز جديد"""
    ticker: str
    name_ar: str
    name_en: Optional[str] = None
    sector: Optional[str] = None
    market_cap: Optional[str] = None
    currency: str = "SAR"
    description: Optional[str] = None


@router.get("/symbols", response_model=List[SymbolResponse])
async def get_symbols(
    skip: int = Query(0, ge=0, description="عدد الرموز المراد تخطيها"),
    limit: int = Query(100, ge=1, le=1000, description="عدد الرموز المراد جلبها"),
    sector: Optional[str] = Query(None, description="فلترة حسب القطاع"),
    search: Optional[str] = Query(None, description="البحث في الاسم أو الرمز"),
    active_only: bool = Query(True, description="عرض الرموز النشطة فقط"),
    db: Session = Depends(get_db)
):
    """جلب قائمة رموز الأسهم مع إمكانية الفلترة والبحث"""
    
    query = db.query(Symbol)
    
    # فلترة الرموز النشطة
    if active_only:
        query = query.filter(Symbol.is_active == True)
    
    # فلترة حسب القطاع
    if sector:
        query = query.filter(Symbol.sector == sector)
    
    # البحث في الاسم أو الرمز
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Symbol.ticker.ilike(search_term),
                Symbol.name_ar.ilike(search_term),
                Symbol.name_en.ilike(search_term)
            )
        )
    
    # ترتيب النتائج
    query = query.order_by(Symbol.ticker)
    
    # تطبيق التصفح
    symbols = query.offset(skip).limit(limit).all()
    
    return symbols


@router.get("/symbols/{symbol_id}", response_model=SymbolResponse)
async def get_symbol(symbol_id: int, db: Session = Depends(get_db)):
    """جلب تفاصيل رمز معين"""
    symbol = db.query(Symbol).filter(Symbol.id == symbol_id).first()
    if not symbol:
        raise HTTPException(status_code=404, detail="الرمز غير موجود")
    return symbol


@router.get("/symbols/ticker/{ticker}", response_model=SymbolResponse)
async def get_symbol_by_ticker(ticker: str, db: Session = Depends(get_db)):
    """جلب تفاصيل رمز معين بالرمز"""
    symbol = db.query(Symbol).filter(Symbol.ticker == ticker.upper()).first()
    if not symbol:
        raise HTTPException(status_code=404, detail="الرمز غير موجود")
    return symbol


@router.get("/sectors")
async def get_sectors(db: Session = Depends(get_db)):
    """جلب قائمة القطاعات المتاحة"""
    sectors = db.query(Symbol.sector).filter(
        Symbol.sector.isnot(None),
        Symbol.is_active == True
    ).distinct().all()
    
    return {
        "sectors": [sector[0] for sector in sectors if sector[0]]
    }


@router.post("/symbols", response_model=SymbolResponse)
async def create_symbol(symbol: SymbolCreate, db: Session = Depends(get_db)):
    """إنشاء رمز جديد (للمشرفين فقط)"""
    # التحقق من عدم وجود الرمز مسبقاً
    existing_symbol = db.query(Symbol).filter(Symbol.ticker == symbol.ticker.upper()).first()
    if existing_symbol:
        raise HTTPException(status_code=400, detail="الرمز موجود مسبقاً")
    
    # إنشاء الرمز الجديد
    db_symbol = Symbol(
        ticker=symbol.ticker.upper(),
        name_ar=symbol.name_ar,
        name_en=symbol.name_en,
        sector=symbol.sector,
        market_cap=symbol.market_cap,
        currency=symbol.currency,
        description=symbol.description
    )
    
    db.add(db_symbol)
    db.commit()
    db.refresh(db_symbol)
    
    return db_symbol

