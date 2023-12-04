import copy
from _decimal import Decimal

from service.iceval.dianchacha_db_api import get_trade_result_data, check_voltage_levels
from service.iceval.iceval_db_api import get_electric_dic_for_region, get_cooperate_type, \
    get_user_charge_discharge_days, add_compute_energy_storage, get_calculation_install_info, \
    get_compute_info, add_benefit_evaluation_info, get_electric_grade_dic_for_region, get_electricity_type_dic
from utils.custom_utils import check_num_cs, check_compute_number, get_np_data, \
    generate_time_intervals, generate_points_data, check_thousand
from utils.file_utils import get_voltage_level_lis, get_region_ele_prices, get_electricity_dic, get_energy_storage_dic
from utils.time_utils import get_month_time, get_hours_num, extract_whole_hours_inclusive


def get_electricity_data(region_id, region_name):
    electric_dict = get_electric_dic_for_region(region_id, region_name)
    return electric_dict


def get_electricity_type_data(region_id, region_name, electricity_type):
    electric_dict = get_electricity_type_dic(region_id, region_name, electricity_type)
    return electric_dict


def get_electricity_grade_data(region_id, region_name, electric_type, electric_price_type):
    """
    获取所有对应的平时段电价ID，判断是否有数据, 有数据返回电压等级，没有数据返回空列表
    db: 电查查  table: trade_op_mon
    param: region_id: 省份ID
    param: region_name: 省份名称
    param: electric_type: 用电类型
    param: electric_price_type: 计价方式
    param: data_type_id: 电价类型ID
    """
    region_mapping = {
        '上海市': '上海和浙江',
        '浙江省': '上海和浙江',
        '河北省（冀北）': '冀北',
        '河北省（冀南）': '冀南',
        '内蒙古（蒙东）': '蒙东',
        '内蒙古（蒙西）': '蒙西',
    }
    specific_voltages = {"10千伏", "1-10千伏", "1-10（20）千伏"}
    target_region = region_mapping.get(region_name, '除冀南冀北蒙东蒙西上海浙江之外')

    electric_grade_data = get_electric_grade_dic_for_region(region_id, region_name, electric_type, electric_price_type)
    if not electric_grade_data:
        return {"electric_grade": []}
    data_ids_voltage_levels = get_voltage_level_lis(region_name, target_region, electric_type, electric_price_type,
                                                    electric_grade_data)
    voltage_dic = check_voltage_levels(data_ids_voltage_levels)
    specific_voltages_in_list = [v for v in voltage_dic if v in specific_voltages]
    other_voltages = [v for v in voltage_dic if v not in specific_voltages]

    return {"electric_grade": specific_voltages_in_list + other_voltages }


def get_calculate_installed_capacity(user_id):
    """
    计算装机台数
    """
    ele_prices, charge_time_dic = get_region_ele_prices_for_dic(user_id)
    power_time_dic = {}
    electricity_info_dic = get_calculation_install_info(user_id)
    discharge_depth = 0.96  # 放电深度
    charge_discharge_efficiency = 0.93  # 充放电效率
    discharge_days = int(get_user_charge_discharge_days(user_id))  # 年运行天数
    year_operation_days = discharge_days  # 年运行天数
    electricity_info = get_calculation_install_info(user_id)
    charge_discharge_times = electricity_info.tariff_data.get("charge_discharge_times", 2)
    battery_attenuation_rate = round(0.2 * (year_operation_days * charge_discharge_times / 6000), 4)  # 电池衰减率
    max_fluctuation_range = electricity_info_dic.max_fluctuation_range
    min_fluctuation_range = electricity_info_dic.min_fluctuation_range
    basic_battery_type = electricity_info_dic.basic_battery_type
    power_curve_type = electricity_info_dic.power_curve_type
    first_charge_time = charge_time_dic.get("first_charge_time", [])
    first_discharging_time = charge_time_dic.get("first_discharge_time", [])
    second_charge_time = charge_time_dic.get("second_charge_time", [])
    second_discharging_time = charge_time_dic.get("second_discharge_time", [])
    every_time_data = get_energy_storage_dic(power_curve_type)
    if basic_battery_type == "capacity_charge":
        max_power = electricity_info_dic.transformers
    else:
        max_power = electricity_info_dic.max_demand
    for key, value in every_time_data.items():
        every_power = min_fluctuation_range + (max_fluctuation_range - min_fluctuation_range) * value
        power_time_dic[key] = float(every_power)
    l1_k = get_hours_num(first_charge_time) * max_power
    first_charge_time_lis = extract_whole_hours_inclusive(first_charge_time)
    first_discharging_time_lis = extract_whole_hours_inclusive(first_discharging_time)
    second_charge_time_lis = extract_whole_hours_inclusive(second_charge_time)
    second_discharging_time_lis = extract_whole_hours_inclusive(second_discharging_time)
    if second_charge_time == [] and second_discharging_time == []:
        l1 = l1_k - sum([power_time_dic[i] for i in first_charge_time_lis])
        l2 = 9999999999
        l3 = sum([power_time_dic[i] for i in first_discharging_time_lis])
        l4 = 9999999999
    else:
        l2_k = get_hours_num(second_charge_time) * max_power
        l1 = l1_k - sum([power_time_dic[i] for i in first_charge_time_lis])
        l2 = l2_k - sum([power_time_dic[i] for i in second_charge_time_lis])
        l3 = sum([power_time_dic[i] for i in first_discharging_time_lis])
        l4 = sum([power_time_dic[i] for i in second_discharging_time_lis])
    l0 = min(l1, l2, l3, l4)
    return 0 if int(l0 / 233) < 0 else int(l0 / 233)  # 计算装机台数


def get_energy_storage_discharging_info(user_id, is_show=False):
    """
    获取储能放电信息, is_show为True时，返回的数据为前端展示数据，否则为计算数据
    """
    electricity_info = get_calculation_install_info(user_id)
    charge_discharge_times = electricity_info.tariff_data.get("charge_discharge_times", 0)
    installed_units_num = get_calculate_installed_capacity(user_id)
    installed_units_nums = f'{installed_units_num}（台）' if is_show else installed_units_num  # 选配台数
    battery_capacity = '100kw / 233kwh' if is_show else 233  # 储能系统电池容量
    installed_capacity = f'{check_thousand(100 * int(installed_units_num))}kw / {check_thousand(233 * int(installed_units_num))}kwh'  # 装机规模
    discharge_depth = '96%' if is_show else 0.96  # 放电深度
    charge_discharge_efficiency = '93%' if is_show else 0.93  # 充放电效率
    operation_duration = '15年' if is_show else 15
    cooperate_type, user_share_ratio = get_cooperate_type(user_id)
    user_share_ratio_v = f'{round(user_share_ratio) * 100}%' if is_show else user_share_ratio
    project_total = round((233 * float(installed_units_num) * 1350), 2)  # 项目总投资
    user_input = f'{0 if cooperate_type == "EMC" else check_thousand(project_total)}万元' if is_show else \
        (0 if cooperate_type == "EMC" else project_total)  # 用户投入
    energy_storage_discharging_info = {"user_id": user_id, "battery_capacity": battery_capacity,
                                       "charge_discharge_times": charge_discharge_times,
                                       "status": "active", "installed_capacity": installed_capacity,
                                       "user_share_ratio": user_share_ratio_v,
                                       "installed_units_num": installed_units_nums,
                                       "discharge_depth": discharge_depth,
                                       "charge_discharge_efficiency": charge_discharge_efficiency,
                                       "user_input": user_input, "operation_duration": operation_duration,
                                       "cooperate_type": cooperate_type, "project_total": project_total
                                       }

    return energy_storage_discharging_info


def get_strategy_info(user_id):
    electricity_info = get_calculation_install_info(user_id)
    if not electricity_info:
        return []
    region_id = electricity_info.region_id
    region_name = electricity_info.region_name
    electric_type = electricity_info.electric_type
    electric_price_type = electricity_info.electric_price_type
    voltage_level = electricity_info.voltage_level
    traffic_data = get_trade_ep_data_month_data(region_id, region_name, electric_type, electric_price_type,
                                                voltage_level)
    strategy_data = traffic_data.get("strategy", {})
    charge_discharge_times = traffic_data.get("charge_discharge_times", 0)
    charge_discharge_mode = [f'{charge_discharge_times}充{charge_discharge_times}放']
    if region_name == "安徽省":
        charge_discharge_mode = ['1充1放（7,8月）', '2充2放（其余月份）']
    data = {
        "strategy_data": strategy_data,
        "charge_discharge_mode": charge_discharge_mode
    }
    return data


def get_investor_cost_recovery_period(i, bo_project_revenue_total, project_total, bo_project_revenue_total_1,
                                      project_revenue):
    if bo_project_revenue_total > project_total and bo_project_revenue_total_1 < 0:
        num = i - 1 + (bo_project_revenue_total - project_total) / project_revenue
        return Decimal(num).quantize(Decimal("0.0"))
    return 0


def check_compute_energy_data(data):
    check_lis = []
    for compute_energy_storage_dic in data:
        check_lis.append({
            "construction_cost": check_compute_number(compute_energy_storage_dic['construction_cost']),  # 第i年建设成本
            "project_revenue": check_num_cs(compute_energy_storage_dic['project_revenue']),  # 第i年项目收益
            "user_project_revenue": check_compute_number(compute_energy_storage_dic['user_project_revenue']),
            "bo_project_revenue": check_compute_number(compute_energy_storage_dic['bo_project_revenue']),
            "year_initial_effective_capacity": check_compute_number(
                compute_energy_storage_dic['year_initial_effective_capacity']),
            "year_discharge_capacity": check_num_cs(compute_energy_storage_dic['year_discharge_capacity']),
            "year_charge_capacity": check_num_cs(compute_energy_storage_dic['year_charge_capacity']),
            "accumulate_revenue": check_num_cs(compute_energy_storage_dic['accumulate_revenue']),
            "bo_accumulate_revenue": check_compute_number(compute_energy_storage_dic['bo_accumulate_revenue'])
        })
    return check_lis


def check_p_data(p1, p2, p3, p4, price_dic):
    return {
        "P1": round(price_dic.get(p1, 0), 2),
        "P2": round(price_dic.get(p2, 0), 2),
        "P3": round(price_dic.get(p3, 0), 2) if p3 != "0" else 0,
        "P4": round(price_dic.get(p4, 0), 2) if p4 != "0" else 0,
    }


