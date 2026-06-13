import pandas as pd


def check_temperature_compliance(df: pd.DataFrame, temp_min: float, temp_max: float) -> pd.DataFrame:
    result = df.copy()
    result['是否超温'] = ~((result['车厢温度℃'] >= temp_min) & (result['车厢温度℃'] <= temp_max))
    result['偏离度'] = result.apply(
        lambda r: r['车厢温度℃'] - temp_max if r['车厢温度℃'] > temp_max
        else (temp_min - r['车厢温度℃'] if r['车厢温度℃'] < temp_min else 0),
        axis=1
    )
    return result


def detect_severe_events(df: pd.DataFrame, temp_min: float, temp_max: float,
                         consecutive_minutes: int = 15, interval_minutes: int = None) -> list:
    if interval_minutes is None:
        if len(df) >= 2:
            diff = (df['时间戳'].iloc[1] - df['时间戳'].iloc[0]).total_seconds() / 60
            interval_minutes = int(round(diff))
        else:
            interval_minutes = 5
    threshold_points = max(1, consecutive_minutes // interval_minutes)
    events = []
    in_event = False
    event_start = None
    event_temps = []
    event_indices = []
    for idx, row in df.iterrows():
        if row['是否超温']:
            if not in_event:
                in_event = True
                event_start = row['时间戳']
                event_temps = [row['车厢温度℃']]
                event_indices = [idx]
            else:
                event_temps.append(row['车厢温度℃'])
                event_indices.append(idx)
        else:
            if in_event:
                if len(event_temps) >= threshold_points:
                    events.append({
                        '开始时间': event_start,
                        '结束时间': df.loc[event_indices[-1], '时间戳'],
                        '持续分钟': len(event_temps) * interval_minutes,
                        '最大偏离度': round(max(
                            abs(t - temp_max) if t > temp_max else abs(temp_min - t)
                            for t in event_temps
                        ), 2),
                        '最高温度': round(max(event_temps), 2),
                        '最低温度': round(min(event_temps), 2)
                    })
                in_event = False
                event_start = None
                event_temps = []
                event_indices = []
    if in_event and len(event_temps) >= threshold_points:
        events.append({
            '开始时间': event_start,
            '结束时间': df.iloc[-1]['时间戳'],
            '持续分钟': len(event_temps) * interval_minutes,
            '最大偏离度': round(max(
                abs(t - temp_max) if t > temp_max else abs(temp_min - t)
                for t in event_temps
            ), 2),
            '最高温度': round(max(event_temps), 2),
            '最低温度': round(min(event_temps), 2)
        })
    return events


def run_check(df: pd.DataFrame, temp_min: float, temp_max: float, verbose: bool = True) -> dict:
    result_df = check_temperature_compliance(df, temp_min, temp_max)
    total = len(result_df)
    abnormal = result_df['是否超温'].sum()
    abnormal_rate = round(abnormal / total * 100, 2) if total > 0 else 0
    severe_events = detect_severe_events(result_df, temp_min, temp_max)

    stats = {
        '总记录数': total,
        '异常点数': int(abnormal),
        '异常率(%)': abnormal_rate,
        '最高温度': round(result_df['车厢温度℃'].max(), 2),
        '最低温度': round(result_df['车厢温度℃'].min(), 2),
        '平均温度': round(result_df['车厢温度℃'].mean(), 2),
        '严重超温事件次数': len(severe_events),
        '严重超温事件明细': severe_events,
        '达标': abnormal == 0
    }

    if verbose:
        print("=" * 50)
        print("温控达标检查结果")
        print("=" * 50)
        print(f"总记录数: {stats['总记录数']}")
        print(f"异常点数: {stats['异常点数']}")
        print(f"异常率:   {stats['异常率(%)']}%")
        print(f"最高温度: {stats['最高温度']}℃")
        print(f"最低温度: {stats['最低温度']}℃")
        print(f"平均温度: {stats['平均温度']}℃")
        print(f"严重超温事件: {stats['严重超温事件次数']}次")
        for i, evt in enumerate(severe_events, 1):
            print(f"  事件{i}: {evt['开始时间']} ~ {evt['结束时间']} "
                  f"({evt['持续分钟']}分钟) 最大偏离{evt['最大偏离度']}℃ "
                  f"(温度区间 {evt['最低温度']}~{evt['最高温度']}℃)")
        print(f"\n结论: {'✓ 温控达标' if stats['达标'] else '✗ 温控不达标'}")

    return {'数据': result_df, '统计': stats}
