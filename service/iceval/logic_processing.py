import os

import pandas as pd

from service.iceval.iceval_db_api import get_electric_dic_for_region, \
    get_user_charge_discharge_times, get_electric_grade_dic_for_region, get_cooperate_type, \
    get_user_charge_discharge_days, add_compute_energy_storage, get_calculation_install_info


def get_electricity_data(region_id, region_name):
    electric_dict = get_electric_dic_for_region(region_id, region_name)
    return electric_dict

def get_electricity_grade_data(region_id, region_name, electric_type, electric_price_type):
    electric_grade_data = get_electric_grade_dic_for_region(region_id, region_name, electric_type, electric_price_type)
    return electric_grade_data


def get_energy_storage_discharging_info(user_id, is_show=False):
    # charging_mode = get_charging_mode(user_id) # todo 充放电模式
    charging_mode = 2
    installed_units_num = f'{2}（台）' if is_show else 2  # todo 选配台数
    battery_capacity = '100KW / 233KWh' if is_show else 233  # 储能系统电池容量
    installed_capacity = f'{100 * int(installed_units_num[0])} / {233 * int(installed_units_num[0])}KWh' if is_show else f'{100 * int(installed_units_num)} / {233 * int(installed_units_num)}KWh'  # 装机规模
    discharge_depth = '95%' if is_show else 0.95  # 放电深度
    charge_discharge_efficiency = '90%' if is_show else 0.90  # 充放电效率
    operation_duration = '15年' if is_show else 15
    charge_discharge_times = get_user_charge_discharge_times(user_id)  # todo 充放电次数
    cooperate_type, user_share_ratio = get_cooperate_type(user_id)   #用户分成比例
    project_total = round(battery_capacity * installed_units_num * 1500, 2)  # 项目总投资
    user_input = '0万元' if cooperate_type == 'emc' else f'{project_total}万元'  # 用户投入
    energy_storage_discharging_info = {"user_id": user_id, "battery_capacity": battery_capacity,
        "charge_discharge_times": charge_discharge_times,
        "status": "active", "installed_capacity": installed_capacity,
        "user_share_ratio": user_share_ratio, "installed_units_num": installed_units_num,
        "discharge_depth": discharge_depth, "charge_discharge_efficiency": charge_discharge_efficiency,
        "user_input": user_input, "charging_mode": charging_mode, "operation_duration": operation_duration
    }

    return energy_storage_discharging_info




def set_compute_energy_storage_info(user_id):
    compute_energy_storage_dic = {}
    all_compute_energy_storage_lis = []

    # 计算参数
    energy_storage_discharging_info = get_energy_storage_discharging_info(user_id)
    charge_discharge_times = energy_storage_discharging_info.get("charge_discharge_times", 0)  # 充放电次数
    battery_capacity = energy_storage_discharging_info.get("battery_capacity", 0)  # 储能系统电池容量
    installed_units_num = energy_storage_discharging_info.get("installed_units_num", 0)  # 选配台数
    discharge_depth = energy_storage_discharging_info.get("discharge_depth", 0)  # 放电深度
    charge_discharge_efficiency = energy_storage_discharging_info.get("charge_discharge_efficiency", 0)  # 充放电效率
    operation_duration = energy_storage_discharging_info.get("operation_duration", 0)  # 运行期限

    unit_construction_cost = 1500  # 单位建设成本
    discharge_days = int(get_user_charge_discharge_days(user_id))  # 年运行天数
    year_operation_days = round(discharge_days, 2)  # 年运行天数
    month_operation_days = round(discharge_days / 12, 2)  # 月运行天数
    battery_attenuation_rate = round(0.2 * year_operation_days * charge_discharge_times / 6000, 2)  # 电池衰减率
    between_three_years = round(unit_construction_cost * 0.09, 2)  # 前三年单位运维成本
    three_years_before = round(unit_construction_cost * 0.20, 2)  # 三年后单位运维成本
    single_discharge = round(battery_capacity * discharge_depth * charge_discharge_efficiency, 2)  # 单台设备单次放电量
    single_charge = round(battery_capacity * discharge_depth / charge_discharge_efficiency, 2)  # 单台设备单次充电量
    project_total = round(battery_capacity * installed_units_num * unit_construction_cost, 2)  # 项目总投资

    for i in range(1, operation_duration):
        compute_energy_storage_dic['year_initial_effective_capacity'] = battery_capacity * \
                                                                        (1 - i * battery_attenuation_rate)  # 年初有效容量
        compute_energy_storage_dic['year_discharge_capacity'] = single_discharge * (1 - i * battery_attenuation_rate) \
                                                                * charge_discharge_times * \
                                                                year_operation_days  # 年放电容量
        compute_energy_storage_dic['year_charge_capacity'] = single_charge * (1 - i * battery_attenuation_rate) \
                                                             * charge_discharge_times * year_operation_days  # 年充电量
        all_compute_energy_storage_lis.append(compute_energy_storage_dic)

    add_compute_energy_storage_info = {"unit_construction_cost": unit_construction_cost, "year_operation_days": year_operation_days,
                                       "month_operation_days": month_operation_days, "battery_attenuation_rate": battery_attenuation_rate, "between_three_years": between_three_years,
                                       "three_years_before": three_years_before, "single_discharge": single_discharge, "single_charge": single_charge, "project_total": project_total,
                                       "user_id": user_id, "status": "active","all_compute_energy_storage": all_compute_energy_storage_lis}
    add_compute_energy_storage(add_compute_energy_storage_info)

    return all_compute_energy_storage_lis


