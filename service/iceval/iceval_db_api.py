from iceval_app.iceval_models import Region, ElectricityInfo, ElectricTypePrice, \
    EnergyStorageDischaringInfo, ComputeEnergyStorageDisharingInfo, BenefitEvaluationInfo


def get_region_data():
    region_list = []
    region_data = Region.objects.order_by('id')
    for region in region_data:
        region_list.append({"region_id": region.region_code, "region_name": region.region_name})
    sorted_region_list = sorted(region_list, key=lambda x: x["region_name"] != "江苏省")
    return sorted_region_list


def get_electricity_type_dic(region_id, region_name, electricity_type):
    region_electricity_type_dic = {}
    electricity_data = ElectricTypePrice.objects.filter(region_id=region_id, region_name=region_name).all().first()
    if electricity_data:
        if region_id in ['310000', '330000'] and electricity_type == '大工业':
            region_electricity_type_dic["electric_price_type"] = [electricity_data.electric_price_type.split('/')[1]]
            return [region_electricity_type_dic]
        else:
            region_electricity_type_dic["electric_price_type"] = [electricity_data.electric_price_type.split('/')[1],
                                                                  electricity_data.electric_price_type.split('/')[0]]
            return [region_electricity_type_dic]
    return [{}]


def get_electric_dic_for_region(region_id, region_name):
    region_electric_dic = {}
    electric_data = ElectricTypePrice.objects.filter(region_id=region_id, region_name=region_name).all().first()
    if electric_data:
        region_electric_dic["electric_type"] = [electric_data.electric_type.split('/')[1],
                                                electric_data.electric_type.split('/')[0]] if region_id in ['310000',
                                                                                                            '330000'] else [
            electric_data.electric_type]
        return [region_electric_dic]
    return [{}]


def get_electric_grade_dic_for_region(region_id, region_name, electric_type, electric_price_type):
    region_electric_grade_dic = {}
    electric_grade_data = ElectricTypePrice.objects.filter(region_id=region_id, region_name=region_name).all().first()
    if electric_grade_data:

        if region_id == '310000':
            if electric_type == '一般工商业':
                if electric_price_type == '单一制':
                    electric_grade = electric_grade_data.voltage_level.split('&')[0].split('/')[0].split(',')
                    region_electric_grade_dic['electric_grade'] = electric_grade
                if electric_price_type == '两部制':
                    electric_grade = electric_grade_data.voltage_level.split('&')[0].split('/')[1].split(',')
                    region_electric_grade_dic['electric_grade'] = electric_grade
            else:
                if electric_price_type == '两部制':
                    electric_grade = electric_grade_data.voltage_level.split('&')[1].split(',')
                    region_electric_grade_dic['electric_grade'] = electric_grade
                else:
                    electric_grade = ''
                    region_electric_grade_dic['electric_grade'] = electric_grade
        elif region_id == '330000':
            if electric_type == '一般工商业':
                if electric_price_type == '单一制':
                    electric_grade = electric_grade_data.voltage_level.split('&')[0].split('/')[0].split(',')
                    region_electric_grade_dic['electric_grade'] = electric_grade
                if electric_price_type == '两部制':
                    electric_grade = electric_grade_data.voltage_level.split('&')[0].split('/')[1].split(',')
                    region_electric_grade_dic['electric_grade'] = electric_grade
            if electric_type == '大工业':
                if electric_price_type == '两部制':
                    electric_grade = electric_grade_data.voltage_level.split('&')[1].split('/')[0].split(',')
                    region_electric_grade_dic['electric_grade'] = electric_grade
                else:
                    electric_grade = ''
                    region_electric_grade_dic['electric_grade'] = electric_grade
        else:
            if electric_type == '工商业':
                if electric_price_type == '单一制':
                    electric_grade = electric_grade_data.voltage_level.split('/')[0].split(',')
                    region_electric_grade_dic['electric_grade'] = electric_grade
                if electric_price_type == '两部制':
                    electric_grade = electric_grade_data.voltage_level.split('/')[1].split(',')
                    region_electric_grade_dic['electric_grade'] = electric_grade
        return region_electric_grade_dic
    return []


def add_electricity_info(user_id, transformers, basic_battery_type, max_demand, year_operation_days, region_id,
                         region_name,
                         electric_type, electric_price_type, voltage_level, tariff_data, translators, power_curve_type,
                         max_fluctuation_range, min_fluctuation_range, cooperate_type):
    update_status = ElectricityInfo.objects.filter(user_id=user_id, status='active').update(status='inactive')
    if update_status:
        create_electric_info = ElectricityInfo.objects.create(user_id=user_id, transformers=transformers,
                                                              tariff_data=tariff_data,
                                                              basic_battery_type=basic_battery_type,
                                                              region_name=region_name,
                                                              max_demand=max_demand,
                                                              year_operation_days=year_operation_days,
                                                              status='active', region_id=region_id,
                                                              electric_type=electric_type,
                                                              electric_price_type=electric_price_type,
                                                              voltage_level=voltage_level,
                                                              translators=translators,
                                                              power_curve_type=power_curve_type,
                                                              max_fluctuation_range=max_fluctuation_range,
                                                              min_fluctuation_range=min_fluctuation_range,
                                                              cooperate_type=cooperate_type)
        if create_electric_info:
            return True
    return False


