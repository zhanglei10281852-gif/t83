import json
import random
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path


SHANGHAI = (121.4737, 31.2304)
HANGZHOU = (120.1551, 30.2741)
TOTAL_RECORDS = 180
INTERVAL_MIN = 1
SET_TEMP_CENTER = -18
TEMP_MIN = -20
TEMP_MAX = -16


def generate_sample_data(output_dir: str = '.'):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    start_time = datetime(2026, 6, 12, 8, 0, 0)
    end_time = start_time + timedelta(minutes=(TOTAL_RECORDS - 1) * INTERVAL_MIN)

    door_open_1_start = 25
    door_open_1_end = 35
    door_open_2_start = 90
    door_open_2_end = 100
    overheat_start = 140
    overheat_end = 152

    records = []
    for i in range(TOTAL_RECORDS):
        ts = start_time + timedelta(minutes=i * INTERVAL_MIN)
        progress = i / TOTAL_RECORDS

        lon = SHANGHAI[0] + (HANGZHOU[0] - SHANGHAI[0]) * progress + random.uniform(-0.02, 0.02)
        lat = SHANGHAI[1] + (HANGZHOU[1] - SHANGHAI[1]) * progress + random.uniform(-0.015, 0.015)

        base_speed = 55 + random.uniform(-25, 25)
        if 10 <= i <= 20:
            base_speed = random.uniform(0, 3)
        elif 85 <= i <= 95:
            base_speed = random.uniform(0, 3)
        elif 160 <= i <= 175:
            base_speed = random.uniform(20, 45)

        temp = SET_TEMP_CENTER + random.uniform(-0.7, 0.7)
        if door_open_1_start <= i <= door_open_1_end:
            door = '开'
            factor = (i - door_open_1_start) / max(door_open_1_end - door_open_1_start, 1)
            temp = SET_TEMP_CENTER + factor * 2.8 + random.uniform(-0.15, 0.2)
            if i > door_open_1_start:
                prev_temp = records[-1]['车厢温度℃']
                temp = max(temp, prev_temp + random.uniform(0.08, 0.25))
        elif door_open_2_start <= i <= door_open_2_end:
            door = '开'
            factor = (i - door_open_2_start) / max(door_open_2_end - door_open_2_start, 1)
            temp = SET_TEMP_CENTER + factor * 3.2 + random.uniform(-0.15, 0.2)
            if i > door_open_2_start:
                prev_temp = records[-1]['车厢温度℃']
                temp = max(temp, prev_temp + random.uniform(0.12, 0.3))
        else:
            door = '关'
            if i > 0:
                prev_temp = records[-1]['车厢温度℃']
                if door_open_1_end < i <= door_open_1_end + 15:
                    temp = min(prev_temp + random.uniform(-0.25, -0.08), temp)
                elif door_open_2_end < i <= door_open_2_end + 18:
                    temp = min(prev_temp + random.uniform(-0.22, -0.06), temp)

        if overheat_start <= i <= overheat_end:
            factor = 1.0
            if i == overheat_start:
                factor = 0.3
            elif i == overheat_end:
                factor = 0.4
            temp = TEMP_MAX + factor * random.uniform(0.2, 0.8)

        ambient = 26 + random.uniform(-2, 3) + progress * 1.5

        records.append({
            '时间戳': ts.strftime('%Y-%m-%d %H:%M:%S'),
            '车厢温度℃': round(temp, 1),
            '设定温度℃': SET_TEMP_CENTER,
            '环境温度℃': round(ambient, 1),
            '车门状态': door,
            'GPS经度': round(lon, 5),
            'GPS纬度': round(lat, 5),
            '车速km/h': round(base_speed, 1)
        })

    csv_path = out / 'temperature_records.csv'
    df = pd.DataFrame(records)
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')

    shipment = {
        '运单号': 'CC-2026-0612-SH-HZ-00891',
        '货物名称': '进口速冻水饺/汤圆（冷冻食品）',
        '要求温度范围': '-18℃±2℃',
        '发货地': '上海市青浦区华新镇冷链物流园A区3号库',
        '收货地': '杭州市余杭区良渚街道农副产品物流中心冷链区',
        '发车时间': start_time.strftime('%Y-%m-%d %H:%M:%S'),
        '到达时间': end_time.strftime('%Y-%m-%d %H:%M:%S'),
        '司机姓名': '王建国',
        '车牌号': '沪A·D3F89（冷藏车）'
    }
    json_path = out / 'shipment.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(shipment, f, ensure_ascii=False, indent=2)

    duration_min = TOTAL_RECORDS * INTERVAL_MIN
    hours = duration_min // 60
    minutes = duration_min % 60
    print(f'✓ 已生成示例数据:')
    print(f'  - 温度记录CSV: {csv_path} ({TOTAL_RECORDS}行)')
    print(f'  - 运单信息JSON: {json_path}')
    print(f'  - 运输时段: {start_time} ~ {end_time} (约{hours}小时{minutes}分钟)')
    print(f'  - 嵌入事件: 2次开门(第{door_open_1_start}-{door_open_1_end}行, {door_open_2_start}-{door_open_2_end}行) + 1次轻微超温(第{overheat_start}-{overheat_end}行, {(overheat_end - overheat_start + 1) * INTERVAL_MIN}分钟)')

    return str(csv_path), str(json_path)


if __name__ == '__main__':
    generate_sample_data()
