from sqlalchemy import select, and_
from iceval_app.dianchacha_models import db, TradeEPDataMonth
from sqlalchemy.orm import sessionmaker
from utils.time_utils import get_now_time

Session = sessionmaker(bind=db)


def get_trade_data_for_time(session, region_id, data_type_dic, data_time):
    """
    获取指定时间的电价数据, 优先使用指定时间的数据，如果没有则使用最近的数据
    params: session: 数据库会话
    params: region_id: 区域ID
    params: data_type_dic: 数据类型字典
    params: data_time: 数据时间
    return: 电价数据 {peak: 0.1234, flat: 0.1234, normal: 0.1234, valley: 0.1234, low: 0.1234}
    """
    trade_ep_dic = {"peak": None, "flat": None, "normal": None, "valley": None, "low": None}
    type_id_to_price_type = {
        data_type_dic["peak_type_id"]: "peak",
        data_type_dic["flat_type_id"]: "flat",
        data_type_dic["normal_type_id"]: "normal",
        data_type_dic["valley_type_id"]: "valley",
        data_type_dic["low_type_id"]: "low"
    }

    # 一次性检索所有相关记录
    all_rows = session.execute(select(TradeEPDataMonth).where(
        and_(
            TradeEPDataMonth.region_id == region_id,
            TradeEPDataMonth.data_time <= data_time,
            TradeEPDataMonth.data_type_id.in_(type_id_to_price_type.keys())
        )
    ).order_by(TradeEPDataMonth.data_time.desc())).scalars().all()

    # 使用字典缓存查询结果
    latest_data_dict = {type_id: None for type_id in type_id_to_price_type.keys()}
    for row in all_rows:
        price_type = type_id_to_price_type.get(row.data_type_id)
        if price_type and (row.data_time == data_time or latest_data_dict[row.data_type_id] is None):
            trade_ep_dic[price_type] = "{:.4f}".format(float(row.data_value)) if row.data_value is not None else None
            latest_data_dict[row.data_type_id] = row.data_value

    # 填充没有当前数据时间值的类型
    for type_id, price_type in type_id_to_price_type.items():
        if trade_ep_dic[price_type] is None and latest_data_dict[type_id] is not None:
            trade_ep_dic[price_type] = "{:.4f}".format(float(latest_data_dict[type_id]))
    return trade_ep_dic


def get_trade_result_data(region_id, data_type_dic, data_time):
    with Session() as session:
        set_time_data = get_trade_data_for_time(session, region_id, data_type_dic, data_time)
        return set_time_data


def check_voltage_levels(data_ids_voltage_levels):
    """
    检查电压等级对应的当月平段价格数据是否存在，去除没有当月平段价格数据的电压等级
    """
    existing_voltage_levels = []
    set_time = get_now_time()
    with Session() as session:
        for _, row in data_ids_voltage_levels.iterrows():
            exists = session.query(TradeEPDataMonth).filter(
                TradeEPDataMonth.data_type_id == row['data_type_id'],
                TradeEPDataMonth.data_time == set_time
            ).first() is not None

            if exists:
                existing_voltage_levels.append(row['voltage_level'])
        return existing_voltage_levels
