from django.urls import path
from rest_framework.routers import DefaultRouter

from service.iceval.views import GetRegionData, GetElectricityTypePricingData, GetElectricityGradeData, \
    AddElectricityInfo, SetEnergyStorageInfo, \
    GETCalculationInstallEnergyStorageUnitsInfo, GetTariffInfo, SetComputeEnergyStorageInfo

router = DefaultRouter()
urlpatterns = [
    path('get_region_data/', GetRegionData.as_view(), name='get_region_data'),
    path('get_ele_type_pricing_data/', GetElectricityTypePricingData.as_view(), name='get_ele_type_pricing_data'),
    path('get_ele_grade_data/', GetElectricityGradeData.as_view(), name='get_ele_grade_data'),
    path('add_electricity_info/', AddElectricityInfo.as_view(), name='add_electricity_info'),
    path('set_energy_storage_info/', SetEnergyStorageInfo.as_view(), name='set_energy_storage_info'),
    path('set_compute_energy_storage_info/', SetComputeEnergyStorageInfo.as_view(), name='get_compute_energy_storage_info'),
    path('get_calculation_install_e_sunits_info/', GETCalculationInstallEnergyStorageUnitsInfo.as_view(), name='get_calculation_install_energy_storage_units_info'),
    path('get_tariff_data/', GetTariffInfo.as_view(), name='get_tariff_data'),
]