def get_region_ele_prices_for_dic(user_id):
    """
    获取可做储能省份充放电时段对应的 电价等级数据
    """
    months = {}
    electricity_info = get_calculation_install_info(user_id)
    region_name = electricity_info.region_name
    electric_type = electricity_info.electric_type
    voltage_level = electricity_info.voltage_level
    electric_price_type = electricity_info.electric_price_type
    electricity_type_str = electric_price_type + electric_type

    if '浙江' in region_name:
        price_dic = get_region_ele_prices(region_name, electricity_type_str, voltage_level)
        charge_time_dic = {
            "first_charge_time": ["00:00", "08:00"],
            "first_discharge_time": ["08:00", "12:00"],
            "second_charge_time": ["11:00", "13:00"],
            "second_discharge_time": ["13:00", "22:00"],
        }
        if electric_type == "一般工商业":
            for month in range(1, 13):
                months[str(month)] = check_p_data("low", "flat", "low", "peak", price_dic)
        else:
            for month in range(1, 13):
                months[str(month)] = check_p_data("low", "peak", "low", "peak", price_dic)
        return months, charge_time_dic

    if '上海' in region_name:
        charge_time_dic = {
            "first_charge_time": ["22:00", "06:00"],
            "first_discharge_time": ["08:00", "15:00"],
            "second_charge_time": ["15:00", "18:00"],
            "second_discharge_time": ["18:00", "22:00"],
        }
        price_dic = get_region_ele_prices(region_name, electricity_type_str, voltage_level)
        if electric_price_type == "单一制":
            if electric_type == "一般工商业":
                for month in range(1, 13):
                    months[str(month)] = check_p_data("low", "flat", "0", "0", price_dic)

        else:
            for month in range(1, 13):
                if month in [7, 8]:
                    months[str(month)] = check_p_data("low", "peak", "normal", "flat", price_dic)
                if month in [9]:
                    months[str(month)] = check_p_data("low", "flat", "normal", "flat", price_dic)
                if month in [1, 12]:
                    months[str(month)] = check_p_data("low", "flat", "normal", "peak", price_dic)
                if month in [2, 3, 4, 5, 6, 10, 11]:
                    months[str(month)] = check_p_data("low", "flat", "normal", "flat", price_dic)
        return months, charge_time_dic

    if '北京' in region_name:
        price_dic = get_region_ele_prices(region_name, electric_price_type, voltage_level)
        charge_time_dic = {
            "first_charge_time": ["23:00", "07:00"],
            "first_discharge_time": ["10:00", "13:00"],
            "second_charge_time": ["13:00", "16:00"],
            "second_discharge_time": ["16:00", "22:00"],
        }
        for month in range(1, 13):
            if month in [7, 8]:
                months[str(month)] = check_p_data("low", "peak", "normal", "peak", price_dic)
            if month in [1, 12]:
                months[str(month)] = check_p_data("low", "flat", "normal", "peak", price_dic)
            if month in [2, 3, 4, 5, 6, 10, 11]:
                months[str(month)] = check_p_data("low", "flat", "normal", "flat", price_dic)
        return months, charge_time_dic

    if '江苏' in region_name:
        price_dic = get_region_ele_prices(region_name, electric_price_type, voltage_level)
        charge_time_dic = {
            "first_charge_time": ["00:00", "08:00"],
            "first_discharge_time": ["08:00", "11:00"],
            "second_charge_time": ["11:00", "17:00"],
            "second_discharge_time": ["17:00", "19:00"],
        }
        for month in range(1, 13):
            months[str(month)] = check_p_data("low", "flat", "normal", "flat", price_dic)
        return months, charge_time_dic

    if '山东' in region_name:
        price_dic = get_region_ele_prices(region_name, electric_price_type, voltage_level)
        charge_time_dic = {
            "first_charge_time": ["10:00", "16:00"],
            "first_discharge_time": ["16:00", "12:00"],
            "second_charge_time": ["10:00", "16:00"],
            "second_discharge_time": ["16:00", "12:00"],
        }
        for month in range(1, 13):
            months[str(month)] = check_p_data("valley", "peak", "0", "0", price_dic)

        return months, charge_time_dic

    if '陕西' in region_name:
        price_dic = get_region_ele_prices(region_name, electric_price_type, voltage_level)
        charge_time_dic = {
            "first_charge_time": ["23:00", "08:00"],
            "first_discharge_time": ["08:00", "12:00"],
            "second_charge_time": ["12:00", "19:00"],
            "second_discharge_time": ["19:00", "23:00"],
        }
        for month in range(1, 13):
            if month in [7, 8]:
                months[str(month)] = check_p_data("low", "flat", "normal", "peak", price_dic)
            if month in [1, 12]:
                months[str(month)] = check_p_data("low", "flat", "normal", "flat", price_dic)
            if month in [2, 3, 4, 5, 6, 10, 11]:
                months[str(month)] = check_p_data("low", "flat", "normal", "peak", price_dic)
        return months, charge_time_dic

    if '黑龙江' in region_name:
        price_dic = get_region_ele_prices(region_name, electric_price_type, voltage_level)
        charge_time_dic = {
            "first_charge_time": ["23:00", "08:00"],
            "first_discharge_time": ["08:00", "12:00"],
            "second_charge_time": ["12:00", "19:00"],
            "second_discharge_time": ["19:00", "23:00"],
        }
        for month in range(1, 13):
            if month in [1, 7, 8, 9, 11, 12]:
                months[str(month)] = check_p_data("low", "flat", "normal", "peak", price_dic)
            if month in [2, 3, 4, 5, 6, 10]:
                months[str(month)] = check_p_data("low", "flat", "normal", "flat", price_dic)
        return months, charge_time_dic

    if '吉林' in region_name:
        price_dic = get_region_ele_prices(region_name, electric_price_type, voltage_level)
        charge_time_dic = {
            "first_charge_time": ["23:00", "06:00"],
            "first_discharge_time": ["09:00", "12:00"],
            "second_charge_time": ["12:00", "16:00"],
            "second_discharge_time": ["16:00", "21:00"],
        }
        for month in range(1, 13):
            if month in [1, 2, 7, 8, 11, 12]:
                months[str(month)] = check_p_data("low", "flat", "normal", "peak", price_dic)
            if month in [3, 4, 5, 6, 9, 10]:
                months[str(month)] = check_p_data("low", "flat", "normal", "flat", price_dic)
        return months, charge_time_dic

    if '河南' in region_name:
        price_dic = get_region_ele_prices(region_name, electric_price_type, voltage_level)
        charge_time_dic = {
            "first_charge_time": ["00:00", "07:00"],
            "first_discharge_time": ["10:00", "14:00"],
            "second_charge_time": ["14:00", "17:00"],
            "second_discharge_time": ["17:00", "21:00"],
        }
        for month in range(1, 13):
            if month in [1, 12]:
                months[str(month)] = check_p_data("low", "flat", "normal", "peak", price_dic)
            if month in [7, 8]:
                months[str(month)] = check_p_data("low", "peak", "normal", "flat", price_dic)
            if month in [2, 3, 4, 5, 6, 9, 10, 11]:
                months[str(month)] = check_p_data("low", "flat", "normal", "flat", price_dic)
        return months, charge_time_dic

    if '湖南' in region_name:
        price_dic = get_region_ele_prices(region_name, electric_price_type, voltage_level)
        charge_time_dic = {
            "first_charge_time": ["23:00", "07:00"],
            "first_discharge_time": ["11:00", "14:00"],
            "second_charge_time": ["14:00", "18:00"],
            "second_discharge_time": ["18:00", "23:00"],
        }
        for month in range(1, 13):
            if month in [1, 7, 8, 9, 12]:
                months[str(month)] = check_p_data("low", "flat", "normal", "peak", price_dic)
            if month in [2, 3, 4, 5, 6, 10, 11]:
                months[str(month)] = check_p_data("low", "peak", "normal", "flat", price_dic)
        return months, charge_time_dic

    if '安徽' in region_name:
        price_dic = get_region_ele_prices(region_name, electric_price_type, voltage_level)
        charge_time_dic = {
            "first_charge_time": ["23:00", "08:00"],
            "first_discharge_time": ["09:00", "12:00"],
            "second_charge_time": ["12:00", "17:00"],
            "second_discharge_time": ["17:00", "22:00"],
        }
        for month in range(1, 13):
            if month in [7, 8]:
                months[str(month)] = check_p_data("low", "flat", "0", "0", price_dic)
            if month in [1, 2, 3, 4, 5, 6, 9, 10, 11, 12]:
                months[str(month)] = check_p_data("low", "peak", "normal", "flat", price_dic)
        return months, charge_time_dic

    if '四川' in region_name:
        price_dic = get_region_ele_prices(region_name, electric_price_type, voltage_level)
        charge_time_dic = {
            "first_charge_time": ["23:00", "07:00"],
            "first_discharge_time": ["10:00", "12:00"],
            "second_charge_time": ["12:00", "15:00"],
            "second_discharge_time": ["15:00", "21:00"],
        }
        for month in range(1, 13):
            if month in [7, 8]:
                months[str(month)] = check_p_data("low", "flat", "normal", "peak", price_dic)
            if month in [1, 12]:
                months[str(month)] = check_p_data("low", "flat", "normal", "peak", price_dic)
            if month in [2, 3, 4, 5, 6, 9, 10, 11]:
                months[str(month)] = check_p_data("low", "flat", "normal", "flat", price_dic)
        return months, charge_time_dic

    if '贵州' in region_name:
        price_dic = get_region_ele_prices(region_name, electric_price_type, voltage_level)
        charge_time_dic = {
            "first_charge_time": ["23:00", "07:00"],
            "first_discharge_time": ["09:00", "12:00"],
            "second_charge_time": ["12:00", "16:00"],
            "second_discharge_time": ["16:00", "21:00"],
        }
        for month in range(1, 13):
            months[str(month)] = check_p_data("low", "flat", "normal", "flat", price_dic)
        return months, charge_time_dic

    if '广东' in region_name:
        price_dic = get_region_ele_prices(region_name, electric_price_type, voltage_level)
        charge_time_dic = {
            "first_charge_time": ["00:00", "08:00"],
            "first_discharge_time": ["10:00", "12:00"],
            "second_charge_time": ["14:00", "19:00"],
            "second_discharge_time": ["19:00", "00:00"],
        }
        for month in range(1, 13):
            if month in [7, 8, 9]:
                months[str(month)] = check_p_data("low", "flat", "normal", "flat", price_dic)
            if month in [1, 2, 3, 4, 5, 6, 10, 11, 12]:
                months[str(month)] = check_p_data("low", "peak", "normal", "peak", price_dic)
        return months, charge_time_dic

    if '湖北' in region_name:
        price_dic = get_region_ele_prices(region_name, electric_price_type, voltage_level)
        charge_time_dic = {
            "first_charge_time": ["23:00", "07:00"],
            "first_discharge_time": ["09:00", "15:00"],
            "second_charge_time": ["15:00", "20:00"],
            "second_discharge_time": ["17:00", "20:00"],
        }
        for month in range(1, 13):
            months[str(month)] = check_p_data("low", "flat", "normal", "peak", price_dic)
        return months, charge_time_dic

    if '海南' in region_name:
        price_dic = get_region_ele_prices(region_name, electric_price_type, voltage_level)
        charge_time_dic = {
            "first_charge_time": ["23:00", "07:00"],
            "first_discharge_time": ["10:00", "12:00"],
            "second_charge_time": ["12:00", "16:00"],
            "second_discharge_time": ["16:00", "22:00"],
        }
        for month in range(1, 13):
            if month in [5, 6, 7]:
                months[str(month)] = check_p_data("low", "flat", "normal", "flat", price_dic)
            if month in [1, 2, 3, 4, 8, 9, 10, 11, 12]:
                months[str(month)] = check_p_data("low", "flat", "normal", "flat", price_dic)
        return months, charge_time_dic


def set_compute_energy_storage_info(user_id):
    """
    计算储能放收益信息，项目累计收益，项目充放电量，用户累计收益，用户充放电量
    params: user_id 用户id
    return: 收益信息data
    """
    all_compute_energy_storage_lis = []
    energy_benefit_lis = []
    ele_prices, charge_time_dic = get_region_ele_prices_for_dic(user_id)
    ele_prices_dic = ele_prices.get("1", {})
    # 计算参数
    energy_storage_discharging_info = get_energy_storage_discharging_info(user_id, is_show=False)
    charge_discharge_times = energy_storage_discharging_info.get("charge_discharge_times", 0)  # 充放电次数
    battery_capacity = energy_storage_discharging_info.get("battery_capacity", 0)  # 储能系统电池容量
    installed_units_num = int(energy_storage_discharging_info.get("installed_units_num", 0))  # 选配台数
    discharge_depth = energy_storage_discharging_info.get("discharge_depth", 0)  # 放电深度
    charge_discharge_efficiency = energy_storage_discharging_info.get("charge_discharge_efficiency", 0)  # 充放电效率
    operation_duration = energy_storage_discharging_info.get("operation_duration", 0)  # 运行期限
    user_share_ratio = energy_storage_discharging_info.get("user_share_ratio", 0)  # 用户分成比例
    cooperate_type = energy_storage_discharging_info.get("cooperate_type", 0)  # 合作类型
    project_total = energy_storage_discharging_info.get("project_total", 0)  # 项目总投资
    user_input = energy_storage_discharging_info.get("user_input", 0)  # 用户投入

    unit_construction_cost = 1350  # 单位建设成本
    discharge_days = int(get_user_charge_discharge_days(user_id))  # 年运行天数
    year_operation_days = discharge_days  # 年运行天数
    month_operation_days = round(discharge_days / 12, 2)  # 月运行天数
    battery_attenuation_rate = round(0.2 * (year_operation_days * charge_discharge_times / 6000), 2)  # 电池衰减率
    between_three_years = round(unit_construction_cost * 0.004, 2)  # 前三年单位运维成本
    three_years_before = round(unit_construction_cost * 0.015, 2)  # 三年后单位运维成本
    single_discharge = round(battery_capacity * discharge_depth * charge_discharge_efficiency, 2)  # 单台设备单次放电量
    single_charge = round(battery_capacity * discharge_depth / charge_discharge_efficiency, 2)  # 单台设备单次充电量

    accumulate_revenue = 0
    bo_accumulate_revenue = 0
    bo_project_revenue_total = 0
    user_project_revenue_total = 0

    for i in range(1, operation_duration + 1):
        compute_energy_storage_dic = {}
        p1 = ele_prices_dic.get("P1", 0)
        p2 = ele_prices_dic.get("P2", 0)
        p3 = ele_prices_dic.get("P3", 0)
        p4 = ele_prices_dic.get("P4", 0)

        yearly_earnings = (sum([(single_discharge * (1 - i * battery_attenuation_rate) * (
                p2 + p4) - single_charge * (1 - i * battery_attenuation_rate) * (
                                         p1 + p3)) * month_operation_days for _ in range(12)])) * installed_units_num

        construction_cost = battery_capacity * installed_units_num * three_years_before if i > 3 else battery_capacity \
                                                                                                      * installed_units_num * between_three_years
        compute_energy_storage_dic['construction_cost'] = construction_cost  # 第i年运维成本
        project_revenue = yearly_earnings - construction_cost  # 第i年项目总收益
        user_project_revenue = yearly_earnings * user_share_ratio if cooperate_type == 'EMC' else project_revenue  # 第i年项目用户总收益
        bo_project_revenue = project_revenue - user_project_revenue  # 第i年项目投资人总收益
        compute_energy_storage_dic['project_revenue'] = project_revenue
        compute_energy_storage_dic['user_project_revenue'] = user_project_revenue
        compute_energy_storage_dic['bo_project_revenue'] = bo_project_revenue
        compute_energy_storage_dic['year_initial_effective_capacity'] = battery_capacity * \
                                                                        (1 - i * battery_attenuation_rate)  # 年初有效容量
        compute_energy_storage_dic['year_discharge_capacity'] = installed_units_num * single_discharge * (
                1 - i * battery_attenuation_rate) * charge_discharge_times * year_operation_days  # 年放电容量
        compute_energy_storage_dic['year_charge_capacity'] = installed_units_num * single_charge * (
                1 - i * battery_attenuation_rate) * charge_discharge_times * year_operation_days  # 年充电量
        accumulate_revenue += project_revenue  # 项目累计总收益)
        bo_accumulate_revenue += bo_project_revenue  # 投资人项目累计总收益
        user_project_revenue_total += user_project_revenue  # 用户项目累计总收益
        bo_project_revenue_total += bo_project_revenue  # 投资人项目总收益
        compute_energy_storage_dic['accumulate_revenue'] = accumulate_revenue
        compute_energy_storage_dic['bo_accumulate_revenue'] = bo_accumulate_revenue
        energy_benefit_lis.append({"year": i,
                                   "project_total": check_compute_number(project_total),
                                   "user_input": check_compute_number(user_input),
                                   "accumulate_revenue": check_compute_number(accumulate_revenue),
                                   "user_project_revenue_total": check_compute_number(user_project_revenue_total)})
        all_compute_energy_storage_lis.append(compute_energy_storage_dic)

    compute_energy_storage_info = {"unit_construction_cost": unit_construction_cost,
                                   "year_operation_days": year_operation_days,
                                   "month_operation_days": month_operation_days,
                                   "battery_attenuation_rate": battery_attenuation_rate,
                                   "between_three_years": between_three_years,
                                   "three_years_before": three_years_before,
                                   "single_discharge": single_discharge,
                                   "single_charge": single_charge,
                                   "project_total": project_total,
                                   "user_input": user_input,
                                   "user_id": user_id,
                                   "status": "active",
                                   "all_compute_energy_storage": all_compute_energy_storage_lis,
                                   "user_project_revenue_total": user_project_revenue_total,
                                   "bo_project_revenue_total": bo_project_revenue_total,
                                   "energy_benefit_lis": energy_benefit_lis
                                   }

    add_compute_energy_storage(compute_energy_storage_info)
    return check_compute_energy_data(all_compute_energy_storage_lis)


