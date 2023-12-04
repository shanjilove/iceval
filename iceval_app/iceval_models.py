from django.db import models


# Create your models here.
class Region(models.Model):
    id = models.AutoField(primary_key=True)
    data_source = models.CharField(max_length=10, verbose_name="数据来源id", null=True)
    region_code = models.CharField(max_length=10, verbose_name="区域编码")
    region_name = models.CharField(max_length=50, verbose_name="区域名称")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'region'
        verbose_name = "区域信息"
        verbose_name_plural = verbose_name


class ElectricTypePrice(models.Model):
    id = models.AutoField(primary_key=True)
    region_id = models.CharField(max_length=50, verbose_name="省份id")
    region_name = models.CharField(max_length=50, verbose_name="区域名称", null=True)
    electric_type = models.CharField(max_length=50, verbose_name="用电类型")
    electric_price_type = models.CharField(max_length=50, verbose_name="计价方式")
    voltage_level = models.CharField(max_length=225, verbose_name="电压等级")
    charge_discharge_times = models.IntegerField(verbose_name="充放电次数")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'electric_type_price'
        verbose_name = "电价信息"
        verbose_name_plural = verbose_name


class ElectricityInfo(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.CharField(max_length=50, verbose_name="用户id")
    region_id = models.CharField(max_length=10, verbose_name="省份id")
    region_name = models.CharField(max_length=50, verbose_name="区域名称")
    electric_type = models.CharField(max_length=50, verbose_name="用电类型")
    electric_price_type = models.CharField(max_length=20, verbose_name="计价方式")
    voltage_level = models.CharField(max_length=225, verbose_name="电压等级")
    tariff_data = models.JSONField(verbose_name="分时电价数据")
    transformers = models.BigIntegerField(verbose_name="变压器容量")
    translators = models.BigIntegerField(verbose_name="变压器数量")
    basic_battery_type = models.CharField(max_length=20, verbose_name="基础电费类型")
    max_demand = models.BigIntegerField(verbose_name="最大需量")
    year_operation_days = models.CharField(max_length=10, verbose_name="年运行天数")
    status = models.CharField(max_length=10, verbose_name="状态")
    power_curve_type = models.CharField(max_length=30, verbose_name="功率曲线类型")
    max_fluctuation_range = models.BigIntegerField(verbose_name="最大负荷")
    min_fluctuation_range = models.BigIntegerField(verbose_name="最小负荷")
    cooperate_type = models.CharField(max_length=30, verbose_name="合作类型")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'electricity_info'
        verbose_name = "企业用电信息记录"
        verbose_name_plural = verbose_name


class EnergyStorageDischaringInfo(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.CharField(max_length=30, verbose_name="用户id")
    user_input = models.BigIntegerField(verbose_name="用户投入")
    user_share_ratio = models.BigIntegerField(verbose_name="用户分成比例")
    battery_capacity = models.BigIntegerField(verbose_name="储能系统电池容量")
    charge_discharge_times = models.BigIntegerField(verbose_name="充放电次数")
    status = models.CharField(max_length=10, verbose_name="状态")
    operation_duration = models.BigIntegerField(verbose_name="运行期限")
    installed_capacity = models.CharField(max_length=30, verbose_name="装机规模")
    installed_units_num = models.BigIntegerField(verbose_name="选配台数")
    discharge_depth = models.BigIntegerField(verbose_name="放电深度")
    charge_discharge_efficiency = models.BigIntegerField(verbose_name="充放电效率")
    charging_mode = models.CharField(max_length=20, verbose_name="充放电模式")
    cooperate_type = models.CharField(max_length=30, verbose_name="合作类型")
    project_total = models.BigIntegerField(verbose_name="项目总投资")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'energy_storage_discharing_info'
        verbose_name = "储能推荐充放电策略"
        verbose_name_plural = verbose_name


class ComputeEnergyStorageDisharingInfo(models.Model):
    id = models.AutoField(primary_key=True)
    user_input = models.BigIntegerField(verbose_name="用户投入")
    user_id = models.CharField(max_length=50, verbose_name="用户id")
    battery_attenuation_rate = models.CharField(max_length=20, verbose_name="电池衰减率")
    year_operation_days = models.BigIntegerField(verbose_name="年运行天数")
    month_operation_days = models.BigIntegerField(verbose_name="月运行天数")
    unit_construction_cost = models.BigIntegerField(verbose_name="单位建设成本")
    between_three_years = models.BigIntegerField(verbose_name="前三年单位运维成本")
    three_years_before = models.BigIntegerField(verbose_name="三年后单位运维成本")
    single_discharge = models.BigIntegerField(verbose_name="单台设备单次放电量")
    single_charge = models.BigIntegerField(verbose_name="单台设备单次充电量")
    project_total = models.BigIntegerField(verbose_name="项目总投资")
    status = models.CharField(max_length=10, verbose_name="状态")
    all_compute_energy_storage = models.JSONField(verbose_name="计算储能信息")
    energy_benefit_lis = models.JSONField(verbose_name="累计收益评价信息")
    user_project_revenue_total = models.BigIntegerField(verbose_name="用户项目收益总额")
    bo_project_revenue_total = models.BigIntegerField(verbose_name="bo项目收益总额")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'compute_energy_storage_disharing_info'
        verbose_name = "计算字段储能推荐充放电策略"
        verbose_name_plural = verbose_name


class BenefitEvaluationInfo(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.CharField(max_length=50, verbose_name="用户id")
    first_year_total_revenue = models.CharField(max_length=20, verbose_name="第一年总收益")
    first_year_bo_total_revenue = models.CharField(max_length=20, verbose_name="第一年总成本")
    investor_cost_recovery_period = models.CharField(max_length=20, verbose_name="项目投资回收期")
    project_internal_rate = models.CharField(max_length=20, verbose_name="项目收益")
    user_project_revenue_total = models.CharField(max_length=20, verbose_name="用户项目收益总额")
    bo_accumulate_revenue = models.CharField(max_length=20, verbose_name="bo累计收益")
    project_total = models.CharField(max_length=20, verbose_name="项目总投资")
    user_input = models.CharField(max_length=20, verbose_name="用户投入")
    accumulate_revenue = models.CharField(max_length=20, verbose_name="累计收益")
    project_npv = models.CharField(max_length=20, verbose_name="项目净现值")
    status = models.CharField(max_length=20, verbose_name="状态")

    class Meta:
        db_table = 'benefit_evaluation_info'
        verbose_name = "用户收益评价"
        verbose_name_plural = verbose_name
