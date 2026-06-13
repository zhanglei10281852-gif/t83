import json
import pandas as pd
from pathlib import Path


def load_temperature_csv(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    df.columns = [c.strip() for c in df.columns]
    if '时间戳' in df.columns:
        df['时间戳'] = pd.to_datetime(df['时间戳'])
    elif 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.rename(columns={
            'timestamp': '时间戳',
            'temp_c': '车厢温度℃',
            'set_temp_c': '设定温度℃',
            'ambient_c': '环境温度℃',
            'door_status': '车门状态',
            'lon': 'GPS经度',
            'lat': 'GPS纬度',
            'speed_kmh': '车速km/h'
        })
    df['车门状态'] = df['车门状态'].astype(str).str.strip()
    return df


def load_shipment_json(json_path: str) -> dict:
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    temp = data.get('要求温度范围')
    if isinstance(temp, str) and '±' in temp:
        center, delta = temp.replace('℃', '').split('±')
        center = float(center)
        delta = float(delta)
        data['温度下限'] = center - delta
        data['温度上限'] = center + delta
    elif isinstance(temp, (list, tuple)) and len(temp) == 2:
        data['温度下限'] = float(temp[0])
        data['温度上限'] = float(temp[1])
    else:
        data['温度下限'] = data.get('温度下限', -20.0)
        data['温度上限'] = data.get('温度上限', -16.0)
    return data
