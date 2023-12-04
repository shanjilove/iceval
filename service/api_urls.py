from django.urls import path
from rest_framework.routers import DefaultRouter

from service.iceval.views import GetRegionData, GetElectricityTypePricingData, GetElectricityGradeData, \
    AddElectricityInfo, GetEnergyStorageInfo, \
    SetTariffInfo, SetComputeEnergyStorageInfo, SetBenefitEvaluationInfo, GetStrategyInfo, GetEnergyBenefitInfo, \
    GetElectricityTypeData

router = DefaultRouter()
urlpatterns = [
    path('get_region_data/', GetRegionData.as_view(), name='get_region_data'),
    path('get_ele_type_pricing_data/', GetElectricityTypePricingData.as_view(), name='get_ele_type_pricing_data'),
    path('get_ele_type_data/', GetElectricityTypeData.as_view(), name='get_ele_type_data'),
    path('get_ele_grade_data/', GetElectricityGradeData.as_view(), name='get_ele_grade_data'),
    path('add_electricity_info/', AddElectricityInfo.as_view(), name='add_electricity_info'),
    path('get_energy_storage_info/', GetEnergyStorageInfo.as_view(), name='get_energy_storage_info'),
    path('set_compute_energy_storage_info/', SetComputeEnergyStorageInfo.as_view(),
         name='set_compute_energy_storage_info'),
    path('set_tariff_data/', SetTariffInfo.as_view(), name='set_tariff_data'),
    path('set_benefit_evakuation_info/', SetBenefitEvaluationInfo.as_view(), name='set_benefit_evaluation_info'),
    path('get_strategy_info/', GetStrategyInfo.as_view(), name='get_strategy_info'),
    path('get_energy_benefit_data/', GetEnergyBenefitInfo.as_view(), name='get_energy_benefit_data'),
]
