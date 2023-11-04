import datetime

from django.conf import settings
from sqlalchemy import String, DateTime, text
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column


import sqlalchemy as sa

db = sa.create_engine(f'postgresql://{settings.DIANCHACHA_POSTGRES_USER}:{settings.DIANCHACHA_POSTGRES_PASSWORD}@'
                       f'{settings.DIANCHACHA_POSTGRES_HOST}:{settings.DIANCHACHA_POSTGRES_PORT}/{settings.DIANCHACHA_POSTGRES_DB_NAME}', echo=False, pool_size=5, pool_recycle=-1, pool_pre_ping=False,
                      max_overflow=10, pool_timeout=30)


class TradeEPDataMonth(DeclarativeBase):
    __tablename__ = "trade_ep_data_mon"

    data_type_id: Mapped[int] = mapped_column(nullable=False, index=True)
    region_id: Mapped[int] = mapped_column(nullable=False, index=True)
    data_value: Mapped[str] = mapped_column(String(512))
    data_source_id: Mapped[int] = mapped_column(nullable=False, index=True)
    data_time: Mapped[str] = mapped_column(nullable=False, index=True)
    remark: Mapped[str] = mapped_column(String(256))
    operator: Mapped[str] = mapped_column(String(64))
    create_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    update_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    class Meta:
        db_table = "trade_ep_data_mon"

DeclarativeBase.metadata.create_all(checkfirst=True, bind=db)