def set_benefit_evaluation(user_id):
    """
    获取收益评估信息
    params: user_id 用户id
    return: 收益评估信息data
    """
    compute_data = get_compute_info(user_id)
    if not compute_data:
        return []
    cooperate_type, user_share_ratio = get_cooperate_type(user_id)
    compute_datas = compute_data["all_compute_energy_storage"]
    first_year_total_revenue = compute_datas[0].get('user_project_revenue', 0)
    project_revenue = compute_datas[0].get('project_revenue', 0)
    first_year_bo_total_revenue = float(project_revenue) - float(first_year_total_revenue)
    user_project_revenue_total = compute_data.get("user_project_revenue_total", 0)
    bo_accumulate_revenue = compute_data.get("bo_accumulate_revenue", 0)
    project_total = compute_data.get("project_total", 0)
    user_input = compute_data.get("user_input", 0)
    accumulate_revenue = compute_datas[-1]["accumulate_revenue"]
    project_internal_rate, project_npv = get_np_data(compute_datas, project_total)  # 项目内部收益率
    investor_cost_recovery_period = None

    for i, j in enumerate(compute_datas, 1):
        if cooperate_type == 'EMC':
            bo_accumulate_revenue = j["bo_accumulate_revenue"]
            bo_project_revenue_total_1 = j["bo_accumulate_revenue"] - j[
                "bo_project_revenue"] - project_total
            bo_project_revenue = j["bo_project_revenue"]

            investor_cost_recovery_period = get_investor_cost_recovery_period(i, bo_accumulate_revenue,
                                                                              project_total,
                                                                              bo_project_revenue_total_1,
                                                                              bo_project_revenue,
                                                                              )
        else:
            i_accumulate_revenue = j["accumulate_revenue"]
            project_revenue_total_1 = j["accumulate_revenue"] - j[
                "project_revenue"] - project_total
            user_project_revenue = j["user_project_revenue"]
            investor_cost_recovery_period = get_investor_cost_recovery_period(i, i_accumulate_revenue,
                                                                              project_total,
                                                                              project_revenue_total_1,
                                                                              user_project_revenue,
                                                                              )
        if investor_cost_recovery_period > 0:
            break

    benefit_evaluation_info = {
        "user_id": user_id,
        "status": "active",
        "first_year_total_revenue": check_compute_number(first_year_total_revenue),
        "first_year_bo_total_revenue": check_compute_number(first_year_bo_total_revenue),
        "investor_cost_recovery_period": check_compute_number(investor_cost_recovery_period, is_show_year=True),
        "project_internal_rate": f'{project_internal_rate}%',
        "user_project_revenue_total": check_compute_number(user_project_revenue_total),
        "bo_accumulate_revenue": check_compute_number(bo_accumulate_revenue),
        "project_total": check_compute_number(project_total),
        "user_input": check_compute_number(user_input),
        "accumulate_revenue": check_compute_number(accumulate_revenue),
        "project_npv": check_compute_number(project_npv)
    }

    add_benefit_evaluation_info(benefit_evaluation_info)

    return benefit_evaluation_info


def check_data_type(region_name, electric_type, electric_price_type, voltage_level):
    region_mapping = {
        '上海市': '上海和浙江',
        '浙江省': '上海和浙江',
        '河北省（冀北）': '冀北',
        '河北省（冀南）': '冀南',
        '内蒙古（蒙东）': '蒙东',
        '内蒙古（蒙西）': '蒙西',
    }

    target_region = region_mapping.get(region_name, '除冀南冀北蒙东蒙西上海浙江之外')
    electricity_str, data_type_dic = get_electricity_dic(region_name, target_region, electric_type, electric_price_type,
                                                         voltage_level)
    return electricity_str, data_type_dic


def generate_result_dict(*args):
    """
    生成首页树状图、表格数据
    :param args: 传入参数
    return: {
    "picture": {},
    "table": {}
    }
    """
    result_dict = {}
    picture_data = {}
    table_data = {}

    for i in range(0, len(args), 2):
        type_name = str(args[i])
        data = args[i + 1]
        picture_data[type_name] = data

        status_price_map = {"0": [], "1": [], "2": [], "3": [], "4": []}

        for timestamp, info in data.items():
            status = info.get('status')
            price = info.get('price')
            if status is not None and status in status_price_map:
                if price not in status_price_map[status]:
                    status_price_map[status].append(price)

        for status in status_price_map:
            if not status_price_map[status]:
                status_price_map[status] = "--"
            else:
                status_price_map[status] = ', '.join(map(str, status_price_map[status]))

        table_data[type_name] = status_price_map

    result_dict["picture"] = picture_data
    result_dict["table"] = table_data

    return result_dict


def update_strategy(ges, charge_discharge_times, **kwargs):
    """
    生成充放电策略数据
    :param ges: 储能系统信息
    return: {
        "picture": {},
        "strategy": {},
        "table": {},
        "charge_discharge_times": 2 充放电次数
    }
    """
    interval = '30min' if kwargs.get('is_48', False) else '60min'
    pic_data = ges.get("picture", {})
    strategy_data = ges.get("strategy", {})

    def update_data(type_key, charge_info, discharge_info):
        if charge_info is not None:
            strategy_data.setdefault(str(type_key), {}).update(
                generate_time_intervals(*charge_info, interval=interval))
        if discharge_info is not None:
            strategy_data.setdefault(str(type_key), {}).update(
                generate_time_intervals(*discharge_info, interval=interval))

    update_data(kwargs.get('first_type'), kwargs.get('f_first_charge_info'), kwargs.get('f_first_discharge_info'))
    update_data(kwargs.get('first_type'), kwargs.get('f_second_charge_info'), kwargs.get('f_second_discharge_info'))

    update_data(kwargs.get('second_type'), kwargs.get('s_first_charge_info'), kwargs.get('s_first_discharge_info'))
    update_data(kwargs.get('second_type'), kwargs.get('s_second_charge_info'), kwargs.get('s_second_discharge_info'))

    update_data(kwargs.get('three_type'), kwargs.get('t_first_charge_info'), kwargs.get('t_first_discharge_info'))
    update_data(kwargs.get('three_type'), kwargs.get('t_second_charge_info'), kwargs.get('t_second_discharge_info'))

    update_data(kwargs.get('four_type'), kwargs.get('r_first_charge_info'), kwargs.get('r_first_discharge_info'))
    update_data(kwargs.get('four_type'), kwargs.get('r_second_charge_info'), kwargs.get('r_second_discharge_info'))

    for key, time_data in pic_data.items():
        for time_key, value in time_data.items():
            strategy_data.setdefault(key, {}).setdefault(time_key, {'price': str(value['price']), 'status': '0'})
        strategy_data[key]["24:00"] = strategy_data[key]["23:00"]
    sorted_strategy_data = {k: dict(sorted(v.items())) for k, v in strategy_data.items()}
    ges['strategy'] = sorted_strategy_data
    ges['charge_discharge_times'] = charge_discharge_times
    # for ges_key, ges_value in ges.items():
    #     for key, value in ges_value.items():
    #
    #         modified_ges = {key.replace(', ', '/').replace('[', '').replace(']', ''): value}
    #         print(modified_ges)
    return modify_month_keys(ges)


def modify_month_keys(d):
    if isinstance(d, dict):
        return {k.replace(', ', '/').replace('[', '').replace(']', ''): modify_month_keys(v) for k, v in d.items()}
    return d


