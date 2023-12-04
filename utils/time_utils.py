import datetime


def get_hours_num(ket_list):
    time1 = datetime.datetime.strptime(ket_list[0], "%H:%M")
    time2 = datetime.datetime.strptime(ket_list[1], "%H:%M")

    if time2 < time1:
        time2 += datetime.timedelta(days=1)
    hour_diff = (time2 - time1).seconds // 3600
    return int(hour_diff)


def get_month_time(month_lis):
    """
    params: month_lis: 月份列表
    return: 返回列表中最接近当前月份的月份
    """
    current_date = datetime.datetime.now()
    current_year_str = current_date.strftime("%Y")
    current_month = datetime.datetime.now().month

    nearest_month = min(month_lis, key=lambda x: abs(int(x) - current_month))
    set_time = f'{current_year_str}-{nearest_month}-01'
    return set_time


def get_now_time():
    current_date = datetime.datetime.now()
    current_year_str = current_date.strftime("%Y")
    current_month = datetime.datetime.now().month
    return f'{current_year_str}-{current_month}-01'


def extract_whole_hours_inclusive(time_lis):

    start = datetime.datetime.strptime(time_lis[0], '%H:%M')
    end = datetime.datetime.strptime(time_lis[1], '%H:%M')
    if end <= start:
        end += datetime.timedelta(days=1)

    current = start
    whole_hours = []
    while current <= end:
        if current.minute == 0:
            whole_hours.append(current.strftime('%H:%M'))
        current += datetime.timedelta(minutes=1)
    return whole_hours

