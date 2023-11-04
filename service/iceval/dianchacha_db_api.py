from sqlalchemy import select

from iceval_app.dianchacha_models import db,TradeEPDataMonth
from sqlalchemy.orm import Session


def get_trade_ep_data_month(data_type_id, region_id, data_time):
    with Session(db) as session:
        statement = select(TradeEPDataMonth).filter_by(data_type_id=data_type_id, region_id=region_id, data_time=data_time)
        user_obj = session.scalars(statement).all()
        if user_obj:
            for row in user_obj:
                print(row.data_type_id, row.region_id, row.data_value, row.data_source_id, row.data_time, row.remark, row.operator, row.create_time, row.update_time)
                return row.data_value
        return []

