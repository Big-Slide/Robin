from sqlalchemy.orm import Session
from dbutils import models
from loguru import logger
from core.messages import Message  # Fixed import
from datetime import datetime
from dbutils.schemas import WebhookStatus
from typing import Dict


def clear_database(db: Session):
    try:
        db.query(models.Manager).delete()
        db.commit()
        return True
    except Exception as exp:
        logger.opt(exception=False, colors=True).warning(f"Failed: {exp.args}")
        db.rollback()
        return False


def get_request(
    db: Session,
    request_id: str,
):
    item = (
        db.query(models.Manager).filter(models.Manager.request_id == request_id).first()
    )
    return item


def add_request(db: Session, **kwargs):
    kwargs["itime"] = datetime.now(tz=None)
    item = models.Manager(**kwargs)
    try:
        db.add(item)
        db.commit()
        return Message("fa").INF_SUCCESS()
    except Exception:
        logger.opt(exception=True, colors=True).error("Failed to add_request")
        msg = Message("fa").ERR_FAILED_TO_ADD_TO_DB()
        return msg


def update_request(
    db: Session, request_id: str, status: WebhookStatus, result: Dict, error: str = None
):
    item = (
        db.query(models.Manager).filter(models.Manager.request_id == request_id).first()
    )
    if item is None:
        return False
    item.utime = datetime.now(tz=None)
    item.status = status
    item.result = result
    if error is not None:
        item.error = error
    try:
        db.commit()
        return True
    except Exception:
        logger.opt(exception=True, colors=True).error("Failed to update_request")
        return False