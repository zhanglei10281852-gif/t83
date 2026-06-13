import math
import pandas as pd
import numpy as np


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    lat1_r = math.radians(lat1)
    lon1_r = math.radians(lon1)
    lat2_r = math.radians(lat2)
    lon2_r = math.radians(lon2)
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def calculate_total_distance(df: pd.DataFrame) -> float:
    total_km = 0.0
    for i in range(1, len(df)):
        lat1 = df.iloc[i-1]['GPS纬度']
        lon1 = df.iloc[i-1]['GPS经度']
        lat2 = df.iloc[i]['GPS纬度']
        lon2 = df.iloc[i]['GPS经度']
        if pd.notna(lat1) and pd.notna(lon1) and pd.notna(lat2) and pd.notna(lon2):
            total_km += haversine_distance(lat1, lon1, lat2, lon2)
    return round(total_km, 2)


def analyze_door_events(df: pd.DataFrame, interval_minutes: int = None) -> dict:
    if interval_minutes is None:
        if len(df) >= 2:
            diff = (df['时间戳'].iloc[1] - df['时间戳'].iloc[0]).total_seconds() / 60
            interval_minutes = int(round(diff))
        else:
            interval_minutes = 5
    df = df.copy().sort_values('时间戳').reset_index(drop=True)
    door_open_periods = []
    in_open = False
    open_start_idx = None

    for i in range(len(df)):
        status = str(df.loc[i, '车门状态']).strip()
        if status in ['开', 'open', 'Open', 'OPEN', '1', True, 'True']:
            if not in_open:
                in_open = True
                open_start_idx = i
        else:
            if in_open:
                door_open_periods.append((open_start_idx, i - 1))
                in_open = False
                open_start_idx = None
    if in_open and open_start_idx is not None:
        door_open_periods.append((open_start_idx, len(df) - 1))

    results = []
    for start_idx, end_idx in door_open_periods:
        period = df.iloc[start_idx:end_idx + 1]
        duration_min = len(period) * interval_minutes
        temp_start = period.iloc[0]['车厢温度℃']
        temp_end = period.iloc[-1]['车厢温度℃']
        temp_rise = temp_end - temp_start
        rise_rate = temp_rise / duration_min if duration_min > 0 else 0
        results.append({
            '开始时间': period.iloc[0]['时间戳'],
            '结束时间': period.iloc[-1]['时间戳'],
            '持续分钟': duration_min,
            '起始温度': round(temp_start, 2),
            '结束温度': round(temp_end, 2),
            '温度上升': round(temp_rise, 2),
            '上升速率(℃/min)': round(rise_rate, 4)
        })

    avg_rate = round(np.mean([r['上升速率(℃/min)'] for r in results]), 4) if results else 0
    return {
        '开门事件数': len(results),
        '开门事件明细': results,
        '平均温度上升速率(℃/min)': avg_rate
    }


def analyze_speed_temperature(df: pd.DataFrame, stop_threshold: float = 1.0) -> dict:
    df = df.copy()
    df['是否停车'] = df['车速km/h'] < stop_threshold
    stop_df = df[df['是否停车']]
    moving_df = df[~df['是否停车']]
    stop_count = len(stop_df)
    moving_count = len(moving_df)
    stop_temp_mean = round(stop_df['车厢温度℃'].mean(), 2) if stop_count > 0 else None
    moving_temp_mean = round(moving_df['车厢温度℃'].mean(), 2) if moving_count > 0 else None
    stop_temp_max = round(stop_df['车厢温度℃'].max(), 2) if stop_count > 0 else None
    moving_temp_max = round(moving_df['车厢温度℃'].max(), 2) if moving_count > 0 else None
    diff = round(stop_temp_mean - moving_temp_mean, 2) if stop_temp_mean and moving_temp_mean else None

    return {
        '停车数据点数': stop_count,
        '行驶数据点数': moving_count,
        '停车时平均温度': stop_temp_mean,
        '行驶时平均温度': moving_temp_mean,
        '停车时最高温度': stop_temp_max,
        '行驶时最高温度': moving_temp_max,
        '平均温差(停车-行驶)': diff,
        '停车时温度偏高倾向': diff is not None and diff > 0.5
    }


def run_analyze(df: pd.DataFrame, verbose: bool = True) -> dict:
    door_analysis = analyze_door_events(df)
    speed_analysis = analyze_speed_temperature(df)
    total_distance = calculate_total_distance(df)

    result = {
        'GPS总里程(km)': total_distance,
        '车门开关分析': door_analysis,
        '车速温度关联分析': speed_analysis
    }

    if verbose:
        print("=" * 50)
        print("深入分析结果")
        print("=" * 50)
        print(f"\n[GPS轨迹分析]")
        print(f"  总里程: {total_distance} km")
        print(f"\n[车门开关分析]")
        print(f"  开门事件数: {door_analysis['开门事件数']}")
        print(f"  平均温度上升速率: {door_analysis['平均温度上升速率(℃/min)']} ℃/min")
        for i, evt in enumerate(door_analysis['开门事件明细'], 1):
            print(f"  事件{i}: {evt['开始时间']} ~ {evt['结束时间']} "
                  f"({evt['持续分钟']}min) "
                  f"温度从{evt['起始温度']}→{evt['结束温度']}℃ "
                  f"(+{evt['温度上升']}℃, 速率{evt['上升速率(℃/min)']}℃/min)")
        print(f"\n[车速与温度关联分析]")
        print(f"  停车数据点: {speed_analysis['停车数据点数']} | 行驶数据点: {speed_analysis['行驶数据点数']}")
        print(f"  停车平均温度: {speed_analysis['停车时平均温度']}℃ | 行驶平均温度: {speed_analysis['行驶时平均温度']}℃")
        print(f"  停车最高温度: {speed_analysis['停车时最高温度']}℃ | 行驶最高温度: {speed_analysis['行驶时最高温度']}℃")
        if speed_analysis['平均温差(停车-行驶)'] is not None:
            sign = '+' if speed_analysis['平均温差(停车-行驶)'] > 0 else ''
            print(f"  平均温差(停车-行驶): {sign}{speed_analysis['平均温差(停车-行驶)']}℃")
            print(f"  停车时温度偏高倾向: {'是' if speed_analysis['停车时温度偏高倾向'] else '否'}")

    return result