def add_energy_storage_discharging_info(energy_storage_discharging_info):
    update_status = EnergyStorageDischaringInfo.objects.filter(user_id=energy_storage_discharging_info["user_id"],
                                                               status='active').update(status='inactive')
    if update_status:
        energy_storage_discharging_info = EnergyStorageDischaringInfo(**energy_storage_discharging_info)
        energy_storage_discharging_info.save()
        if energy_storage_discharging_info:
            return True
    return False


def add_compute_energy_storage(compute_energy_storage_info):
    active_storage = ComputeEnergyStorageDisharingInfo.objects.select_for_update().filter(
        user_id=compute_energy_storage_info["user_id"],
        status='active'
    )
    if active_storage.exists():
        active_storage.update(status='inactive')
        new_storage = ComputeEnergyStorageDisharingInfo(**compute_energy_storage_info)
        new_storage.save()
        return True
    return False


def get_region_name(user_id):
    region_name = ElectricityInfo.objects.filter(user_id=user_id, status='active').order_by(
        "-created_at").first().region_name
    if region_name is not None:
        return region_name
    return None


def get_cooperate_type(user_id):
    cooperate_type = ElectricityInfo.objects.filter(user_id=user_id, status='active').order_by(
        "-created_at").first().cooperate_type
    if cooperate_type is not None:
        return cooperate_type, 0.15 if cooperate_type == "EMC" else 1
    return 0


def get_user_charge_discharge_days(user_id):
    charge_discharge_days = ElectricityInfo.objects.filter(user_id=user_id, status='active').order_by(
        "-created_at").first().year_operation_days
    if charge_discharge_days is not None:
        return charge_discharge_days
    return 0


def get_charging_mode(user_id):
    region_name = ElectricityInfo.objects.filter(user_id=user_id, status='active').order_by(
        "-created_at").first().region_name
    if region_name is not None:
        charging_mode = Region.objects.filter(region_name=region_name).first().charging_mode
        return charging_mode
    return None


def get_energy_storage_discharging_info_for_show(user_id):
    energy_storage_discharging_data = EnergyStorageDischaringInfo.objects.filter(user_id=user_id,
                                                                                 status='active').order_by(
        "-created_at").first()
    return energy_storage_discharging_data


def get_calculation_install_info(user_id):
    region_name = get_region_name(user_id)
    electricity_data = ElectricityInfo.objects.filter(user_id=user_id, region_name=region_name,
                                                      status='active').order_by("-created_at").first()
    if electricity_data:
        return electricity_data
    return []


def get_compute_info(user_id):
    compute_dic = {}
    compute_data = ComputeEnergyStorageDisharingInfo.objects.filter(user_id=user_id, status='active').order_by(
        '-created_at').first()
    if compute_data:
        compute_dic["user_id"] = compute_data.user_id
        compute_dic["project_total"] = compute_data.project_total
        compute_dic["user_project_revenue_total"] = compute_data.user_project_revenue_total
        compute_dic["bo_project_revenue_total"] = compute_data.bo_project_revenue_total
        compute_dic["all_compute_energy_storage"] = compute_data.all_compute_energy_storage
        compute_dic["energy_benefit_lis"] = compute_data.energy_benefit_lis
        compute_dic["user_input"] = compute_data.user_input
        return compute_dic
    return []


def add_benefit_evaluation_info(benefit_evaluation_data):
    update_status = BenefitEvaluationInfo.objects.filter(user_id=benefit_evaluation_data["user_id"],
                                                         status='active').update(status='inactive')
    if update_status:
        benefit_evaluation_datas = BenefitEvaluationInfo(**benefit_evaluation_data)
        benefit_evaluation_datas.save()
        if benefit_evaluation_datas:
            return True
    return False


def get_trade_dic_for_db(region_id):
    trade_dic = {}
    trade_data = ElectricTypePrice.objects.filter(region_id=region_id).all().first()
    if trade_data:
        trade_dic["peak"] = trade_data.peak
        trade_dic["flat"] = trade_data.flat
        trade_dic["normal"] = trade_data.normal
        trade_dic["valley"] = trade_data.valley
        trade_dic["low"] = trade_data.low
        return trade_dic
    return []