def get_electricity_dic(region_name, electric_type, electric_price_type, voltage_level):

    electricity_type_str = electric_price_type + electric_type
    file_name = "electricity_data.xlsx"
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
    file_path = project_root + "/electricity_xlsx/" + file_name
    df = pd.read_excel(file_path)
    filtered_data = df[(df['electricity_type_str'] == electricity_type_str) &
                       (df['region_name'] == region_name) &
                       (df['voltage_level'] == voltage_level)]
    electricity_dic = filtered_data.fillna('').to_dict(orient='records')
    return electricity_type_str, electricity_dic


def get_energy_storage_dic(mode_type):

    file_name = "energy.xlsx"
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
    file_path = project_root + "/electricity_xlsx/" + file_name
    df = pd.read_excel(file_path)
    selected_columns = ['time', f'mode_{mode_type}']
    subset_df = df[selected_columns]
    result_dict = {}
    for index, row in subset_df.iterrows():
        result_dict[round(row['time'])] = row[f'mode_{mode_type}']
    return result_dict



def get_tariff_data(region_id, region_name, electric_type, electric_price_type, voltage_level):
    electricity_type_str, electricity_dic = get_electricity_dic(region_name, electric_type, electric_price_type, voltage_level)
    if region_name == "浙江省":
        if electric_type == "大工业":
          pass
    else:
        pass
    electricity_dic = {"spikes": "spikes", "peaks": "peaks", "flat ": "flat", "through": "through"}
    return electricity_dic



def get_calculate_installed_capacity(user_id, region_name):
    electricity_info_dic = get_calculation_install_info(user_id, region_name)
    discharge_depth = 0.95  # 放电深度
    charge_discharge_efficiency =  0.90  # 充放电效率
    discharge_days = int(get_user_charge_discharge_days(user_id))  # 年运行天数
    year_operation_days = round(discharge_days, 2)  # 年运行天数
    month_operation_days = round(discharge_days / 12, 2)  # 月运行天数
    charge_discharge_times = get_user_charge_discharge_times(user_id)  # todo 充放电次数
    battery_attenuation_rate = round(0.2 * year_operation_days * charge_discharge_times / 6000, 2)  # 电池衰减率
    max_fluctuation_range = electricity_info_dic.get('max_fluctuation_range',0)
    min_fluctuation_range = electricity_info_dic.get('min_fluctuation_range',0)
    basic_battery_type = electricity_info_dic.get('basic_battery_type')
    if basic_battery_type == "容量电费":
        max_power = electricity_info_dic.get('transformers')
    else:
        max_power = electricity_info_dic.get('max_demand')