def get_trade_ep_data_month_data(region_id, region_name, electric_type, electric_price_type, voltage_level):
    """
    param: region_id
    param: region_name
    param: electric_type
    param: electric_price_type
    param: voltage_level
    peak 尖峰 flat 平段  normal 峰段 low 谷段 valley 深谷段 charge_status 充电状态 discharge_status
    放电状态 data_24_hours 24小时数据 data_48_hours 48小时数据
    """
    peak = 4
    flat = 3
    normal = 2
    low = 1
    valley = 0
    charge_status = '-1'
    discharge_status = '1'
    data_24_hours = "60min"
    data_48_hours = "30min"

    electricity_type_str, data_type_dic = check_data_type(region_name, electric_type, electric_price_type,
                                                          voltage_level)

    if '陕西' in region_name:
        charge_discharge_times = 2
        first_type = [7, 8]
        second_type = [1, 12]
        three_type = [2, 3, 4, 5, 6, 9, 10, 11]

        first_type_lis = [low] * 16 + [flat] * 7 + [normal] * 14 + [flat] * 2 + [peak] * 4 + [flat] * 3 + [low] * 2
        second_type_lis = [low] * 16 + [flat] * 7 + [normal] * 14 + [peak] * 4 + [flat] * 5 + [low] * 2
        three_type_lis = [low] * 16 + [flat] * 7 + [normal] * 14 + [flat] * 9 + [low] * 2

        first_set_time = get_month_time(first_type)
        second_set_time = get_month_time(second_type)
        three_set_time = get_month_time(three_type)

        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        second_dic = get_trade_result_data(region_id, data_type_dic, second_set_time)
        three_dic = get_trade_result_data(region_id, data_type_dic, three_set_time)
        first_data_48_points = generate_points_data(first_type_lis, first_dic, data_48_hours)
        second_data_48_points = generate_points_data(second_type_lis, second_dic, data_48_hours)
        three_data_48_points = generate_points_data(three_type_lis, three_dic, data_48_hours)

        ges = generate_result_dict(first_type, first_data_48_points, second_type, second_data_48_points,
                                   three_type, three_data_48_points)
        type_price = ges["table"]

        f_first_charge_info = ("23:00", "08:00", (type_price[str(first_type)].get("1", "--")), charge_status)
        f_first_discharge_info = ("08:00", "11:30", (type_price[str(first_type)].get("3", "--")), discharge_status)
        f_second_charge_info = ("11:30", "18:30", (type_price[str(first_type)].get("2", "--")), charge_status)
        f_second_discharge_info = ("18:30", "23:00", (type_price[str(first_type)].get("4", "--")), discharge_status)

        s_first_charge_info = ("23:00", "08:00", (type_price[str(second_type)].get("1", "--")), charge_status)
        s_first_discharge_info = ("08:00", "11:30", (type_price[str(second_type)].get("3", "--")), discharge_status)
        s_second_charge_info = ("11:30", "18:30", (type_price[str(second_type)].get("2", "--")), charge_status)
        s_second_discharge_info = ("18:30", "23:00", (type_price[str(second_type)].get("3", "--")), discharge_status)

        t_first_charge_info = ("23:00", "08:00", (type_price[str(three_type)].get("1", "--")), charge_status)
        t_first_discharge_info = ("08:00", "11:30", (type_price[str(three_type)].get("3", "--")), discharge_status)
        t_second_charge_info = ("11:30", "18:30", (type_price[str(three_type)].get("2", "--")), charge_status)
        t_second_discharge_info = ("18:30", "23:00", (type_price[str(three_type)].get("3", "--")), discharge_status)

        return update_strategy(ges, charge_discharge_times, first_type=first_type, second_type=second_type,
                               three_type=three_type,
                               four_type=None,
                               f_first_charge_info=f_first_charge_info, f_first_discharge_info=f_first_discharge_info,
                               f_second_charge_info=f_second_charge_info,
                               f_second_discharge_info=f_second_discharge_info,
                               s_first_charge_info=s_first_charge_info, s_first_discharge_info=s_first_discharge_info,
                               s_second_charge_info=s_second_charge_info,
                               s_second_discharge_info=s_second_discharge_info,
                               t_first_charge_info=t_first_charge_info, t_first_discharge_info=t_first_discharge_info,
                               t_second_charge_info=t_second_charge_info,
                               t_second_discharge_info=t_second_discharge_info,
                               r_first_charge_info=None, r_first_discharge_info=None,
                               r_second_charge_info=None, r_second_discharge_info=None,
                               is_48=True
                               )

    if region_name == '黑龙江省':
        charge_discharge_times = 2
        first_type = [1, 7, 8, 9, 11, 12]
        second_type = [2, 3, 4, 5, 6, 10]

        first_type_lis = [low] * 11 + [normal] * 1 + [flat] * 2 + [normal] * 4 + [flat] * 5 + [normal] * 8 + [
            flat] * 2 + [peak] * 4 + [flat] * 3 + [normal] * 5 + [low] * 3
        second_type_lis = [low] * 11 + [normal] * 1 + [flat] * 2 + [normal] * 4 + [flat] * 5 + [normal] * 8 + [
            flat] * 9 + [normal] * 5 + [low] * 3

        first_set_time = get_month_time(first_type)
        second_set_time = get_month_time(second_type)
        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        second_dic = get_trade_result_data(region_id, data_type_dic, second_set_time)
        first_data_48_points = generate_points_data(first_type_lis, first_dic, data_48_hours)
        second_data_48_points = generate_points_data(second_type_lis, second_dic, data_48_hours)

        ges = generate_result_dict(first_type, first_data_48_points, second_type, second_data_48_points)

        type_price = ges["table"]
        f_first_charge_info = ("22:30", "05:30", (type_price[str(first_type)]["1"]), charge_status)
        f_first_discharge_info = ("08:00", "11:30", (type_price[str(first_type)]["3"]), discharge_status)
        f_second_charge_info = ("11:30", "15:30", (type_price[str(first_type)]["2"]), charge_status)
        f_second_discharge_info = ("15:30", "20:00", (type_price[str(first_type)]["4"]), discharge_status)

        s_first_charge_info = ("22:30", "05:30", (type_price[str(second_type)]["1"]), charge_status)
        s_first_discharge_info = ("08:00", "11:30", (type_price[str(second_type)]["3"]), discharge_status)
        s_second_charge_info = ("11:30", "15:30", (type_price[str(second_type)]["2"]), charge_status)
        s_second_discharge_info = ("15:30", "20:00", (type_price[str(second_type)]["3"]), discharge_status)

        return update_strategy(ges, charge_discharge_times, first_type=first_type, second_type=second_type,
                               three_type=None,
                               four_type=None,
                               f_first_charge_info=f_first_charge_info, f_first_discharge_info=f_first_discharge_info,
                               f_second_charge_info=f_second_charge_info,
                               f_second_discharge_info=f_second_discharge_info,
                               s_first_charge_info=s_first_charge_info, s_first_discharge_info=s_first_discharge_info,
                               s_second_charge_info=s_second_charge_info,
                               s_second_discharge_info=s_second_discharge_info,
                               t_first_charge_info=None, t_first_discharge_info=None,
                               t_second_charge_info=None,
                               t_second_discharge_info=None,
                               r_first_charge_info=None, r_first_discharge_info=None,
                               r_second_charge_info=None, r_second_discharge_info=None,
                               is_48=True
                               )

    if '广东' in region_name:
        first_type = [1, 2, 3, 4, 5, 6, 10, 11, 12]
        second_type = [7, 8, 9]
        charge_discharge_times = 2
        first_type_lis = [low] * 8 + [normal] * 2 + [flat] * 2 + [normal] * 2 + [flat] * 5 + [normal] * 5
        second_type_lis = [low] * 8 + [normal] * 2 + [flat] * 1 + [peak] * 1 + [normal] * 2 + [flat] * 1 + [
            peak] * 2 + [flat] * 2 + [normal] * 5

        first_set_time = get_month_time(first_type)
        second_set_time = get_month_time(second_type)

        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        second_dic = get_trade_result_data(region_id, data_type_dic, second_set_time)
        first_data_48_points = generate_points_data(first_type_lis, first_dic, data_24_hours)
        second_data_48_points = generate_points_data(second_type_lis, second_dic, data_24_hours)

        ges = generate_result_dict(first_type, first_data_48_points, second_type, second_data_48_points)

        type_price = ges["table"]
        f_first_charge_info = ("00:00", "08:00", (type_price[str(first_type)]["1"]), charge_status)
        f_first_discharge_info = ("10:00", "12:00", (type_price[str(first_type)]["3"]), discharge_status)
        f_second_charge_info = ("12:00", "14:00", (type_price[str(first_type)]["2"]), charge_status)
        f_second_discharge_info = ("14:00", "19:00", (type_price[str(first_type)]["3"]), discharge_status)

        s_first_charge_info = ("00:00", "08:00", (type_price[str(second_type)]["1"]), charge_status)
        s_first_discharge_info = ("10:00", "12:00", (type_price[str(second_type)]["4"]), discharge_status)
        s_second_charge_info = ("12:00", "14:00", (type_price[str(second_type)]["2"]), charge_status)
        s_second_discharge_info = ("14:00", "19:00", (type_price[str(second_type)]["4"]), discharge_status)

        return update_strategy(ges, charge_discharge_times, first_type=first_type, second_type=second_type,
                               three_type=None,
                               four_type=None,
                               f_first_charge_info=f_first_charge_info, f_first_discharge_info=f_first_discharge_info,
                               f_second_charge_info=f_second_charge_info,
                               f_second_discharge_info=f_second_discharge_info,
                               s_first_charge_info=s_first_charge_info, s_first_discharge_info=s_first_discharge_info,
                               s_second_charge_info=s_second_charge_info,
                               s_second_discharge_info=s_second_discharge_info,
                               t_first_charge_info=None, t_first_discharge_info=None,
                               t_second_charge_info=None,
                               t_second_discharge_info=None,
                               r_first_charge_info=None, r_first_discharge_info=None,
                               r_second_charge_info=None, r_second_discharge_info=None,
                               )

    if region_name == '江苏省':
        charge_discharge_times = 2
        first_type = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        first_type_lis = [low] * 8 + [flat] * 3 + [normal] * 6 + [flat] * 5 + [normal] * 2

        first_set_time = get_month_time(first_type)
        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        first_data_48_points = generate_points_data(first_type_lis, first_dic, data_24_hours)

        ges = generate_result_dict(first_type, first_data_48_points)
        type_price = ges["table"]
        f_first_charge_info = ("00:00", "08:00", (type_price[str(first_type)]["1"]), charge_status)
        f_first_discharge_info = ("08:00", "11:00", (type_price[str(first_type)]["3"]), discharge_status)
        f_second_charge_info = ("11:00", "17:00", (type_price[str(first_type)]["2"]), charge_status)
        f_second_discharge_info = ("17:00", "22:00", (type_price[str(first_type)]["3"]), discharge_status)

        return update_strategy(ges, charge_discharge_times, first_type=first_type, second_type=None,
                               three_type=None,
                               four_type=None,
                               f_first_charge_info=f_first_charge_info, f_first_discharge_info=f_first_discharge_info,
                               f_second_charge_info=f_second_charge_info,
                               f_second_discharge_info=f_second_discharge_info,
                               s_first_charge_info=None, s_first_discharge_info=None,
                               s_second_charge_info=None,
                               s_second_discharge_info=None,
                               t_first_charge_info=None, t_first_discharge_info=None,
                               t_second_charge_info=None,
                               t_second_discharge_info=None,
                               r_first_charge_info=None, r_first_discharge_info=None,
                               r_second_charge_info=None, r_second_discharge_info=None,
                               )

    if region_name == '山东省':
        charge_discharge_times = 1
        first_type = [1, 12]
        second_type = [2, 3, 4, 5]
        three_type = [6, 7, 8]
        four_type = [9, 10, 11]

        first_type_lis = [normal] * 10 + [low] * 2 + [valley] * 2 + [low] * 2 + [peak] * 3 + [flat] * 3 + [normal] * 2
        second_type_lis = [normal] * 10 + [low] * 1 + [valley] * 3 + [low] * 1 + [normal] * 2 + [flat] * 1 + [
            peak] * 2 + [flat] * 2 + [normal] * 2
        three_type_lis = [normal] * 2 + [low] * 6 + [normal] * 8 + [flat] * 2 + [peak] * 4 + [normal] * 2
        four_type_lis = [normal] * 10 + [low] * 1 + [valley] * 3 + [low] * 1 + [normal] * 1 + [flat] * 1 + [
            peak] * 2 + [flat] * 2 + [normal] * 3

        first_set_time = get_month_time(first_type)
        second_set_time = get_month_time(second_type)
        three_set_time = get_month_time(three_type)
        four_set_time = get_month_time(four_type)

        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        second_dic = get_trade_result_data(region_id, data_type_dic, second_set_time)
        three_dic = get_trade_result_data(region_id, data_type_dic, three_set_time)
        four_dic = get_trade_result_data(region_id, data_type_dic, four_set_time)

        first_data_48_points = generate_points_data(first_type_lis, first_dic, data_24_hours)
        second_data_48_points = generate_points_data(second_type_lis, second_dic, data_24_hours)
        three_data_48_points = generate_points_data(three_type_lis, three_dic, data_24_hours)
        four_data_48_points = generate_points_data(four_type_lis, four_dic, data_24_hours)

        ges = generate_result_dict(first_type, first_data_48_points, second_type, second_data_48_points,
                                   three_type, three_data_48_points, four_type, four_data_48_points)

        type_price = ges["table"]
        f_first_charge_info = ("10:00", "16:00", (type_price[str(first_type)]["0"]), charge_status)
        f_first_discharge_info = ("16:00", "22:00", (type_price[str(first_type)]["4"]), discharge_status)

        s_first_charge_info = ("10:00", "15:00", (type_price[str(second_type)]["0"]), charge_status)
        s_first_discharge_info = ("17:00", "22:00", (type_price[str(second_type)]["4"]), discharge_status)

        t_first_charge_info = ("02:00", "08:00", (type_price[str(second_type)]["0"]), charge_status)
        t_first_discharge_info = ("16:00", "22:00", (type_price[str(second_type)]["4"]), discharge_status)

        r_first_charge_info = ("10:00", "15:00", (type_price[str(second_type)]["0"]), charge_status)
        r_first_discharge_info = ("16:00", "21:00", (type_price[str(second_type)]["4"]), discharge_status)

        return update_strategy(ges, charge_discharge_times, first_type=first_type, second_type=second_type,
                               three_type=three_type,
                               four_type=four_type,
                               f_first_charge_info=f_first_charge_info, f_first_discharge_info=f_first_discharge_info,
                               f_second_charge_info=None,
                               f_second_discharge_info=None,
                               s_first_charge_info=s_first_charge_info, s_first_discharge_info=s_first_discharge_info,
                               s_second_charge_info=None,
                               s_second_discharge_info=None,
                               t_first_charge_info=t_first_charge_info, t_first_discharge_info=t_first_discharge_info,
                               t_second_charge_info=None,
                               t_second_discharge_info=None,
                               r_first_charge_info=r_first_charge_info, r_first_discharge_info=r_first_discharge_info,
                               r_second_charge_info=None, r_second_discharge_info=None,
                               )

    if region_name == "山西省":
        if electric_price_type == "单一制":
            first_type = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
            first_type_lis = [low] * 7 + [normal] * 1 + [flat] * 3 + [low] * 2 + [normal] * 4 + [flat] * 6 + [
                normal] * 1

            first_set_time = get_month_time(first_type)
            first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
            first_data_48_points = generate_points_data(first_type_lis, first_dic, data_24_hours)

            return generate_result_dict(first_type, first_data_48_points)
        if electric_price_type == "两部制":
            first_type = [2, 3, 4, 5, 6, 9, 10, 11]
            second_type = [1, 7, 8, 12]

            first_type_lis = [low] * 7 + [normal] * 1 + [flat] * 3 + [low] * 2 + [normal] * 4 + [flat] * 6 + [
                normal] * 1
            second_type_lis = [low] * 7 + [normal] * 1 + [flat] * 3 + [low] * 2 + [normal] * 4 + [flat] * 1 + [peak] * 2 \
                              + [flat] * 3 + [normal] * 1

            first_set_time = get_month_time(first_type)
            second_set_time = get_month_time(second_type)

            first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
            second_dic = get_trade_result_data(region_id, data_type_dic, second_set_time)
            first_data_48_points = generate_points_data(first_type_lis, first_dic, data_24_hours)
            second_data_48_points = generate_points_data(second_type_lis, second_dic, data_24_hours)

            return generate_result_dict(first_type, first_data_48_points, second_type, second_data_48_points)

    if region_name == "浙江省":
        charge_discharge_times = 2
        if electric_type == "大工业":
            first_type = [1, 7, 8, 12]
            second_type = [2, 3, 4, 5, 6, 9, 10, 11]

            first_type_lis = [low] * 8 + [flat] * 1 + [peak] * 2 + [low] * 2 + [peak] * 4 + [flat] * 5 + [
                low] * 2
            second_type_lis = [low] * 8 + [flat] * 1 + [peak] * 2 + [low] * 2 + [flat] * 2 + [peak] * 2 + [flat] * 5 \
                              + [low] * 2

            first_set_time = get_month_time(first_type)
            second_set_time = get_month_time(second_type)

            first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
            second_dic = get_trade_result_data(region_id, data_type_dic, second_set_time)
            first_data_48_points = generate_points_data(first_type_lis, first_dic, data_24_hours)
            second_data_48_points = generate_points_data(second_type_lis, second_dic, data_24_hours)

            ges = generate_result_dict(first_type, first_data_48_points, second_type, second_data_48_points)

            type_price = ges["table"]
            f_first_charge_info = ("22:00", "08:00", (type_price[str(first_type)]["1"]), charge_status)
            f_first_discharge_info = ("08:00", "11:00", (type_price[str(first_type)]["4"]), discharge_status)
            f_second_charge_info = ("11:00", "13:00", (type_price[str(first_type)]["1"]), charge_status)
            f_second_discharge_info = ("13:00", "22:00", (type_price[str(first_type)]["4"]), discharge_status)

            s_first_charge_info = ("00:00", "08:00", (type_price[str(second_type)]["1"]), charge_status)
            s_first_discharge_info = ("08:00", "11:00", (type_price[str(second_type)]["4"]), discharge_status)
            s_second_charge_info = ("11:00", "13:00", (type_price[str(second_type)]["1"]), charge_status)
            s_second_discharge_info = ("13:00", "22:00", (type_price[str(second_type)]["4"]), discharge_status)

            return update_strategy(ges, charge_discharge_times, first_type=first_type, second_type=second_type,
                                   three_type=None,
                                   four_type=None,
                                   f_first_charge_info=f_first_charge_info,
                                   f_first_discharge_info=f_first_discharge_info,
                                   f_second_charge_info=f_second_charge_info,
                                   f_second_discharge_info=f_second_discharge_info,
                                   s_first_charge_info=s_first_charge_info,
                                   s_first_discharge_info=s_first_discharge_info,
                                   s_second_charge_info=s_second_charge_info,
                                   s_second_discharge_info=s_second_discharge_info,
                                   t_first_charge_info=None, t_first_discharge_info=None,
                                   t_second_charge_info=None,
                                   t_second_discharge_info=None,
                                   r_first_charge_info=None, r_first_discharge_info=None,
                                   r_second_charge_info=None, r_second_discharge_info=None,
                                   )

        if electric_type == "一般工商业":
            first_type = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
            first_type_lis = [low] * 8 + [flat] * 3 + [low] * 2 + [flat] * 6 + [peak] * 2 + [
                flat] * 1 + [low] * 2

            first_set_time = get_month_time(first_type)
            first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
            first_data_48_points = generate_points_data(first_type_lis, first_dic, data_24_hours)

            ges = generate_result_dict(first_type, first_data_48_points)

            type_price = ges["table"]
            f_first_charge_info = ("00:00", "08:00", (type_price[str(first_type)].get("1", "--")), charge_status)
            f_first_discharge_info = ("08:00", "11:00", (type_price[str(first_type)].get("3", "--")), discharge_status)
            f_second_charge_info = ("11:00", "13:00", (type_price[str(first_type)].get("1", "--")), charge_status)
            f_second_discharge_info = ("13:00", "22:00", (type_price[str(first_type)].get("4", "--")), discharge_status)

            return update_strategy(ges, charge_discharge_times, first_type=first_type, second_type=None,
                                   three_type=None,
                                   four_type=None,
                                   f_first_charge_info=f_first_charge_info,
                                   f_first_discharge_info=f_first_discharge_info,
                                   f_second_charge_info=f_second_charge_info,
                                   f_second_discharge_info=f_second_discharge_info,
                                   s_first_charge_info=None,
                                   s_first_discharge_info=None,
                                   s_second_charge_info=None,
                                   s_second_discharge_info=None,
                                   t_first_charge_info=None, t_first_discharge_info=None,
                                   t_second_charge_info=None,
                                   t_second_discharge_info=None,
                                   r_first_charge_info=None, r_first_discharge_info=None,
                                   r_second_charge_info=None, r_second_discharge_info=None,
                                   )

    if region_name == "河南省":
        charge_discharge_times = 2
        first_type = [1, 12]
        second_type = [7, 8]
        three_type = [2, 3, 4, 5, 6, 9, 10, 11]

        first_type_lis = [low] * 7 + [normal] * 3 + [flat] * 4 + [normal] * 3 + [flat] * 1 + [peak] * 1 + \
                         [flat] * 2 + [normal] * 2 + [low] * 1
        second_type_lis = [low] * 7 + [normal] * 3 + [flat] * 2 + [peak] * 2 + [normal] * 3 + [flat] * 3 + [
            peak] * 1 + [normal] * 2 + [low] * 1

        three_type_lis = [low] * 7 + [normal] * 3 + [flat] * 4 + [normal] * 3 + [flat] * 4 + \
                         [normal] * 2 + [low] * 1

        first_set_time = get_month_time(first_type)
        second_set_time = get_month_time(second_type)
        three_set_time = get_month_time(three_type)

        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        second_dic = get_trade_result_data(region_id, data_type_dic, second_set_time)
        three_dic = get_trade_result_data(region_id, data_type_dic, three_set_time)

        first_data_24_points = generate_points_data(first_type_lis, first_dic, data_24_hours)
        second_data_24_points = generate_points_data(second_type_lis, second_dic, data_24_hours)
        three_data_24_points = generate_points_data(three_type_lis, three_dic, data_24_hours)

        ges = generate_result_dict(first_type, first_data_24_points, second_type, second_data_24_points,
                                   three_type, three_data_24_points)
        type_price = ges["table"]

        f_first_charge_info = ("23:00", "07:00", (type_price[str(first_type)].get("1", "--")), charge_status)
        f_first_discharge_info = ("11:00", "14:00", (type_price[str(first_type)].get("3", "--")), discharge_status)
        f_second_charge_info = ("14:00", "17:00", (type_price[str(first_type)].get("2", "--")), charge_status)
        f_second_discharge_info = ("17:00", "21:00", (type_price[str(first_type)].get("4", "--")), discharge_status)

        s_first_charge_info = ("23:00", "07:00", (type_price[str(second_type)].get("1", "--")), charge_status)
        s_first_discharge_info = ("11:00", "14:00", (type_price[str(second_type)].get("4", "--")), discharge_status)
        s_second_charge_info = ("14:00", "17:00", (type_price[str(second_type)].get("2", "--")), charge_status)
        s_second_discharge_info = ("17:00", "21:00", (type_price[str(second_type)].get("3", "--")), discharge_status)

        t_first_charge_info = ("23:00", "07:00", (type_price[str(three_type)].get("1", "--")), charge_status)
        t_first_discharge_info = ("11:00", "14:00", (type_price[str(three_type)].get("3", "--")), discharge_status)
        t_second_charge_info = ("14:00", "17:00", (type_price[str(three_type)].get("2", "--")), charge_status)
        t_second_discharge_info = ("17:00", "21:00", (type_price[str(three_type)].get("3", "--")), discharge_status)

        return update_strategy(ges, charge_discharge_times, first_type=first_type, second_type=second_type,
                               three_type=three_type,
                               four_type=None,
                               f_first_charge_info=f_first_charge_info, f_first_discharge_info=f_first_discharge_info,
                               f_second_charge_info=f_second_charge_info,
                               f_second_discharge_info=f_second_discharge_info,
                               s_first_charge_info=s_first_charge_info, s_first_discharge_info=s_first_discharge_info,
                               s_second_charge_info=s_second_charge_info,
                               s_second_discharge_info=s_second_discharge_info,
                               t_first_charge_info=t_first_charge_info, t_first_discharge_info=t_first_discharge_info,
                               t_second_charge_info=t_second_charge_info,
                               t_second_discharge_info=t_second_discharge_info,
                               r_first_charge_info=None, r_first_discharge_info=None,
                               r_second_charge_info=None, r_second_discharge_info=None,
                               )

    if region_name == "安徽省":
        charge_discharge_times = 2
        first_type = [7, 8]
        second_type = [1, 2, 3, 4, 5, 6, 9, 10, 11, 12]

        first_type_lis = [low] * 9 + [normal] * 7 + [flat] * 8
        second_type_lis = [low] * 8 + [normal] * 1 + [flat] * 3 + [normal] * 5 + [flat] * 5 + [normal] * 1 + [low] * 1

        first_set_time = get_month_time(first_type)
        second_set_time = get_month_time(second_type)

        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        second_dic = get_trade_result_data(region_id, data_type_dic, second_set_time)
        first_data_48_points = generate_points_data(first_type_lis, first_dic, data_24_hours)
        second_data_48_points = generate_points_data(second_type_lis, second_dic, data_24_hours)

        ges = generate_result_dict(first_type, first_data_48_points, second_type, second_data_48_points)
        type_price = ges["table"]
        f_first_charge_info = ("00:00", "08:00", (type_price[str(first_type)]["1"]), charge_status)
        f_first_discharge_info = ("16:00", "24:00", (type_price[str(first_type)]["3"]), discharge_status)

        s_first_charge_info = ("23:00", "07:00", (type_price[str(second_type)]["1"]), charge_status)
        s_first_discharge_info = ("09:00", "12:00", (type_price[str(second_type)]["3"]), discharge_status)
        s_second_charge_info = ("12:00", "17:00", (type_price[str(second_type)]["2"]), charge_status)
        s_second_discharge_info = ("17:00", "22:00", (type_price[str(second_type)]["3"]), discharge_status)

        return update_strategy(ges, charge_discharge_times, first_type=first_type, second_type=second_type,
                               three_type=None,
                               four_type=None,
                               f_first_charge_info=f_first_charge_info,
                               f_first_discharge_info=f_first_discharge_info,
                               f_second_charge_info=None,
                               f_second_discharge_info=None,
                               s_first_charge_info=s_first_charge_info,
                               s_first_discharge_info=s_first_discharge_info,
                               s_second_charge_info=s_second_charge_info,
                               s_second_discharge_info=s_second_discharge_info,
                               t_first_charge_info=None, t_first_discharge_info=None,
                               t_second_charge_info=None,
                               t_second_discharge_info=None,
                               r_first_charge_info=None, r_first_discharge_info=None,
                               r_second_charge_info=None, r_second_discharge_info=None,
                               )

    if '冀北' in region_name:
        first_type = [6, 7, 8]
        second_type = [1, 11, 12]
        three_type = [2, 3, 4, 5, 9, 10]

        first_type_lis = [low] * 7 + [normal] * 3 + [peak] * 1 + [flat] * 1 + [normal] * 2 + [flat] * 3 + \
                         [peak] * 1 + [normal] * 1 + [flat] * 1 + [peak] * 1 + [normal] * 2 + [low] * 1
        second_type_lis = [low] * 7 + [normal] * 1 + [flat] * 1 + [normal] * 1 + [flat] * 1 + [normal] * 3 + \
                          [flat] * 3 + [peak] * 2 + [flat] * 1 + [normal] * 3 + [low] * 1
        three_type_lis = [low] * 7 + [flat] * 2 + [peak] * 3 + [flat] * 3 + [peak] * 3 + \
                         [flat] * 1 + [peak] * 2 + [flat] * 2 + [low] * 1

        first_set_time = get_month_time(first_type)
        second_set_time = get_month_time(second_type)
        three_set_time = get_month_time(three_type)

        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        second_dic = get_trade_result_data(region_id, data_type_dic, second_set_time)
        three_dic = get_trade_result_data(region_id, data_type_dic, three_set_time)

        first_data_24_points = generate_points_data(first_type_lis, first_dic, data_24_hours)
        second_data_24_points = generate_points_data(second_type_lis, second_dic, data_24_hours)
        three_data_24_points = generate_points_data(three_type_lis, three_dic, data_24_hours)

        return generate_result_dict(first_type, first_data_24_points, second_type, second_data_24_points,
                                    three_type, three_data_24_points)

    if '冀南' in region_name:
        first_type = [6, 7, 8]
        second_type = [1, 2, 12]
        three_type = [3, 4, 5, 9, 10, 11]

        first_type_lis = [low] * 8 + [normal] * 7 + [flat] * 4 + [peak] * 3 + [flat] * 1 + [normal] * 1
        second_type_lis = [normal] * 1 + [low] * 5 + [normal] * 6 + [low] * 3 + [normal] * 1 + [flat] * 1 + \
                          [peak] * 2 + [flat] * 5
        three_type_lis = [normal] * 1 + [low] * 5 + [normal] * 6 + [low] * 3 + [normal] * 1 + [flat] * 8

        first_set_time = get_month_time(first_type)
        second_set_time = get_month_time(second_type)
        three_set_time = get_month_time(three_type)

        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        second_dic = get_trade_result_data(region_id, data_type_dic, second_set_time)
        three_dic = get_trade_result_data(region_id, data_type_dic, three_set_time)

        first_data_24_points = generate_points_data(first_type_lis, first_dic, data_24_hours)
        second_data_24_points = generate_points_data(second_type_lis, second_dic, data_24_hours)
        three_data_24_points = generate_points_data(three_type_lis, three_dic, data_24_hours)

        return generate_result_dict(first_type, first_data_24_points, second_type, second_data_24_points,
                                    three_type, three_data_24_points)

    if region_name == "四川省":
        charge_discharge_times = 2

        if electric_price_type == "两部制":
            first_type = [7, 8]
            second_type = [2, 3, 4, 5, 6, 9, 10, 11]
            three_type = [1, 12]
            first_type_lis = [low] * 7 + [normal] * 3 + [flat] * 2 + [normal] * 3 + [peak] * 2 + [flat] * 4 + [
                normal] * 2 + [low] * 1
            second_type_lis = [low] * 7 + [normal] * 3 + [flat] * 2 + [normal] * 3 + [flat] * 6 + [normal] * 2 + [
                low] * 1
            three_type_lis = [low] * 7 + [normal] * 3 + [flat] * 2 + [normal] * 3 + [flat] * 4 + [peak] * 2 + [
                normal] * 2 + [low] * 1

            first_set_time = get_month_time(first_type)
            second_set_time = get_month_time(second_type)
            three_set_time = get_month_time(three_type)

            first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
            second_dic = get_trade_result_data(region_id, data_type_dic, second_set_time)
            three_dic = get_trade_result_data(region_id, data_type_dic, three_set_time)

            first_data_24_points = generate_points_data(first_type_lis, first_dic, data_24_hours)
            second_data_24_points = generate_points_data(second_type_lis, second_dic, data_24_hours)
            three_data_24_points = generate_points_data(three_type_lis, three_dic, data_24_hours)

            ges = generate_result_dict(first_type, first_data_24_points, second_type, second_data_24_points,
                                       copy.deepcopy(three_type), three_data_24_points)
            type_price = ges["table"]

            f_first_charge_info = ("23:00", "07:00", (type_price[str(first_type)].get("1", "--")), charge_status)
            f_first_discharge_info = ("10:00", "12:00", (type_price[str(first_type)].get("3", "--")), discharge_status)
            f_second_charge_info = ("12:00", "15:00", (type_price[str(first_type)].get("2", "--")), charge_status)
            f_second_discharge_info = ("15:00", "21:00", (type_price[str(first_type)].get("4", "--")), discharge_status)

            s_first_charge_info = ("23:00", "07:00", (type_price[str(second_type)].get("1", "--")), charge_status)
            s_first_discharge_info = ("10:00", "12:00", (type_price[str(second_type)].get("3", "--")), discharge_status)
            s_second_charge_info = ("12:00", "15:00", (type_price[str(second_type)].get("2", "--")), charge_status)
            s_second_discharge_info = (
                "15:00", "21:00", (type_price[str(second_type)].get("3", "--")), discharge_status)

            t_first_charge_info = ("23:00", "07:00", (type_price[str(three_type)].get("1", "--")), charge_status)
            t_first_discharge_info = ("10:00", "12:00", (type_price[str(three_type)].get("3", "--")), discharge_status)
            t_second_charge_info = ("12:00", "15:00", (type_price[str(three_type)].get("2", "--")), charge_status)
            t_second_discharge_info = ("15:00", "21:00", (type_price[str(three_type)].get("3", "--")), discharge_status)

            return update_strategy(ges, charge_discharge_times, first_type=first_type, second_type=second_type,
                                   three_type=three_type,
                                   four_type=None,
                                   f_first_charge_info=f_first_charge_info,
                                   f_first_discharge_info=f_first_discharge_info,
                                   f_second_charge_info=f_second_charge_info,
                                   f_second_discharge_info=f_second_discharge_info,
                                   s_first_charge_info=s_first_charge_info,
                                   s_first_discharge_info=s_first_discharge_info,
                                   s_second_charge_info=s_second_charge_info,
                                   s_second_discharge_info=s_second_discharge_info,
                                   t_first_charge_info=t_first_charge_info,
                                   t_first_discharge_info=t_first_discharge_info,
                                   t_second_charge_info=t_second_charge_info,
                                   t_second_discharge_info=t_second_discharge_info,
                                   r_first_charge_info=None, r_first_discharge_info=None,
                                   r_second_charge_info=None, r_second_discharge_info=None,
                                   )

        if electric_price_type == "单一制":
            first_type = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

            first_type_lis = [low] * 7 + [normal] * 3 + [flat] * 2 + [normal] * 3 + [flat] * 2 + [flat] * 4 + [
                normal] * 2 + [low] * 1

            first_set_time = get_month_time(first_type)

            first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)

            first_data_24_points = generate_points_data(first_type_lis, first_dic, data_24_hours)

            ges = generate_result_dict(first_type, first_data_24_points)
            type_price = ges["table"]

            f_first_charge_info = ("23:00", "07:00", (type_price[str(first_type)].get("1", "--")), charge_status)
            f_first_discharge_info = ("10:00", "12:00", (type_price[str(first_type)].get("3", "--")), discharge_status)
            f_second_charge_info = ("12:00", "15:00", (type_price[str(first_type)].get("2", "--")), charge_status)
            f_second_discharge_info = ("15:00", "21:00", (type_price[str(first_type)].get("3", "--")), discharge_status)

            return update_strategy(ges, charge_discharge_times, first_type=first_type, second_type=None,
                                   three_type=None,
                                   four_type=None,
                                   f_first_charge_info=f_first_charge_info,
                                   f_first_discharge_info=f_first_discharge_info,
                                   f_second_charge_info=f_second_charge_info,
                                   f_second_discharge_info=f_second_discharge_info,
                                   s_first_charge_info=None,
                                   s_first_discharge_info=None,
                                   s_second_charge_info=None,
                                   s_second_discharge_info=None,
                                   t_first_charge_info=None,
                                   t_first_discharge_info=None,
                                   t_second_charge_info=None,
                                   t_second_discharge_info=None,
                                   r_first_charge_info=None, r_first_discharge_info=None,
                                   r_second_charge_info=None, r_second_discharge_info=None,
                                   )

    if region_name == "重庆市":
        first_type = [1, 7, 8, 12]
        second_type = [2, 3, 4, 5, 6, 9, 10, 11]

        first_type_lis = [low] * 8 + [normal] * 3 + [flat] * 1 + [peak] * 2 + [flat] * 3 + [normal] * 3 + [flat] * 2 + [
            normal] * 2
        second_type_lis = [low] * 8 + [normal] * 3 + [flat] * 6 + [normal] * 3 + [flat] * 2 + [normal] * 2

        first_set_time = get_month_time(first_type)
        second_set_time = get_month_time(second_type)

        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        second_dic = get_trade_result_data(region_id, data_type_dic, second_set_time)

        first_data_24_points = generate_points_data(first_type_lis, first_dic, data_24_hours)
        second_data_24_points = generate_points_data(second_type_lis, second_dic, data_24_hours)

        return generate_result_dict(first_type, first_data_24_points, second_type, second_data_24_points,
                                    )

    if region_name == "天津市":

        if electric_price_type == "两部制":
            first_type = [1, 12]
            second_type = [7, 8]
            three_type = [2, 3, 4, 5, 6, 9, 10, 11]
            first_type_lis = [low] * 7 + [normal] * 2 + [flat] * 2 + [flat] * 1 + [normal] * 4 + [flat] * 2 + [peak] * 1 \
                             + [flat] * 2 + [normal] * 2 + [low] * 1
            second_type_lis = [low] * 7 + [normal] * 2 + [flat] * 2 + [peak] * 1 + [normal] * 4 + [peak] * 1 \
                              + [flat] * 4 + [normal] * 2 + [low] * 1
            three_type_lis = [low] * 7 + [normal] * 2 + [flat] * 3 + [normal] * 4 + [flat] * 5 + [normal] * 2 \
                             + [low] * 1

            first_set_time = get_month_time(first_type)
            second_set_time = get_month_time(second_type)
            three_set_time = get_month_time(three_type)

            first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
            second_dic = get_trade_result_data(region_id, data_type_dic, second_set_time)
            three_dic = get_trade_result_data(region_id, data_type_dic, three_set_time)

            first_data_24_points = generate_points_data(first_type_lis, first_dic, data_24_hours)
            second_data_24_points = generate_points_data(second_type_lis, second_dic, data_24_hours)
            three_data_24_points = generate_points_data(three_type_lis, three_dic, data_24_hours)

            return generate_result_dict(first_type, first_data_24_points, second_type, second_data_24_points,
                                        three_type, three_data_24_points)
        if electric_price_type == "单一制":
            first_type = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
            first_type_lis = [low] * 7 + [normal] * 2 + [flat] * 2 + [flat] * 1 + [normal] * 4 + [flat] * 2 + [flat] * 1 \
                             + [flat] * 2 + [normal] * 2 + [low] * 1
            first_set_time = get_month_time(first_type)
            first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
            first_data_24_points = generate_points_data(first_type_lis, first_dic, data_24_hours)

            return generate_result_dict(first_type, first_data_24_points)

    if region_name == "湖北省":
        charge_discharge_times = 2
        first_type = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        first_type_lis = [low] * 7 + [normal] * 2 + [flat] * 6 + [normal] * 5 + [peak] * 2 + [normal] * 1 + [low] * 1

        first_set_time = get_month_time(first_type)
        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        first_data_24_points = generate_points_data(first_type_lis, first_dic, data_24_hours)

        ges = generate_result_dict(first_type, first_data_24_points)

        type_price = ges["table"]

        f_first_charge_info = ("23:00", "07:00", (type_price[str(first_type)].get("1", "--")), charge_status)
        f_first_discharge_info = ("09:00", "15:00", (type_price[str(first_type)].get("3", "--")), discharge_status)
        f_second_charge_info = ("14:00", "18:00", (type_price[str(first_type)].get("2", "--")), charge_status)
        f_second_discharge_info = ("18:00", "23:00", (type_price[str(first_type)].get("4", "--")), discharge_status)
        return update_strategy(ges, charge_discharge_times, first_type=first_type, second_type=None,
                               three_type=None,
                               four_type=None,
                               f_first_charge_info=f_first_charge_info, f_first_discharge_info=f_first_discharge_info,
                               f_second_charge_info=f_second_charge_info,
                               f_second_discharge_info=f_second_discharge_info,
                               s_first_charge_info=None, s_first_discharge_info=None,
                               s_second_charge_info=None,
                               s_second_discharge_info=None,
                               t_first_charge_info=None, t_first_discharge_info=None,
                               t_second_charge_info=None,
                               t_second_discharge_info=None,
                               r_first_charge_info=None, r_first_discharge_info=None,
                               r_second_charge_info=None, r_second_discharge_info=None,
                               )

    if region_name == "湖南省":
        charge_discharge_times = 2
        first_type = [1, 7, 8, 9, 12]
        second_type = [2, 3, 4, 5, 6, 10, 11]

        first_type_lis = [low] * 7 + [normal] * 4 + [flat] * 3 + [normal] * 4 + [peak] * 4 + [flat] * 1 + [low] * 1
        second_type_lis = [low] * 7 + [normal] * 4 + [flat] * 3 + [normal] * 4 + [flat] * 5 + [low] * 1
        first_set_time = get_month_time(first_type)
        second_set_time = get_month_time(second_type)

        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        second_dic = get_trade_result_data(region_id, data_type_dic, second_set_time)

        first_data_24_points = generate_points_data(first_type_lis, first_dic, data_24_hours)
        second_data_24_points = generate_points_data(second_type_lis, second_dic, data_24_hours)

        ges = generate_result_dict(first_type, first_data_24_points, second_type, second_data_24_points)

        type_price = ges["table"]

        f_first_charge_info = ("23:00", "07:00", (type_price[str(first_type)].get("1", "--")), charge_status)
        f_first_discharge_info = ("11:00", "14:00", (type_price[str(first_type)].get("3", "--")), discharge_status)
        f_second_charge_info = ("14:00", "18:00", (type_price[str(first_type)].get("2", "--")), charge_status)
        f_second_discharge_info = ("18:00", "23:00", (type_price[str(first_type)].get("4", "--")), discharge_status)

        s_first_charge_info = ("23:00", "07:00", (type_price[str(second_type)].get("1", "--")), charge_status)
        s_first_discharge_info = ("11:00", "14:00", (type_price[str(second_type)].get("3", "--")), discharge_status)
        s_second_charge_info = ("14:00", "18:00", (type_price[str(second_type)].get("2", "--")), charge_status)
        s_second_discharge_info = ("18:00", "23:00", (type_price[str(second_type)].get("3", "--")), discharge_status)

        return update_strategy(ges, charge_discharge_times, first_type=first_type, second_type=second_type,
                               three_type=None,
                               four_type=None,
                               f_first_charge_info=f_first_charge_info, f_first_discharge_info=f_first_discharge_info,
                               f_second_charge_info=f_second_charge_info,
                               f_second_discharge_info=f_second_discharge_info,
                               s_first_charge_info=s_first_charge_info, s_first_discharge_info=s_first_discharge_info,
                               s_second_charge_info=s_second_charge_info,
                               s_second_discharge_info=s_second_discharge_info,
                               t_first_charge_info=None, t_first_discharge_info=None,
                               t_second_charge_info=None,
                               t_second_discharge_info=None,
                               r_first_charge_info=None, r_first_discharge_info=None,
                               r_second_charge_info=None, r_second_discharge_info=None,
                               )

    if region_name == "江西省":
        first_type = [1, 12]
        second_type = [7, 8, 9]
        three_type = [2, 3, 4, 5, 6, 10, 11]

        first_type_lis = [low] * 6 + [normal] * 3 + [flat] * 3 + [normal] * 5 + [peak] * 2 + [flat] * 1 + [normal] * 4
        second_type_lis = [low] * 6 + [normal] * 10 + [flat] * 4 + [peak] * 2 + [normal] * 2
        three_type_lis = [low] * 6 + [normal] * 10 + [flat] * 6 + [normal] * 2

        first_set_time = get_month_time(first_type)
        second_set_time = get_month_time(second_type)
        three_set_time = get_month_time(three_type)

        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        second_dic = get_trade_result_data(region_id, data_type_dic, second_set_time)
        three_dic = get_trade_result_data(region_id, data_type_dic, three_set_time)

        first_data_24_points = generate_points_data(first_type_lis, first_dic, data_24_hours)
        second_data_24_points = generate_points_data(second_type_lis, second_dic, data_24_hours)
        three_data_24_points = generate_points_data(three_type_lis, three_dic, data_24_hours)

        return generate_result_dict(first_type, first_data_24_points, second_type, second_data_24_points,
                                    three_type, three_data_24_points)

    if region_name == "上海市":
        charge_discharge_times = 2
        if electric_type == "一般工商业":
            if electric_price_type == "单一制":
                charge_discharge_times = 1
                first_type = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
                first_type_lis = [low] * 6 + [flat] * 16 + [low] * 2

                first_set_time = get_month_time(first_type)
                first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
                first_data_24_points = generate_points_data(first_type_lis, first_dic, data_24_hours)

                ges = generate_result_dict(first_type, first_data_24_points)

                type_price = ges["table"]

                f_first_charge_info = ("22:00", "07:00", (type_price[str(first_type)].get("1", "--")), charge_status)
                f_first_discharge_info = (
                    "07:00", "22:00", (type_price[str(first_type)].get("3", "--")), discharge_status)

                return update_strategy(ges, charge_discharge_times, first_type=first_type, second_type=None,
                                       three_type=None,
                                       four_type=None,
                                       f_first_charge_info=f_first_charge_info,
                                       f_first_discharge_info=f_first_discharge_info,
                                       f_second_charge_info=None,
                                       f_second_discharge_info=None,
                                       s_first_charge_info=None,
                                       s_first_discharge_info=None,
                                       s_second_charge_info=None,
                                       s_second_discharge_info=None,
                                       t_first_charge_info=None, t_first_discharge_info=None,
                                       t_second_charge_info=None,
                                       t_second_discharge_info=None,
                                       r_first_charge_info=None, r_first_discharge_info=None,
                                       r_second_charge_info=None, r_second_discharge_info=None,
                                       )

            if electric_price_type == "两部制":
                three_type = [1, 12]
                first_type = [7, 8]
                second_type = [9]
                four_type = [2, 3, 4, 5, 6, 10, 11]
                print(first_type, second_type, three_type, four_type)
                first_type_lis = [low] * 6 + [normal] * 2 + [flat] * 4 + [peak] * 2 + [flat] * 1 + [normal] * 3 + [
                    flat] * 3 + [normal] * 1 + [low] * 2
                second_type_lis = [low] * 6 + [normal] * 2 + [flat] * 7 + [normal] * 3 + [
                    flat] * 3 + [normal] * 1 + [low] * 2
                three_type_lis = [low] * 6 + [normal] * 2 + [flat] * 3 + [normal] * 7 + [flat] * 1 + [peak] * 2 + \
                                 [normal] * 1 + [low] * 2
                four_type_lis = [low] * 6 + [normal] * 2 + [flat] * 3 + [normal] * 7 + [flat] * 3 + [normal] * 1 + [
                    low] * 2

                first_set_time = get_month_time(first_type)
                second_set_time = get_month_time(second_type)
                three_set_time = get_month_time(three_type)
                four_set_time = get_month_time(four_type)

                first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
                second_dic = get_trade_result_data(region_id, data_type_dic, second_set_time)
                three_dic = get_trade_result_data(region_id, data_type_dic, three_set_time)
                four_dic = get_trade_result_data(region_id, data_type_dic, four_set_time)

                first_data_48_points = generate_points_data(first_type_lis, first_dic, data_24_hours)
                second_data_48_points = generate_points_data(second_type_lis, second_dic, data_24_hours)
                three_data_48_points = generate_points_data(three_type_lis, three_dic, data_24_hours)
                four_data_48_points = generate_points_data(four_type_lis, four_dic, data_24_hours)

                ges = generate_result_dict(first_type, first_data_48_points, second_type, second_data_48_points,
                                           three_type, three_data_48_points, four_type, four_data_48_points)
                type_price = ges["table"]

                f_first_charge_info = ("23:00", "06:00", (type_price[str(first_type)].get("1", "--")), charge_status)
                f_first_discharge_info = (
                    "08:00", "15:00", (type_price[str(first_type)].get("4", "--")), discharge_status)
                f_second_charge_info = (
                    "15:00", "18:00", (type_price[str(first_type)].get("2", "--")), charge_status)
                f_second_discharge_info = (
                    "18:00", "21:00", (type_price[str(first_type)].get("3", "--")), discharge_status)

                s_first_charge_info = (
                    "23:00", "06:00", (type_price[str(second_type)].get("1", "--")), charge_status)
                s_first_discharge_info = (
                    "08:00", "15:00", (type_price[str(second_type)].get("3", "--")), discharge_status)
                s_second_charge_info = (
                    "15:00", "18:00", (type_price[str(second_type)].get("2", "--")), charge_status)
                s_second_discharge_info = (
                    "18:00", "21:00", (type_price[str(second_type)].get("3", "--")), discharge_status)

                t_first_charge_info = (
                    "22:00", "06:00", (type_price[str(three_type)].get("1", "--")), charge_status)
                t_first_discharge_info = (
                    "08:00", "11:00", (type_price[str(three_type)].get("3", "--")), discharge_status)
                t_second_charge_info = (
                    "11:00", "18:00", (type_price[str(three_type)].get("2", "--")), charge_status)
                t_second_discharge_info = (
                    "18:00", "21:00", (type_price[str(three_type)].get("3", "--")), discharge_status)

                r_first_charge_info = (
                    "22:00", "06:00", (type_price[str(four_type)].get("1", "--")), charge_status)
                r_first_discharge_info = (
                    "08:00", "11:00", (type_price[str(four_type)].get("3", "--")), discharge_status)
                r_second_charge_info = (
                    "11:00", "18:00", (type_price[str(four_type)].get("2", "--")), charge_status)
                r_second_discharge_info = (
                    "18:00", "21:00", (type_price[str(four_type)].get("3", "--")), discharge_status)

                return update_strategy(ges, charge_discharge_times, first_type=first_type, second_type=second_type,
                                       three_type=three_type,
                                       four_type=four_type,
                                       f_first_charge_info=f_first_charge_info,
                                       f_first_discharge_info=f_first_discharge_info,
                                       f_second_charge_info=f_second_charge_info,
                                       f_second_discharge_info=f_second_discharge_info,
                                       s_first_charge_info=s_first_charge_info,
                                       s_first_discharge_info=s_first_discharge_info,
                                       s_second_charge_info=s_second_charge_info,
                                       s_second_discharge_info=s_second_discharge_info,
                                       t_first_charge_info=t_first_charge_info,
                                       t_first_discharge_info=t_first_discharge_info,
                                       t_second_charge_info=t_second_charge_info,
                                       t_second_discharge_info=t_second_discharge_info,
                                       r_first_charge_info=r_first_charge_info,
                                       r_first_discharge_info=r_first_discharge_info,
                                       r_second_charge_info=r_second_charge_info,
                                       r_second_discharge_info=r_second_discharge_info,
                                       )

        if electric_type == "大工业":
            first_type = [7, 8]
            second_type = [9]
            three_type = [1, 12]
            four_type = [2, 3, 4, 5, 6, 10, 11]

            first_type_lis = [low] * 6 + [normal] * 2 + [flat] * 4 + [peak] * 2 + [flat] * 1 + [normal] * 3 + [
                flat] * 3 + [normal] * 1 + [low] * 2
            second_type_lis = [low] * 6 + [normal] * 2 + [flat] * 7 + [normal] * 3 + [
                flat] * 3 + [normal] * 1 + [low] * 2
            three_type_lis = [low] * 6 + [normal] * 2 + [flat] * 3 + [normal] * 7 + [flat] * 1 + [peak] * 2 + \
                             [normal] * 1 + [low] * 2
            four_type_lis = [low] * 6 + [normal] * 2 + [flat] * 3 + [normal] * 7 + [flat] * 3 + [normal] * 1 + [low] * 2

            first_set_time = get_month_time(first_type)
            second_set_time = get_month_time(second_type)
            three_set_time = get_month_time(three_type)
            four_set_time = get_month_time(four_type)

            first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
            second_dic = get_trade_result_data(region_id, data_type_dic, second_set_time)
            three_dic = get_trade_result_data(region_id, data_type_dic, three_set_time)
            four_dic = get_trade_result_data(region_id, data_type_dic, four_set_time)

            first_data_48_points = generate_points_data(first_type_lis, first_dic, data_24_hours)
            second_data_48_points = generate_points_data(second_type_lis, second_dic, data_24_hours)
            three_data_48_points = generate_points_data(three_type_lis, three_dic, data_24_hours)
            four_data_48_points = generate_points_data(four_type_lis, four_dic, data_24_hours)

            ges = generate_result_dict(first_type, first_data_48_points, second_type, second_data_48_points,
                                       three_type, three_data_48_points, four_type, four_data_48_points)
            type_price = ges["table"]

            f_first_charge_info = ("23:00", "06:00", (type_price[str(first_type)].get("1", "--")), charge_status)
            f_first_discharge_info = (
                "08:00", "15:00", (type_price[str(first_type)].get("4", "--")), discharge_status)
            f_second_charge_info = (
                "15:00", "18:00", (type_price[str(first_type)].get("2", "--")), charge_status)
            f_second_discharge_info = (
                "18:00", "21:00", (type_price[str(first_type)].get("3", "--")), discharge_status)

            s_first_charge_info = (
                "23:00", "06:00", (type_price[str(second_type)].get("1", "--")), charge_status)
            s_first_discharge_info = (
                "08:00", "15:00", (type_price[str(second_type)].get("3", "--")), discharge_status)
            s_second_charge_info = (
                "15:00", "18:00", (type_price[str(second_type)].get("2", "--")), charge_status)
            s_second_discharge_info = (
                "18:00", "21:00", (type_price[str(second_type)].get("3", "--")), discharge_status)

            t_first_charge_info = (
                "22:00", "06:00", (type_price[str(three_type)].get("1", "--")), charge_status)
            t_first_discharge_info = (
                "08:00", "11:00", (type_price[str(three_type)].get("3", "--")), discharge_status)
            t_second_charge_info = (
                "11:00", "18:00", (type_price[str(three_type)].get("2", "--")), charge_status)
            t_second_discharge_info = (
                "18:00", "21:00", (type_price[str(three_type)].get("3", "--")), discharge_status)

            r_first_charge_info = (
                "22:00", "06:00", (type_price[str(four_type)].get("1", "--")), charge_status)
            r_first_discharge_info = (
                "08:00", "11:00", (type_price[str(four_type)].get("3", "--")), discharge_status)
            r_second_charge_info = (
                "11:00", "18:00", (type_price[str(four_type)].get("2", "--")), charge_status)
            r_second_discharge_info = (
                "18:00", "21:00", (type_price[str(four_type)].get("3", "--")), discharge_status)

            return update_strategy(ges, charge_discharge_times, first_type=first_type, second_type=second_type,
                                   three_type=three_type,
                                   four_type=four_type,
                                   f_first_charge_info=f_first_charge_info,
                                   f_first_discharge_info=f_first_discharge_info,
                                   f_second_charge_info=f_second_charge_info,
                                   f_second_discharge_info=f_second_discharge_info,
                                   s_first_charge_info=s_first_charge_info,
                                   s_first_discharge_info=s_first_discharge_info,
                                   s_second_charge_info=s_second_charge_info,
                                   s_second_discharge_info=s_second_discharge_info,
                                   t_first_charge_info=t_first_charge_info,
                                   t_first_discharge_info=t_first_discharge_info,
                                   t_second_charge_info=t_second_charge_info,
                                   t_second_discharge_info=t_second_discharge_info,
                                   r_first_charge_info=r_first_charge_info,
                                   r_first_discharge_info=r_first_discharge_info,
                                   r_second_charge_info=r_second_charge_info,
                                   r_second_discharge_info=r_second_discharge_info,
                                   )

    if region_name == "海南省":
        charge_discharge_times = 2
        first_type = [5, 6, 7]
        second_type = [1, 2, 3, 4, 8, 9, 10, 11, 12]

        first_type_lis = [low] * 7 + [normal] * 3 + [flat] * 2 + [normal] * 4 + [flat] * 4 + [peak] * 2 + [
            normal] * 1 + [low] * 1
        second_type_lis = [low] * 7 + [normal] * 3 + [flat] * 2 + [normal] * 4 + [flat] * 6 + [normal] * 1 + [low] * 1

        first_set_time = get_month_time(first_type)
        second_set_time = get_month_time(second_type)

        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        second_dic = get_trade_result_data(region_id, data_type_dic, second_set_time)

        first_data_24_points = generate_points_data(first_type_lis, first_dic, data_24_hours)
        second_data_24_points = generate_points_data(second_type_lis, second_dic, data_24_hours)

        ges = generate_result_dict(first_type, first_data_24_points, second_type, second_data_24_points)

        type_price = ges["table"]

        f_first_charge_info = ("23:00", "07:00", (type_price[str(first_type)].get("1", "--")), charge_status)
        f_first_discharge_info = (
            "10:00", "12:00", (type_price[str(first_type)].get("3", "--")), discharge_status)
        f_second_charge_info = (
            "12:00", "16:00", (type_price[str(first_type)].get("2", "--")), charge_status)
        f_second_discharge_info = (
            "16:00", "22:00", (type_price[str(first_type)].get("3", "--")), discharge_status)

        s_first_charge_info = (
            "23:00", "07:00", (type_price[str(second_type)].get("1", "--")), charge_status)
        s_first_discharge_info = (
            "10:00", "12:00", (type_price[str(second_type)].get("3", "--")), discharge_status)
        s_second_charge_info = (
            "12:00", "16:00", (type_price[str(second_type)].get("2", "--")), charge_status)
        s_second_discharge_info = (
            "16:00", "22:00", (type_price[str(second_type)].get("3", "--")), discharge_status)

        return update_strategy(ges, charge_discharge_times, first_type=first_type, second_type=second_type,
                               three_type=None,
                               four_type=None,
                               f_first_charge_info=f_first_charge_info,
                               f_first_discharge_info=f_first_discharge_info,
                               f_second_charge_info=f_second_charge_info,
                               f_second_discharge_info=f_second_discharge_info,
                               s_first_charge_info=s_first_charge_info,
                               s_first_discharge_info=s_first_discharge_info,
                               s_second_charge_info=s_second_charge_info,
                               s_second_discharge_info=s_second_discharge_info,
                               t_first_charge_info=None, t_first_discharge_info=None,
                               t_second_charge_info=None,
                               t_second_discharge_info=None,
                               r_first_charge_info=None, r_first_discharge_info=None,
                               r_second_charge_info=None,
                               r_second_discharge_info=None,
                               )

    if region_name == "广西壮族自治区":
        first_type = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        first_type_lis = [low] * 7 + [normal] * 4 + [flat] * 2 + [normal] * 4 + [flat] * 6 + [low] * 1

        first_set_time = get_month_time(first_type)
        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        first_data_24_points = generate_points_data(first_type_lis, first_dic, data_24_hours)

        return generate_result_dict(first_type, first_data_24_points)

    if region_name == "青海省":
        first_type = [1, 2, 3, 10, 11, 12]
        second_type = [4, 5, 6, 7, 8, 9]

        first_type_lis = [low] * 8 + [peak] * 1 + [flat] * 2 + [normal] * 7 + [flat] * 2 + [peak] * 1 + [
            flat] * 2 + [normal] * 1
        second_type_lis = [low] * 8 + [flat] * 3 + [normal] * 7 + [flat] * 5 + [normal] * 1

        first_set_time = get_month_time(first_type)
        second_set_time = get_month_time(second_type)

        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        second_dic = get_trade_result_data(region_id, data_type_dic, second_set_time)

        first_data_24_points = generate_points_data(first_type_lis, first_dic, data_24_hours)
        second_data_24_points = generate_points_data(second_type_lis, second_dic, data_24_hours)

        return generate_result_dict(first_type, first_data_24_points, second_type, second_data_24_points)

    if region_name == "宁夏回族自治区":
        first_type = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        first_type_lis = [normal] * 7 + [flat] * 2 + [low] * 8 + [flat] * 6 + [normal] * 1

        first_set_time = get_month_time(first_type)
        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        first_data_24_points = generate_points_data(first_type_lis, first_dic, data_24_hours)

        return generate_result_dict(first_type, first_data_24_points)

    if region_name == "甘肃省":
        first_type = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        first_type_lis = [normal] * 7 + [flat] * 2 + [low] * 8 + [flat] * 6 + [normal] * 1

        first_set_time = get_month_time(first_type)
        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        first_data_24_points = generate_points_data(first_type_lis, first_dic, data_24_hours)

        return generate_result_dict(first_type, first_data_24_points)

    if '蒙西' in region_name:
        first_type = [1, 2, 3, 4, 5, 9, 10, 11, 12]
        second_type = [6, 7, 8]

        first_type_lis = [low] * 4 + [normal] * 6 + [low] * 5 + [normal] * 2 + [flat] * 4 + [normal] * 3
        second_type_lis = [normal] * 5 + [flat] * 2 + [normal] * 3 + [low] * 5 + [normal] * 2 + [flat] * 1 + \
                          [peak] * 2 + [flat] * 1 + [normal] * 3

        first_set_time = get_month_time(first_type)
        second_set_time = get_month_time(second_type)

        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        second_dic = get_trade_result_data(region_id, data_type_dic, second_set_time)

        first_data_24_points = generate_points_data(first_type_lis, first_dic, data_24_hours)
        second_data_24_points = generate_points_data(second_type_lis, second_dic, data_24_hours)

        return generate_result_dict(first_type, first_data_24_points, second_type, second_data_24_points)

    if region_name == "新疆维吾尔自治区":
        first_type = [5, 6, 8]
        second_type = [1, 11, 12]
        three_type = [2, 3, 4, 9, 10]
        four_type = [7]

        first_type_lis = [normal] * 4 + [low] * 4 + [flat] * 3 + [normal] * 2 + [low] * 1 + [valley] * 2 + [
            low] * 1 + [normal] * 2 + [flat] * 5
        second_type_lis = [normal] * 4 + [low] * 4 + [flat] * 3 + [normal] * 2 + [low] * 4 + [normal] * 2 + [peak] * 2 \
                          + [flat] * 2 + [flat] * 1
        three_type_lis = [normal] * 4 + [low] * 4 + [flat] * 3 + [normal] * 2 + [low] * 4 + [normal] * 2 + [flat] * 5
        four_type_lis = [normal] * 4 + [low] * 4 + [flat] * 3 + [normal] * 2 + [low] * 1 + [valley] * 2 + [
            low] * 1 + [normal] * 2 + [flat] * 2 + [peak] * 2 + [flat] * 1

        first_set_time = get_month_time(first_type)
        second_set_time = get_month_time(second_type)
        three_set_time = get_month_time(three_type)
        four_set_time = get_month_time(four_type)

        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        second_dic = get_trade_result_data(region_id, data_type_dic, second_set_time)
        three_dic = get_trade_result_data(region_id, data_type_dic, three_set_time)
        four_dic = get_trade_result_data(region_id, data_type_dic, four_set_time)

        first_data_48_points = generate_points_data(first_type_lis, first_dic, data_24_hours)
        second_data_48_points = generate_points_data(second_type_lis, second_dic, data_24_hours)
        three_data_48_points = generate_points_data(three_type_lis, three_dic, data_24_hours)
        four_data_48_points = generate_points_data(four_type_lis, four_dic, data_24_hours)

        return generate_result_dict(first_type, first_data_48_points, second_type, second_data_48_points,
                                    three_type, three_data_48_points, four_type, four_data_48_points)

    if region_name == "贵州省":
        charge_discharge_times = 2
        first_type = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        first_type_lis = [normal] * 24
        if electric_price_type == "两部制":
            first_type_lis = [low] * 7 + [normal] * 2 + [flat] * 3 + [normal] * 4 + [flat] * 5 + [normal] * 2 + [
                low] * 1
        first_set_time = get_month_time(first_type)
        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        first_data_24_points = generate_points_data(first_type_lis, first_dic, data_24_hours)

        ges = generate_result_dict(first_type, first_data_24_points)
        type_price = ges["table"]

        f_first_charge_info = ("23:00", "07:00", (type_price[str(first_type)].get("1", "--")), charge_status)
        f_first_discharge_info = (
            "09:00", "12:00", (type_price[str(first_type)].get("3", "--")), discharge_status)
        f_second_charge_info = (
            "12:00", "16:00", (type_price[str(first_type)].get("2", "--")), charge_status)
        f_second_discharge_info = (
            "16:00", "21:00", (type_price[str(first_type)].get("3", "--")), discharge_status)

        return update_strategy(ges, charge_discharge_times, first_type=first_type, second_type=None,
                               three_type=None,
                               four_type=None,
                               f_first_charge_info=f_first_charge_info,
                               f_first_discharge_info=f_first_discharge_info,
                               f_second_charge_info=f_second_charge_info,
                               f_second_discharge_info=f_second_discharge_info,
                               s_first_charge_info=None,
                               s_first_discharge_info=None,
                               s_second_charge_info=None,
                               s_second_discharge_info=None,
                               t_first_charge_info=None, t_first_discharge_info=None,
                               t_second_charge_info=None,
                               t_second_discharge_info=None,
                               r_first_charge_info=None, r_first_discharge_info=None,
                               r_second_charge_info=None,
                               r_second_discharge_info=None,
                               )

    if "福建" in region_name:
        first_type = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        first_type_lis = [low] * 8 + [normal] * 2 + [flat] * 1 + [peak] * 1 + [normal] * 3 + [flat] * 2 + [peak] * 1 + [
            flat] * 2 + [normal] * 1 + [flat] * 1 + [normal] * 2

        first_set_time = get_month_time(first_type)
        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        first_data_24_points = generate_points_data(first_type_lis, first_dic, data_24_hours)

        return generate_result_dict(first_type, first_data_24_points)

    if region_name == "云南省":
        first_type = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        first_type_lis = [low] * 7 + [normal] * 2 + [flat] * 3 + [normal] * 6 + [flat] * 5 + [low] * 1

        first_set_time = get_month_time(first_type)
        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        first_data_24_points = generate_points_data(first_type_lis, first_dic, data_24_hours)

        return generate_result_dict(first_type, first_data_24_points)

    if region_name == "北京市":
        charge_discharge_times = 2
        first_type = [7, 8]
        second_type = [1, 12]
        three_type = [2, 3, 4, 5, 6, 9, 10, 11]

        first_type_lis = [low] * 7 + [normal] * 3 + [flat] * 1 + [peak] * 2 + [normal] * 3 + [peak] * 1 + [
            flat] * 5 + [normal] * 1 + [low] * 1
        second_type_lis = [low] * 7 + [normal] * 3 + [flat] * 3 + [normal] * 4 + [flat] * 1 + [
            peak] * 3 + [flat] * 1 + [normal] * 1 + [low] * 1
        three_type_lis = [low] * 7 + [normal] * 3 + [flat] * 3 + [normal] * 4 + [flat] * 5 + [normal] * 1 + [low] * 1

        first_set_time = get_month_time(first_type)
        second_set_time = get_month_time(second_type)
        three_set_time = get_month_time(three_type)

        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        second_dic = get_trade_result_data(region_id, data_type_dic, second_set_time)
        three_dic = get_trade_result_data(region_id, data_type_dic, three_set_time)

        first_data_24_points = generate_points_data(first_type_lis, first_dic, data_24_hours)
        second_data_24_points = generate_points_data(second_type_lis, second_dic, data_24_hours)
        three_data_24_points = generate_points_data(three_type_lis, three_dic, data_24_hours)

        ges = generate_result_dict(first_type, first_data_24_points, second_type, second_data_24_points,
                                   three_type, three_data_24_points)

        type_price = ges["table"]

        f_first_charge_info = ("23:00", "07:00", (type_price[str(first_type)].get("1", "--")), charge_status)
        f_first_discharge_info = ("10:00", "13:00", (type_price[str(first_type)].get("3", "--")), discharge_status)
        f_second_charge_info = ("13:00", "16:00", (type_price[str(first_type)].get("2", "--")), charge_status)
        f_second_discharge_info = ("16:00", "20:00", (type_price[str(first_type)].get("4", "--")), discharge_status)

        s_first_charge_info = ("23:00", "07:00", (type_price[str(second_type)].get("1", "--")), charge_status)
        s_first_discharge_info = ("10:00", "13:00", (type_price[str(second_type)].get("3", "--")), discharge_status)
        s_second_charge_info = ("13:00", "17:00", (type_price[str(second_type)].get("2", "--")), charge_status)
        s_second_discharge_info = ("17:00", "20:00", (type_price[str(second_type)].get("3", "--")), discharge_status)

        t_first_charge_info = ("23:00", "07:00", (type_price[str(three_type)].get("1", "--")), charge_status)
        t_first_discharge_info = ("10:00", "13:00", (type_price[str(three_type)].get("3", "--")), discharge_status)
        t_second_charge_info = ("13:00", "17:00", (type_price[str(three_type)].get("2", "--")), charge_status)
        t_second_discharge_info = ("17:00", "20:00", (type_price[str(three_type)].get("4", "--")), discharge_status)

        return update_strategy(ges, charge_discharge_times, first_type=first_type, second_type=second_type,
                               three_type=three_type,
                               four_type=None,
                               f_first_charge_info=f_first_charge_info, f_first_discharge_info=f_first_discharge_info,
                               f_second_charge_info=f_second_charge_info,
                               f_second_discharge_info=f_second_discharge_info,
                               s_first_charge_info=s_first_charge_info, s_first_discharge_info=s_first_discharge_info,
                               s_second_charge_info=s_second_charge_info,
                               s_second_discharge_info=s_second_discharge_info,
                               t_first_charge_info=t_first_charge_info, t_first_discharge_info=t_first_discharge_info,
                               t_second_charge_info=t_second_charge_info,
                               t_second_discharge_info=t_second_discharge_info,
                               r_first_charge_info=None, r_first_discharge_info=None,
                               r_second_charge_info=None, r_second_discharge_info=None
                               )

    if region_name == "辽宁省":
        first_type = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        first_type_lis = [low] * 10 + [normal] * 5 + [flat] * 8 + [normal] * 11 + [peak] * 4 + [flat] * 4 + [
            normal] * 2 + [low] * 4

        first_set_time = get_month_time(first_type)
        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        first_data_24_points = generate_points_data(first_type_lis, first_dic, data_48_hours)

        return generate_result_dict(first_type, first_data_24_points)

    if region_name == "吉林省":
        charge_discharge_times = 2
        first_type = [1, 2, 7, 8, 11, 12]
        second_type = [3, 4, 5, 6, 9, 10]

        first_type_lis = [low] * 12 + [normal] * 6 + [flat] * 5 + [normal] * 8 + [flat] * 1 + [peak] * 4 + [
            flat] * 6 + [normal] * 4 + [low] * 2
        second_type_lis = [low] * 12 + [normal] * 6 + [flat] * 5 + [normal] * 8 + [flat] * 11 + [normal] * 4 + [low] * 2

        first_set_time = get_month_time(first_type)
        second_set_time = get_month_time(second_type)

        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        second_dic = get_trade_result_data(region_id, data_type_dic, second_set_time)

        first_data_48_points = generate_points_data(first_type_lis, first_dic, data_48_hours)
        second_data_48_points = generate_points_data(second_type_lis, second_dic, data_48_hours)

        ges = generate_result_dict(first_type, first_data_48_points, second_type, second_data_48_points)
        type_price = ges["table"]

        f_first_charge_info = ("23:00", "06:00", (type_price[str(first_type)].get("1", "--")), charge_status)
        f_first_discharge_info = ("09:00", "11:30", (type_price[str(first_type)].get("3", "--")), discharge_status)
        f_second_charge_info = ("11:30", "15:30", (type_price[str(first_type)].get("2", "--")), charge_status)
        f_second_discharge_info = ("15:30", "21:00", (type_price[str(first_type)].get("4", "--")), discharge_status)

        s_first_charge_info = ("23:00", "06:00", (type_price[str(second_type)].get("1", "--")), charge_status)
        s_first_discharge_info = ("09:00", "11:30", (type_price[str(second_type)].get("3", "--")), discharge_status)
        s_second_charge_info = ("11:30", "15:30", (type_price[str(second_type)].get("2", "--")), charge_status)
        s_second_discharge_info = ("15:30", "21:00", (type_price[str(second_type)].get("3", "--")), discharge_status)

        return update_strategy(ges, charge_discharge_times, first_type=first_type, second_type=second_type,
                               three_type=None,
                               four_type=None,
                               f_first_charge_info=f_first_charge_info, f_first_discharge_info=f_first_discharge_info,
                               f_second_charge_info=f_second_charge_info,
                               f_second_discharge_info=f_second_discharge_info,
                               s_first_charge_info=s_first_charge_info, s_first_discharge_info=s_first_discharge_info,
                               s_second_charge_info=s_second_charge_info,
                               s_second_discharge_info=s_second_discharge_info,
                               t_first_charge_info=None, t_first_discharge_info=None,
                               t_second_charge_info=None,
                               t_second_discharge_info=None,
                               r_first_charge_info=None, r_first_discharge_info=None,
                               r_second_charge_info=None, r_second_discharge_info=None, is_48=True
                               )

    if '蒙东' in region_name:
        first_type = [6, 7, 8]
        second_type = [1, 2, 3, 4, 5, 9, 10, 11, 12]

        first_type_lis = [low] * 10 + [normal] * 5 + [flat] * 8 + [normal] * 11 + [flat] * 2 + [peak] * 4 + [
            flat] * 2 + [normal] * 2 + [low] * 4
        second_type_lis = [low] * 10 + [normal] * 5 + [flat] * 8 + [normal] * 11 + [flat] * 8 + [normal] * 2 + [low] * 4

        first_set_time = get_month_time(first_type)
        second_set_time = get_month_time(second_type)

        first_dic = get_trade_result_data(region_id, data_type_dic, first_set_time)
        second_dic = get_trade_result_data(region_id, data_type_dic, second_set_time)

        first_data_48_points = generate_points_data(first_type_lis, first_dic, data_48_hours)
        second_data_48_points = generate_points_data(second_type_lis, second_dic, data_48_hours)

        return generate_result_dict(first_type, first_data_48_points, second_type, second_data_48_points)


def get_energy_benefit_data(user_id):
    compute_data = get_compute_info(user_id)
    if compute_data:
        energy_benefit_data = compute_data.get("energy_benefit_lis", None)
        if energy_benefit_data:
            return energy_benefit_data
        return []
