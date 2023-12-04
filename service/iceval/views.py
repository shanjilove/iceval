from django.db import transaction
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from service.iceval.iceval_db_api import get_region_data, add_electricity_info, add_energy_storage_discharging_info
from service.iceval.logic_processing import get_electricity_data, \
    get_electricity_grade_data, \
    get_energy_storage_discharging_info, set_compute_energy_storage_info, set_benefit_evaluation, \
    get_trade_ep_data_month_data, get_strategy_info, get_energy_benefit_data, get_electricity_type_data
from utils.custom_utils import is_have_money
from utils.logger_utils import handler_exception


class GetRegionData(APIView):
    """
        获取省份信息
    """

    @handler_exception()
    def get(self, request):
        region_data = get_region_data()
        return Response({"data": region_data, "status": status.HTTP_200_OK, "msg": "success"})


class GetElectricityTypeData(APIView):
    """
        获取身份用电类型
    """

    @handler_exception()
    def get(self, request):
        region_id = request.query_params.get('region_id')
        region_name = request.query_params.get('region_name')
        electricity_type = request.query_params.get('electricity_type')
        if region_id is None or region_name is None and electricity_type is None:
            return Response({"msg": "Invalid Params", "status": status.HTTP_400_BAD_REQUEST, "data": []})

        region_electricity_data = get_electricity_type_data(region_id, region_name, electricity_type)
        if not is_have_money(region_name):
            return Response(
                {
                    "msg": f"当前{region_name}工商业用电峰谷电价差较小，暂不适宜工商业配储，让我们一起静候佳音，期待新电价政策的到来。",
                    "status": status.HTTP_200_OK, "data": region_electricity_data,
                    "is_have_money": False})
        return Response(
            {"data": region_electricity_data, "status": status.HTTP_200_OK, "msg": "success", "is_have_money": True})


class GetElectricityTypePricingData(APIView):
    """
        获取身份用电类型和计价方式
    """

    @handler_exception()
    def get(self, request):
        region_id = request.query_params.get('region_id')
        region_name = request.query_params.get('region_name')
        if region_id is None or region_name is None:
            return Response({"msg": "Invalid region_id", "status": status.HTTP_400_BAD_REQUEST, "data": []})

        region_electricity_data = get_electricity_data(region_id, region_name)

        return Response(
            {"data": region_electricity_data, "status": status.HTTP_200_OK, "msg": "success"})


class GetElectricityGradeData(APIView):
    @handler_exception()
    def get(self, request):
        region_id = request.query_params.get('region_id')
        region_name = request.query_params.get('region_name')
        electric_type = request.query_params.get('electric_type')
        electric_price_type = request.query_params.get('electric_price_type')
        if region_id is None or electric_type is None or electric_price_type is None or region_name is None:
            return Response({"msg": "Invalid Params", "status": status.HTTP_400_BAD_REQUEST, "data": []})
        region_electricity_data = get_electricity_grade_data(region_id, region_name, electric_type, electric_price_type)
        return Response({"data": region_electricity_data, "status": status.HTTP_200_OK, "msg": "success"})


class SetTariffInfo(APIView):
    """
        获取分时电价数据
    """
    handler_exception()

    def post(self, request):
        with transaction.atomic():
            region_id = request.data.get("region_id")
            region_name = request.data.get("region_name")
            electric_type = request.data.get("electric_type")
            electric_price_type = request.data.get("electric_price_type")
            voltage_level = request.data.get("voltage_level")
            if voltage_level == "":
                return Response({"msg": "success", "status": status.HTTP_200_OK, "data": []})
            tariff_data = get_trade_ep_data_month_data(region_id, region_name, electric_type, electric_price_type,
                                                       voltage_level)
            return Response({"data": tariff_data, "status": status.HTTP_200_OK, "msg": "success"})


