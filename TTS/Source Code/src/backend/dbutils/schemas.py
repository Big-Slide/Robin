from typing import Optional
from pydantic import BaseModel
from datetime import datetime
from enum import Enum


class GenerateRequest(BaseModel):
    text: str
    lang: str = "fa"
    model: str = None
    request_id: str = None
    priority: int = 1


class WebhookStatus(Enum):
    pending = 0
    in_progress = 1
    completed = 2
    failed = 3


class TaskStatus(BaseModel):
    request_id: str
    status: str  # "pending", "processing", "completed", "failed"
    itime: datetime
    utime: Optional[datetime] = None
    result_path: Optional[str] = None
    error: Optional[str] = None


class vm_response(BaseModel):
    status: bool = False
    message: str = ""
    code: str = ""
    data: dict = None

    class Config:
        from_attributes = True
