from sqlalchemy import Column, String, DateTime, Integer, Enum, SmallInteger, JSON
from dbutils.database import Base
from core.utils import generate_uuid
from dbutils.schemas import WebhookStatus


def str(self) -> str:
    return " , ".join([f"{key}: {value}" for key, value in self.__dict__.items()][::-1])


def items(self) -> dict:
    result = {}
    for k, v in self.__dict__.items():
        if not k.startswith("_"):
            result[k] = v
    return result.items()


Base.__str__ = str
Base.items = items


class Manager(Base):
    """
    Database model for managing NC to Text OCR requests
    """
    __tablename__ = "nc_ocr_manager"

    id = Column(String(255), primary_key=True, default=generate_uuid)
    request_id = Column(String(255), nullable=False, unique=True)

    # Fields specific to NCtoText
    image_path = Column(String(255), nullable=True)  # Path to the stored image
    priority = Column(Integer, nullable=True, default=1)

    # Status tracking
    status = Column(Enum(WebhookStatus), nullable=False, default=WebhookStatus.pending)
    result = Column(JSON, nullable=True)  # Store OCR results as JSON
    error = Column(String(4000), nullable=True)

    # Webhook retry tracking
    webhook_retry_count = Column(SmallInteger, nullable=True, default=0)
    webhook_status_code = Column(SmallInteger, nullable=True)

    # Timestamps
    itime = Column(DateTime, nullable=False)  # Created time
    utime = Column(DateTime, nullable=True)  # Updated time

    # Additional information
    descr = Column(String(255), nullable=True)
    language = Column(String(10), nullable=True, default="fa")  # UI language preference