class AddElectricityInfo(APIView):
    """
        添加用户输入装置信息
    """

    @handler_exception()
    def post(self, request):
        with transaction.atomic():
            user_id = request.data.get("user_id")
            region_id = request.data.get("region_id")
            region_name = request.data.get("region_name")
            electric_type = request.data.get("electric_type")
            electric_price_type = request.data.get("electric_price_type")
            voltage_level = request.data.get("voltage_level")
            tariff_data = request.data.get("tariff_data")
            translators = request.data.get("translators")
            transformers = request.data.get("transformers")
            basic_battery_type = request.data.get("basic_battery_type")
            max_demand = request.data.get("max_demand")
            year_operation_days = request.data.get("year_operation_days")
            power_curve_type = request.data.get("power_curve_type")
            max_fluctuation_range = request.data.get("max_fluctuation_range")
            min_fluctuation_range = request.data.get("min_fluctuation_range")
            cooperate_type = request.data.get("cooperate_type")

            if user_id is None or transformers is None or year_operation_days is None or max_demand is None or basic_battery_type is None \
                    or min_fluctuation_range is None or transformers is None or year_operation_days is None \
                    or translators is None or power_curve_type is None or min_fluctuation_range is None or max_fluctuation_range is None or tariff_data is None:
                return Response({"msg": "Invalid parameters", "status": status.HTTP_401_UNAUTHORIZED})
            add_electricity_info(str(user_id), int(transformers), str(basic_battery_type), int(max_demand),
                                 str(year_operation_days), str(region_id), str(region_name),
                                 electric_type, electric_price_type, voltage_level, tariff_data, int(translators),
                                 str(power_curve_type), int(max_fluctuation_range), int(min_fluctuation_range),
                                 str(cooperate_type))
            energy_storage_discharging_info = get_energy_storage_discharging_info(user_id)
            add_energy_storage_discharging_info(energy_storage_discharging_info)
            if add_electricity_info and add_energy_storage_discharging_info:
                return Response({"msg": "success", "status": status.HTTP_200_OK})
            return Response({"msg": "failed", "status": status.HTTP_500_INTERNAL_SERVER_ERROR})


class GetEnergyStorageInfo(APIView):
    """
        添加储能信息
    """

    @handler_exception()
    def get(self, request):
        user_id = request.query_params.get("user_id")
        if user_id is None:
            return Response({"msg": "Invalid parameters", "status": status.HTTP_400_BAD_REQUEST})
        energy_storage_discharging_info = get_energy_storage_discharging_info(user_id, is_show=True)
        return Response({"msg": "success", "data": energy_storage_discharging_info, "status": status.HTTP_200_OK,
                         "user_id": user_id})


class GetStrategyInfo(APIView):
    """
     获取策略信息
    """

    @handler_exception()
    def get(self, request):
        user_id = request.query_params.get("user_id")
        if user_id is None:
            return Response({"msg": "Invalid parameters", "status": status.HTTP_400_BAD_REQUEST})
        strategy_info = get_strategy_info(user_id)
        return Response({"msg": "success", "data": strategy_info, "status": status.HTTP_200_OK, "user_id": user_id})


class SetComputeEnergyStorageInfo(APIView):
    """
        获取计算储能信息
    """

    @handler_exception()
    def post(self, request):
        with transaction.atomic():
            user_id = request.data.get("user_id")
            if user_id is None:
                return Response({"msg": "Invalid parameters", "status": status.HTTP_400_BAD_REQUEST})
            compute_energy_storage_info = set_compute_energy_storage_info(user_id)
            return Response({"msg": "success", "status": status.HTTP_200_OK, "data": compute_energy_storage_info,
                            "user_id": user_id})


class SetBenefitEvaluationInfo(APIView):
    """
        获取收益评价信息
    """

    @handler_exception()
    def post(self, request):
        with transaction.atomic():
            user_id = request.data.get("user_id")
            if user_id is None:
                return Response({"msg": "Invalid parameters", "status": status.HTTP_400_BAD_REQUEST})
            compute_energy_storage_info = set_benefit_evaluation(user_id)
            return Response({"msg": "success", "status": status.HTTP_200_OK, "data": compute_energy_storage_info})


class GetEnergyBenefitInfo(APIView):
    """
        获取收益评价信息
    """

    @handler_exception()
    def get(self, request):
        user_id = request.query_params.get("user_id")
        if user_id is None:
            return Response({"msg": "Invalid parameters", "status": status.HTTP_400_BAD_REQUEST})
        energy_benefit_info = get_energy_benefit_data(user_id)
        return Response({"msg": "success", "status": status.HTTP_200_OK, "data": energy_benefit_info})
