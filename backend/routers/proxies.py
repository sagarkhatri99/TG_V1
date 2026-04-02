from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import httpx
import time
from datetime import datetime

from database import get_db
from models import Proxy, User
from routers.auth import get_current_user
from core.dependencies import plan_based_dependency
from core.proxy_utils import parse_proxy_string, build_proxy_config
import requests

router = APIRouter()

class ProxyCreate(BaseModel):
    proxy_url: str
    proxy_type: str = "socks5"  # Always enforced as socks5 on backend
    country_code: str = "US"
    name: Optional[str] = None  # Optional human-readable label

class ProxyRename(BaseModel):
    name: str

class ProxyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: Optional[str] = None
    proxy_url: str
    proxy_type: str
    country_code: str
    status: str
    ip_address: Optional[str] = None
    response_time: Optional[int] = None

@router.post("/create", response_model=ProxyOut)
async def create_proxy(proxy: ProxyCreate, db: Session = Depends(get_db), current_user: User = Depends(plan_based_dependency("proxies"))):
    # Enforce SOCKS5 as per user requirement
    details = parse_proxy_string(proxy.proxy_url, "socks5")
    
    # Override proxy_type to socks5 if it's anything else
    final_type = "socks5"
    
    db_proxy = Proxy(
        proxy_url=proxy.proxy_url,
        proxy_type=final_type,
        country_code=proxy.country_code,
        name=proxy.name or None
    )
    db.add(db_proxy)
    db.commit()
    db.refresh(db_proxy)
    return db_proxy

@router.get("/list", response_model=List[ProxyOut])
async def list_proxies(db: Session = Depends(get_db), current_user: User = Depends(plan_based_dependency("proxies"))):
    proxies = db.query(Proxy).all()
    return proxies

@router.put("/{proxy_id}/rename")
async def rename_proxy(proxy_id: int, body: ProxyRename, db: Session = Depends(get_db), current_user: User = Depends(plan_based_dependency("proxies"))):
    """Rename/relabel a proxy for easier identification"""
    proxy = db.query(Proxy).filter(Proxy.id == proxy_id).first()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    
    proxy.name = body.name.strip()
    db.commit()
    db.refresh(proxy)
    return {"status": "success", "message": f"Proxy renamed to '{proxy.name}'", "id": proxy.id, "name": proxy.name}

@router.post("/{proxy_id}/test")
async def test_proxy(proxy_id: int, db: Session = Depends(get_db), current_user: User = Depends(plan_based_dependency("proxies"))):
    """Test proxy connection and detect IP address"""
    proxy = db.query(Proxy).filter(Proxy.id == proxy_id).first()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    
    try:
        # Measure response time
        start_time = time.time()
        
        # Build unified proxy config
        config = build_proxy_config(proxy)
        requests_proxies = config.get("requests")
        
        # Try multiple IP detection services for reliability
        ip_services = [
            "https://api.ipify.org?format=json",
            "https://ifconfig.me/ip",
            "https://icanhazip.com"
        ]
        
        detected_ip = None
        error_details = []

        for service_url in ip_services:
            try:
                # Use requests for better SOCKS support via PySocks
                response = requests.get(service_url, proxies=requests_proxies, timeout=15.0)
                response.raise_for_status()
                
                if "ipify" in service_url:
                    detected_ip = response.json().get("ip")
                else:
                    detected_ip = response.text.strip()
                
                if detected_ip:
                    break
            except Exception as e:
                error_details.append(f"{service_url}: {str(e)}")
                continue
        
        if not detected_ip:
            error_msg = "Could not detect IP from any service. " + " | ".join(error_details)
            raise Exception(error_msg)
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Update proxy status
        proxy.status = "active"
        proxy.ip_address = detected_ip
        proxy.response_time = response_time_ms
        proxy.last_check = datetime.utcnow()
        db.commit()
        db.refresh(proxy)
        
        return {
            "status": "success",
            "ip_address": detected_ip,
            "response_time": response_time_ms,
            "message": f"Proxy is working correctly. IP: {detected_ip}"
        }
        
    except Exception as e:
        proxy.status = "failed"
        proxy.last_check = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{proxy_id}")
async def delete_proxy(proxy_id: int, db: Session = Depends(get_db), current_user: User = Depends(plan_based_dependency("proxies"))):
    proxy = db.query(Proxy).filter(Proxy.id == proxy_id).first()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")

    # In a real system, you'd also need to un-assign it from any accounts.

    db.delete(proxy)
    db.commit()
    return {"status": "success", "message": "Proxy deleted"}
