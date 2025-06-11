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


class TextEntry(BaseModel):
    """Schema for a single text entry from OCR"""
    index: int
    text: str
    confidence: float
    position: Dict[str, int]


class CardData(BaseModel):
    """Schema for data from a single ID card"""
    bbox: List[int]
    texts: List[TextEntry]
    skew_corrected: bool
    image_path: Optional[str] = None


class OCRResult(BaseModel):
    """Schema for OCR results from ID card processing"""
    text_data: List[CardData]
    image_path: str
    processed_images: List[str]
    cards_detected: int
    processing_time: float


class NCOCRRequest(BaseModel):
    """Schema for NC to Text OCR request"""
    request_id: Optional[str] = None
    priority: int = 1
    language: Optional[str] = "fa"


class TaskStatus(BaseModel):
    """Schema for task status"""
    request_id: str
    status: str  # "pending", "in_progress", "completed", "failed"
    itime: datetime
    utime: Optional[datetime] = None
    results: Optional[OCRResult] = None
    error: Optional[str] = None


class WebhookRequest(BaseModel):
    """Schema for webhook request"""
    request_id: str


class WebhookResponse(BaseModel):
    """Schema for webhook response"""
    status: bool = False
    message: str = ""
    code: str = ""
    results: Optional[OCRResult] = None


class ApiResponse(BaseModel):
    """Standard API response format"""
    status: bool = False
    message: str = ""
    code: str = ""
    data: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True