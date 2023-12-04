import logging
import os
import pandas as pd


def get_file_path(file_name):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    excel_file_path = os.path.join(script_dir, '..', 'electricity_file', file_name)
    df = pd.read_excel(excel_file_path)
    return df


def get_voltage_level_lis(region_name, target_region, electric_type, electric_price_type, electric_grade_data):
    """
    获取指定省份的电压等级的平时段电价ID
    """
    file_name = "electricity_data.xlsx"
    df = get_file_path(file_name)
    result_data = []

    for voltage_level in electric_grade_data["electric_grade"]:
        electricity_type_str = electric_price_type + f'（{electric_type}）' + voltage_level
        if region_name == '上海市' or region_name == '浙江省':
            filtered_data = df.loc[
                ((df['electricity_type_str'] == electricity_type_str) &
                 (df['region_name'] == target_region) &
                 (df['voltage_level'] == voltage_level) &
                 (df['data_type'].isin(['电度电价']))),
                ['data_type_id', 'voltage_level']
            ]
        else:
            filtered_data = df.loc[
                ((df['electricity_type_str'] == electric_price_type) &
                 (df['region_name'] == target_region) &
                 (df['voltage_level'] == voltage_level) &
                 (df['data_type'].isin(['电度电价']))),
                ['data_type_id', 'voltage_level']
            ]
        result_data.append(filtered_data)

    if result_data:
        combined_data = pd.concat(result_data, ignore_index=True)
    else:
        combined_data = pd.DataFrame()
    return combined_data


def get_region_ele_prices(region_name, electricity_type_str, voltage_level):
    """
    获取所有可做储能省份固定电价
    """
    file_name = "electricity_price.xlsx"
    df = get_file_path(file_name)

    filtered_data = df[(df['electricity_type_str'] == electricity_type_str) & (df['region_name'] == region_name) & (
            df['voltage_level'] == voltage_level)]
    columns_to_exclude = ['peak', 'flat', 'normal', 'low', 'valley']
    if filtered_data.empty:
        columns_to_exclude_dict = {col: 0 for col in columns_to_exclude}
    else:
        filtered_data = filtered_data.fillna(0)
        columns_to_exclude_dict = {col: filtered_data[col].values[0] for col in columns_to_exclude}
    return columns_to_exclude_dict


def get_electricity_dic(region_name, region_name_excel, electric_type, electric_price_type, voltage_level):
    """
    获取电价ID
    """

    file_name = "electricity_data.xlsx"
    df = get_file_path(file_name)
    electricity_type_str = electric_price_type + f'（{electric_type}）' + voltage_level
    electricity_str = electric_price_type + '工商业'
    data_type_dic = {
        "peak_type_id": 0,
        "flat_type_id": 0,
        "normal_type_id": 0,
        "valley_type_id": 0,
        "low_type_id": 0
    }

    if region_name == '上海市' or region_name == '浙江省':
        filtered_data = df[(df['electricity_type_str'] == electricity_type_str) &
                           (df['region_name'] == region_name_excel) &
                           (df['voltage_level'] == voltage_level) &
                           (df['data_type'].isin(['尖峰电价', '高峰电价', '电度电价', '深谷电价', '低谷电价']))]
        electricity_str = electric_price_type + electric_type
    elif region_name == '山东省':
        filtered_data1 = df[(df['electricity_type_str'] == electric_price_type) &
                            (df['region_name'] == region_name_excel) &
                            (df['voltage_level'] == voltage_level) &
                            (df['data_type'].isin(['尖峰电价', '高峰电价', '电度电价', '低谷电价']))]

        filtered_data2 = df[(df['electricity_type_str'] == electric_price_type) &
                            (df['region_name'] == '山东') &
                            (df['voltage_level'] == voltage_level) &
                            (df['data_type'] == '深谷电价')]

        filtered_data = pd.concat([filtered_data1, filtered_data2])
    else:
        filtered_data = df[(df['electricity_type_str'] == electric_price_type) &
                           (df['region_name'] == region_name_excel) &
                           (df['voltage_level'] == voltage_level) &
                           (df['data_type'].isin(['尖峰电价', '高峰电价', '电度电价', '深谷电价', '低谷电价']))]
    data_type_map = {
        '尖峰电价': 'peak_type_id',
        '高峰电价': 'flat_type_id',
        '电度电价': 'normal_type_id',
        '深谷电价': 'valley_type_id',
        '低谷电价': 'low_type_id'
    }
    for data_type, column_name in data_type_map.items():
        value = filtered_data.loc[filtered_data['data_type'] == data_type, 'data_type_id']
        if not value.empty:
            data_type_dic[column_name] = round(value.iloc[0])

    logging.info(f"{region_name}的电价ID是：{data_type_dic}")
    return electricity_str, data_type_dic


def get_energy_storage_dic(mode_type):
    """
    获取储能模式对应图表数据
    """
    file_name = "energy.xlsx"
    df = get_file_path(file_name)
    selected_columns = ['time', f'mode_{mode_type}']
    subset_df = df[selected_columns]
    energy_storage_dict = {}
    for index, row in subset_df.iterrows():
        energy_storage_dict[row['time'].strftime('%H:%M')] = row[f'mode_{mode_type}']
    return energy_storage_dict
