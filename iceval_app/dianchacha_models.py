from django.conf import settings
from sqlalchemy import Column, Integer, String, DateTime, text
from sqlalchemy.ext.declarative import declarative_base

import sqlalchemy as sa

db = sa.create_engine(f'postgresql+psycopg2://{settings.DIANCHACHA_POSTGRES_USER}:{settings.DIANCHACHA_POSTGRES_PASSWORD}@'
                     f'{settings.DIANCHACHA_POSTGRES_HOST}:{settings.DIANCHACHA_POSTGRES_PORT}/{settings.DIANCHACHA_POSTGRES_DB_NAME}',
                      echo=False, pool_size=10, pool_recycle=-1, pool_pre_ping=True,
                     max_overflow=10, pool_timeout=30)

Base = declarative_base()

class TradeEPDataMonth(Base):
    __tablename__ = "trade_ep_data_mon"

    data_type_id = Column(Integer, primary_key=True, nullable=False, index=True)
    region_id = Column(Integer, nullable=False, index=True)
    data_value = Column(String(512))
    data_source_id = Column(Integer, nullable=False, index=True)
    data_time = Column(DateTime, nullable=False, index=True)
    remark = Column(String(256))
    operator = Column(String(64))
    create_time = Column(DateTime(timezone=True), server_default=text("now()"))
    update_time = Column(DateTime(timezone=True), server_default=text("now()"))