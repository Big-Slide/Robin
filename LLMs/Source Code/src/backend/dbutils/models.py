from sqlalchemy import Column, String, DateTime, Integer, Enum, SmallInteger
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
# Base.__repr__ = str


class Manager(Base):
    __tablename__ = "manager"

    id = Column(String(255), primary_key=True, default=generate_uuid)
    request_id = Column(String(255), nullable=False, unique=True)
    task = Column(String(255), nullable=False)
    input1_path = Column(String(4000), nullable=False)
    input2_path = Column(String(4000), nullable=True)
    priority = Column(Integer, nullable=True)
    model = Column(String(255), nullable=True)
    status = Column(Enum(WebhookStatus), nullable=False, default=WebhookStatus.pending)
    result = Column(String(4000), nullable=True)
    error = Column(String(4000), nullable=True)
    webhook_retry_count = Column(SmallInteger, nullable=True)
    webhook_status_code = Column(SmallInteger, nullable=True)
    itime = Column(DateTime, nullable=False)
    utime = Column(DateTime, nullable=True)
    descr = Column(String(255), nullable=True)
