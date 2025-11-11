"""
Pydantic validation models for API endpoints.
Ensures input validation, type safety, and range checking.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime


class MassDMJobRequest(BaseModel):
    """Validation for mass DM job creation"""
    account_id: int = Field(..., gt=0, description="Valid account ID")
    message: str = Field(..., min_length=1, max_length=10000, description="Message text 1-10000 chars")
    stop_after_hours: Optional[int] = Field(None, ge=1, le=720, description="1-30 days max")
    rate_limit_per_hour: Optional[int] = Field(None, ge=1, le=1000, description="Max 1000/hour (Telegram limit)")
    delay_seconds: Optional[int] = Field(None, ge=0, le=3600, description="0-1 hour delay")
    min_delay_seconds: Optional[int] = Field(None, ge=0, le=600, description="0-10 min delay")
    max_delay_seconds: Optional[int] = Field(None, ge=0, le=3600, description="0-1 hour delay")
    user_description: Optional[str] = Field(None, max_length=500)
    
    @validator('max_delay_seconds')
    def validate_max_delay(cls, v, values):
        """Ensure max_delay >= min_delay"""
        if v is not None and 'min_delay_seconds' in values:
            min_val = values['min_delay_seconds']
            if min_val is not None and v < min_val:
                raise ValueError('max_delay_seconds must be >= min_delay_seconds')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "account_id": 1,
                "message": "Hello! Check out our service.",
                "stop_after_hours": 24,
                "rate_limit_per_hour": 300,
                "min_delay_seconds": 30,
                "max_delay_seconds": 120,
            }
        }


class DistributedMassDMJobRequest(BaseModel):
    """Validation for distributed mass DM jobs"""
    message: str = Field(..., min_length=1, max_length=10000)
    account_ids: list = Field(..., min_items=2, description="At least 2 accounts for distribution")
    stop_after_hours: Optional[int] = Field(None, ge=1, le=720)
    rate_limit_per_hour: Optional[int] = Field(None, ge=1, le=1000)
    delay_seconds: Optional[int] = Field(None, ge=0, le=3600)
    min_delay_seconds: Optional[int] = Field(None, ge=0, le=600)
    max_delay_seconds: Optional[int] = Field(None, ge=0, le=3600)
    user_description: Optional[str] = Field(None, max_length=500)
    
    @validator('account_ids')
    def validate_account_ids(cls, v):
        """Validate account IDs are positive integers"""
        if not all(isinstance(acc_id, int) and acc_id > 0 for acc_id in v):
            raise ValueError('All account IDs must be positive integers')
        # Remove duplicates
        return list(set(v))
    
    class Config:
        schema_extra = {
            "example": {
                "message": "Hello! Check out our service.",
                "account_ids": [1, 2, 3],
                "min_delay_seconds": 30,
                "max_delay_seconds": 120,
            }
        }


class JobStatusUpdate(BaseModel):
    """Validation for job status updates"""
    status: str = Field(..., description="Job status")
    
    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['pending', 'running', 'paused', 'completed', 'failed']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v


class ProxyConfigRequest(BaseModel):
    """Validation for proxy configuration"""
    proxy_url: str = Field(..., min_length=10, max_length=500, description="Valid proxy URL")
    proxy_type: str = Field(..., description="http, https, or socks5")
    country_code: Optional[str] = Field(None, min_length=2, max_length=2)
    
    @validator('proxy_type')
    def validate_proxy_type(cls, v):
        valid_types = ['http', 'https', 'socks5']
        if v.lower() not in valid_types:
            raise ValueError(f'Proxy type must be one of: {", ".join(valid_types)}')
        return v.lower()
    
    class Config:
        schema_extra = {
            "example": {
                "proxy_url": "http://proxy.example.com:8080",
                "proxy_type": "http",
                "country_code": "US"
            }
        }


class AccountConfigRequest(BaseModel):
    """Validation for account configuration"""
    nickname: str = Field(..., min_length=1, max_length=100)
    api_id: Optional[int] = Field(None, gt=0)
    api_hash: Optional[str] = Field(None, min_length=32, max_length=64)
    proxy_id: Optional[int] = Field(None, gt=0)
    
    class Config:
        schema_extra = {
            "example": {
                "nickname": "Main Account",
                "api_id": 123456,
                "api_hash": "abcdef1234567890abcdef1234567890"
            }
        }


# File upload validation
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_FILE_TYPES = {'text/csv', 'application/vnd.ms-excel', 'image/jpeg', 'image/png', 'image/gif'}


class FileUploadValidator:
    """Helper class for validating file uploads"""
    
    @staticmethod
    def validate_csv_file(file_size: int, content_type: str) -> bool:
        """Validate CSV file"""
        if file_size > 10 * 1024 * 1024:  # 10MB for CSV
            raise ValueError("CSV file size must be less than 10MB")
        if content_type not in {'text/csv', 'application/vnd.ms-excel'}:
            raise ValueError(f"Invalid CSV content type: {content_type}")
        return True
    
    @staticmethod
    def validate_image_file(file_size: int, content_type: str) -> bool:
        """Validate image file"""
        if file_size > 5 * 1024 * 1024:  # 5MB for images
            raise ValueError("Image file size must be less than 5MB")
        if content_type not in {'image/jpeg', 'image/png', 'image/gif'}:
            raise ValueError(f"Invalid image type. Allowed: JPEG, PNG, GIF. Got: {content_type}")
        return True
