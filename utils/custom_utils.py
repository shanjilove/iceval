import numpy_financial as npf

from _decimal import Decimal


def check_compute_number(keys, is_show_year=False):
    if is_show_year:
        return f'{keys}年'
    return round(keys / 10000, 2)


def check_num_cs(num):
    """
    判断是否大于1000万。大于1000万，返回取整数万元，否则返回保留两位小数万元
    params: num: 金额
    return: 金额
    """
    if num is None:
        return 0
    if isinstance(num, str):
        num = float(num)
    return Decimal(str(num / 10000)).quantize(Decimal("1."), rounding="ROUND_HALF_UP")


def check_thousand(num):
    return f"{round(num):,}"


def get_np_data(compute_datas, project_total):
    """
    计算IRR和NPV
    """
    np_lis = [data["project_revenue"] for data in compute_datas]
    np_lis.insert(0, -project_total)  # 在第一个位置插入负的项目总收入
    np_data = npf.irr(np_lis)
    irr_data = round(np_data * 100, 2)
    discount_rate = 0.03  # 折现率
    npv_data = npf.npv(discount_rate, np_lis)
    return irr_data, npv_data


def is_have_money(region_name):
    """
    判断是否适合做储能
    """
    have_money_lis = ["浙江", "上海", "江苏", "陕西", "河南", "黑龙江", "湖南", "吉林", "山东", "安徽", "四川", "贵州",
                      "广东", "湖北", "海南"]
    for have_money in have_money_lis:
        if have_money in region_name:
            return True
    return False


def generate_points_data(status_list, price_dic, interval):
    """
    生成图表数据, status_list: 状态列表, price_dic: 电价字典, interval: 时间间隔
    params: status_list: 状态列表
    params: price_dic: 电价字典
    params: interval: 时间间隔
    params: 30min: 24 * 2
    params: 60min: 24 * 1
    return: 图表数据
    """
    points_data = {}
    status_mapping = {"4": "peak", "3": "flat", "2": "normal", "1": "low", "0": "valley"}

    total_points = 24 * (2 if interval == '30min' else 1)

    for i in range(total_points):
        hour = i // (2 if interval == '30min' else 1)
        minute = "30" if interval == '30min' and i % 2 != 0 else "00"
        key = f"{hour:02d}:{minute}"
        status_code = str(status_list[i])
        status = status_mapping.get(status_code, "unknown")

        price = price_dic.get(status)
        if price is None or price == "--":
            price_value = "--"
        else:
            try:
                price_value = float(price)
            except ValueError:
                price_value = "--"  # 如果无法转换为浮点数，使用默认值

        points_data[key] = {"status": status_code, "price": price_value}
    last_hour_key = "23:00" if interval == '60min' else "23:30"
    points_data["24:00"] = points_data.get(last_hour_key, {"status": "unknown", "price": "--"})
    return points_data


def generate_time_intervals(start_time, end_time, price, status, interval='30min'):
    """
    生成时间区间数据
    param : start_time: 开始时间
    param : end_time: 结束时间
    param : price: 电价
    param : status: 状态
    param : interval: 时间间隔
    return: 时间区间数据
    """
    from datetime import datetime, timedelta
    result = {}
    start_time_dt = datetime.strptime(start_time, '%H:%M')
    end_time_dt = datetime.strptime(end_time, '%H:%M')

    if start_time_dt > end_time_dt:
        end_time_dt += timedelta(days=1)

    interval_delta = timedelta(minutes=30) if interval == '30min' else timedelta(hours=1)
    current_time = start_time_dt

    while current_time != end_time_dt:
        time_str = current_time.strftime('%H:%M')
        result[time_str] = {"price": price, "status": status}
        current_time += interval_delta
    return result
