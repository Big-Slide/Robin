from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.config_handler import config
import os


def _fk_pragma_on_connect(dbapi_con, con_record):
    dbapi_con.execute("pragma foreign_keys=ON")


if "sqlite" in config["DB_CONNECTION"]:
    engine = create_engine(
        config["DB_CONNECTION"],
        connect_args={"check_same_thread": False},
        pool_recycle=3600,
    )
    from sqlalchemy import event

    event.listen(engine, "connect", _fk_pragma_on_connect)
elif "mysql" in config["DB_CONNECTION"]:
    engine = create_engine(config["DB_CONNECTION"], pool_recycle=3600)
elif "oracle" in config["DB_CONNECTION"]:
    engine = create_engine(config["DB_CONNECTION"], pool_recycle=3600)

# This called before base inialization
os.makedirs(config["DB_DIR"], exist_ok=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
