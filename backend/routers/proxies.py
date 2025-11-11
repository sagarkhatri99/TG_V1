from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import List

from database import get_db
from models import Proxy, User
from routers.auth import get_current_user
from core.dependencies import plan_based_dependency

router = APIRouter()

class ProxyCreate(BaseModel):
    proxy_url: str
    proxy_type: str = "http"
    country_code: str = "US"

class ProxyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    proxy_url: str
    proxy_type: str
    country_code: str
    status: str

@router.post("/create", response_model=ProxyOut)
async def create_proxy(proxy: ProxyCreate, db: Session = Depends(get_db), current_user: User = Depends(plan_based_dependency("proxies"))):
    # In a real multi-tenant system, proxies might be owned by users.
    # For now, we'll treat them as global.
    db_proxy = Proxy(**proxy.dict())
    db.add(db_proxy)
    db.commit()
    db.refresh(db_proxy)
    return db_proxy

@router.get("/list", response_model=List[ProxyOut])
async def list_proxies(db: Session = Depends(get_db), current_user: User = Depends(plan_based_dependency("proxies"))):
    proxies = db.query(Proxy).all()
    return proxies

@router.delete("/{proxy_id}")
async def delete_proxy(proxy_id: int, db: Session = Depends(get_db), current_user: User = Depends(plan_based_dependency("proxies"))):
    proxy = db.query(Proxy).filter(Proxy.id == proxy_id).first()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")

    # In a real system, you'd also need to un-assign it from any accounts.

    db.delete(proxy)
    db.commit()
    return {"status": "success", "message": "Proxy deleted"}
