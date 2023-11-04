from iceval_app.iceval_models import Region, ElectricityInfo, ElectricTypePrice, \
    EnergyStorageDischaringInfo, ComputeEnergyStorageDisharingInfo


def get_region_data():
    region_lis = []
    region_data = Region.objects.all()
    for region in region_data:
        region_lis.append({"region_id": region.region_code, "region_name": region.region_name})
    return region_lis

def get_electric_dic_for_region(region_id, region_name):
    region_electric_dic = {}
    electric_data = ElectricTypePrice.objects.filter(region_id=region_id, region_name=region_name).all().first()
    if electric_data:
        region_electric_dic["electric_type"] = electric_data.electric_type.split('/') if region_id == '310000' else [electric_data.electric_type]
        region_electric_dic["electric_price_type"] = electric_data.electric_price_type.split('/')
        return [region_electric_dic]
    return [{}]


def get_electric_grade_dic_for_region(region_id, region_name, electric_type, electric_price_type):
    region_electric_grade_dic = {}
    electric_grade_data = ElectricTypePrice.objects.filter(region_id=region_id, region_name=region_name).all().first()
    if electric_grade_data:
        if  region_id == '310000':
            if electric_type == '一般工商业':
                if electric_price_type == '单一制':
                    electric_grade = electric_grade_data.voltage_level.split('&')[0].split('/')[0].split(',')
                if electric_price_type == '两部制':
                    electric_grade = electric_grade_data.voltage_level.split('&')[0].split('/')[1].split(',')
            else:
                electric_grade = electric_grade_data.voltage_level.split('&')[1].split(',')
        elif region_id == '330000':
            if electric_price_type == '单一制（一般工商业用电）':
                electric_grade = electric_grade_data.voltage_level.split('&')[1].split(',')
            if electric_price_type == '两部制（大工业用电）':
                electric_grade = electric_grade_data.voltage_level.split('&')[0].split('/')[0].split(',')
            if electric_price_type == '两部制（一般工商业用电）':
                electric_grade = electric_grade_data.voltage_level.split('&')[0].split('/')[1].split(',')
        else:
            if electric_price_type == '单一制' or electric_price_type == '单一制（一般工商业用电）' or electric_price_type == '100千伏安以下（单一制，含行政事业单位办公场所用电）':
                electric_grade = electric_grade_data.voltage_level.split('/')[0].split(',')
            if electric_price_type == '两部制' or electric_price_type == '两部制（大工业用电）' or electric_price_type == '100千伏安及以上（两部制）':
                electric_grade = electric_grade_data.voltage_level.split('/')[1].split(',')

        region_electric_grade_dic['electric_grade'] = electric_grade
        return region_electric_grade_dic
    return {"electric_grade": []}


def add_electricity_info(user_id, transformers, basic_battery_type, max_demand, year_operation_days, region_id, region_name,
                         electric_type, electric_price_type, voltage_level, translators, power_curve_type, max_fluctuation_range, min_fluctuation_range, cooperate_type):
    charge_discharge_times = ElectricTypePrice.objects.filter(region_id=region_id, region_name=region_name).first().charge_discharge_times
    create_electric_info = ElectricityInfo.objects.create(user_id=user_id, transformers=transformers,
                                                          basic_battery_type=basic_battery_type, region_name=region_name,
                                                          max_demand=max_demand, year_operation_days=year_operation_days,
                                                          status='active',region_id=region_id, electric_type=electric_type,
                                                          electric_price_type=electric_price_type, voltage_level=voltage_level,
                                                          charge_discharge_times=charge_discharge_times, translators=translators,
                                                          power_curve_type=power_curve_type, max_fluctuation_range=max_fluctuation_range,
                                                          min_fluctuation_range=min_fluctuation_range, cooperate_type=cooperate_type)
    if create_electric_info:
        return True
    return False

def get_user_charge_discharge_times(user_id):
    charge_discharge_times = ElectricityInfo.objects.filter(user_id=user_id, status='active').order_by("-created_at").first().charge_discharge_times
    print(charge_discharge_times)
    if charge_discharge_times is not None:
        return charge_discharge_times
    return 0

def add_energy_storage_discharging_info(energy_storage_discharging_info):
    energy_storage_discharging_info = EnergyStorageDischaringInfo(**energy_storage_discharging_info)
    energy_storage_discharging_info.save()
    if energy_storage_discharging_info:
        return True
    return False


def add_compute_energy_storage(compute_energy_storage_info):
    compute_energy_storage_info = ComputeEnergyStorageDisharingInfo(**compute_energy_storage_info)
    compute_energy_storage_info.save()
    if compute_energy_storage_info:
        return True
    return False


def get_cooperate_type(user_id):
    cooperate_type = ElectricityInfo.objects.filter(user_id=user_id, status='active').order_by("-created_at").first().cooperate_type
    if cooperate_type is not None:
        return cooperate_type, 1 if cooperate_type == "emc" else 0.1
    return 0

def get_user_charge_discharge_days(user_id):
    charge_discharge_days = ElectricityInfo.objects.filter(user_id=user_id, status='active').order_by("-created_at").first().year_operation_days
    if charge_discharge_days is not None:
        return charge_discharge_days
    return 0

def get_charging_mode(user_id):
    region_name = ElectricityInfo.objects.filter(user_id=user_id, status='active').order_by("-created_at").first().region_name
    if region_name is not None:
        charging_mode = Region.objects.filter(region_name=region_name).first().charging_mode
        return charging_mode
    return None

def get_energy_storage_discharging_info_for_show(user_id):
    energy_storage_discharging_data = EnergyStorageDischaringInfo.objects.filter(user_id=user_id, status='active').order_by("-created_at").first()
    return energy_storage_discharging_data

def get_calculation_install_info(user_id, region_name):
    electricity_data = ElectricityInfo.objects.filter(user_id=user_id, region_name=region_name, status='active').order_by("-created_at").first()
    if electricity_data:
        return electricity_data
    return []