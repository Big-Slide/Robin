from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class WebhookStatus(Enum):
    """Status codes for the webhook"""
    pending = 0
    in_progress = 1
    completed = 2
    failed = 3


class FaceResult(BaseModel):
    """Schema for facial expression analysis results"""
    gender: str
    emotion: str
    bounding_box: List[int] = Field(..., description="[x, y, x1, y1]")


class FaceAnalysisRequest(BaseModel):
    """Schema for facial expression analysis request"""
    request_id: Optional[str] = None
    priority: int = 1
    language: Optional[str] = "en"


class TaskStatus(BaseModel):
    """Schema for task status"""
    request_id: str
    status: str  # "pending", "in_progress", "completed", "failed"
    itime: datetime
    utime: Optional[datetime] = None
    results: Optional[List[FaceResult]] = None
    error: Optional[str] = None


class WebhookRequest(BaseModel):
    """Schema for webhook request"""
    request_id: str


class WebhookResponse(BaseModel):
    """Schema for webhook response"""
    status: bool = False
    message: str = ""
    code: str = "0"  # 0=pending, 1=in_progress, 2=completed, 3=failed
    results: Optional[List[FaceResult]] = None


class ApiResponse(BaseModel):
    """Standard API response format"""
    status: bool = False
    message: str = ""
    code: str = ""
    data: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True