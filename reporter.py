import os
import base64
import io
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle

from data_loader import load_temperature_csv, load_shipment_json
from checker import run_check
from analyzer import run_analyze


plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


def generate_temperature_chart(df: pd.DataFrame, temp_min: float, temp_max: float,
                               severe_events: list, door_events: list) -> str:
    fig, ax = plt.subplots(figsize=(14, 7))
    timestamps = df['时间戳']
    temps = df['车厢温度℃']

    ax.plot(timestamps, temps, label='车厢温度', color='#1f77b4', linewidth=1.8, zorder=3)
    ax.axhline(y=temp_max, color='#d62728', linestyle='--', linewidth=1.2, label=f'温度上限 {temp_max}℃', zorder=2)
    ax.axhline(y=temp_min, color='#2ca02c', linestyle='--', linewidth=1.2, label=f'温度下限 {temp_min}℃', zorder=2)
    ax.axhline(y=(temp_min + temp_max) / 2, color='#7f7f7f', linestyle=':', linewidth=0.8,
               label=f'设定温度 {(temp_min + temp_max) / 2:.1f}℃', zorder=2)

    abnormal_mask = df['是否超温']
    for i in range(len(df)):
        if abnormal_mask.iloc[i]:
            x_start = df.iloc[i]['时间戳']
            if i < len(df) - 1:
                x_end = df.iloc[i + 1]['时间戳']
            else:
                x_end = x_start + pd.Timedelta(minutes=5)
            y_low = min(temps.min(), temp_min) - 1
            y_high = max(temps.max(), temp_max) + 1
            width = mdates.date2num(x_end) - mdates.date2num(x_start)
            rect = Rectangle((mdates.date2num(x_start), y_low), width, y_high - y_low,
                             facecolor='red', alpha=0.12, edgecolor='none', zorder=1)
            ax.add_patch(rect)

    for evt in severe_events:
        ax.axvspan(evt['开始时间'], evt['结束时间'], alpha=0.22, color='red', zorder=1)

    for de in door_events:
        ax.axvline(de['开始时间'], color='orange', linestyle='-', linewidth=1.5, alpha=0.7)
        ax.axvline(de['结束时间'], color='orange', linestyle='-', linewidth=1.5, alpha=0.7)
        ax.axvspan(de['开始时间'], de['结束时间'], alpha=0.15, color='orange', zorder=1)

    ax.set_xlabel('时间', fontsize=11)
    ax.set_ylabel('温度 (℃)', fontsize=11)
    ax.set_title('全程温度曲线监控', fontsize=14, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.6, zorder=0)
    ax.legend(loc='upper right', fontsize=9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    fig.autofmt_xdate()
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=120, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


def generate_gps_svg(df: pd.DataFrame, width: int = 500, height: int = 380) -> str:
    lons = df['GPS经度'].values
    lats = df['GPS纬度'].values
    valid_mask = ~pd.isna(lons) & ~pd.isna(lats)
    lons = lons[valid_mask]
    lats = lats[valid_mask]
    if len(lons) == 0:
        return '<svg viewBox="0 0 500 380" xmlns="http://www.w3.org/2000/svg"><text x="250" y="190" text-anchor="middle">无GPS数据</text></svg>'

    min_lon, max_lon = lons.min(), lons.max()
    min_lat, max_lat = lats.min(), lats.max()
    lon_range = max_lon - min_lon if max_lon != min_lon else 1
    lat_range = max_lat - min_lat if max_lat != min_lat else 1

    padding = 40
    w = width - 2 * padding
    h = height - 2 * padding

    scale = max(lon_range / w, lat_range / h)
    w_used = lon_range / scale
    h_used = lat_range / scale
    x_offset = padding + (w - w_used) / 2
    y_offset = padding + (h - h_used) / 2

    points = []
    for lon, lat in zip(lons, lats):
        x = x_offset + (lon - min_lon) / scale
        y = y_offset + h_used - (lat - min_lat) / scale
        points.append(f'{x:.1f},{y:.1f}')

    polyline = ' '.join(points)
    start_x, start_y = [float(v) for v in points[0].split(',')]
    end_x, end_y = [float(v) for v in points[-1].split(',')]

    svg = f'''<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" style="border:1px solid #ddd;border-radius:8px;">
  <defs>
    <marker id="arrow" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="#1f77b4"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="{width}" height="{height}" fill="#fafafa"/>
  <polyline points="{polyline}" fill="none" stroke="#1f77b4" stroke-width="2"
            marker-end="url(#arrow)" stroke-linejoin="round" stroke-linecap="round"/>
  <circle cx="{start_x}" cy="{start_y}" r="6" fill="#2ca02c" stroke="white" stroke-width="2"/>
  <text x="{start_x}" y="{start_y - 12}" text-anchor="middle" font-size="11" fill="#2ca02c" font-weight="bold">起点</text>
  <circle cx="{end_x}" cy="{end_y}" r="6" fill="#d62728" stroke="white" stroke-width="2"/>
  <text x="{end_x}" y="{end_y - 12}" text-anchor="middle" font-size="11" fill="#d62728" font-weight="bold">终点</text>
  <text x="{padding}" y="{height - 12}" font-size="10" fill="#666">经度范围: {min_lon:.4f}° ~ {max_lon:.4f}°</text>
  <text x="{width - padding}" y="{height - 12}" font-size="10" fill="#666" text-anchor="end">纬度范围: {min_lat:.4f}° ~ {max_lat:.4f}°</text>
</svg>'''
    return svg


def generate_door_timeline_html(door_events: list) -> str:
    if not door_events:
        return '<p class="muted">无车门开关事件记录</p>'
    rows = ''
    for i, evt in enumerate(door_events, 1):
        rows += f'''<tr>
      <td>{i}</td>
      <td>{evt['开始时间'].strftime('%Y-%m-%d %H:%M')}</td>
      <td>{evt['结束时间'].strftime('%Y-%m-%d %H:%M')}</td>
      <td>{evt['持续分钟']} 分钟</td>
      <td>{evt['起始温度']}℃ → {evt['结束温度']}℃</td>
      <td style="color:#d62728;font-weight:bold;">+{evt['温度上升']}℃</td>
      <td>{evt['上升速率(℃/min)']}℃/min</td>
    </tr>'''
    return f'''<table class="data-table">
  <thead><tr><th>序号</th><th>开始时间</th><th>结束时间</th><th>持续时长</th><th>温度变化</th><th>上升幅度</th><th>上升速率</th></tr></thead>
  <tbody>{rows}</tbody>
</table>'''


def generate_severe_events_html(events: list) -> str:
    if not events:
        return '<p class="pass">无严重超温事件 ✓</p>'
    rows = ''
    for i, evt in enumerate(events, 1):
        rows += f'''<tr>
      <td>{i}</td>
      <td>{evt['开始时间'].strftime('%Y-%m-%d %H:%M')}</td>
      <td>{evt['结束时间'].strftime('%Y-%m-%d %H:%M')}</td>
      <td>{evt['持续分钟']} 分钟</td>
      <td>{evt['最低温度']}℃ ~ {evt['最高温度']}℃</td>
      <td style="color:#d62728;font-weight:bold;">{evt['最大偏离度']}℃</td>
    </tr>'''
    return f'''<table class="data-table">
  <thead><tr><th>序号</th><th>开始时间</th><th>结束时间</th><th>持续时长</th><th>温度区间</th><th>最大偏离度</th></tr></thead>
  <tbody>{rows}</tbody>
</table>'''


def build_html_report(shipment: dict, check_result: dict, analyze_result: dict,
                      chart_img_b64: str, gps_svg: str) -> str:
    stats = check_result['统计']
    pass_status = '达标' if stats['达标'] else '不达标'
    pass_class = 'pass' if stats['达标'] else 'fail'
    pass_icon = '✓' if stats['达标'] else '✗'

    ship_info_rows = f'''<tr><td>运单号</td><td><strong>{shipment.get('运单号', 'N/A')}</strong></td>
      <td>车牌号</td><td>{shipment.get('车牌号', 'N/A')}</td></tr>
    <tr><td>货物名称</td><td>{shipment.get('货物名称', 'N/A')}</td>
      <td>司机姓名</td><td>{shipment.get('司机姓名', 'N/A')}</td></tr>
    <tr><td>要求温度范围</td><td style="color:#1f77b4;font-weight:bold;">{shipment.get('要求温度范围', 'N/A')} ({shipment.get('温度下限', '?')}℃ ~ {shipment.get('温度上限', '?')}℃)</td>
      <td>运距(GPS)</td><td>{analyze_result['GPS总里程(km)']} km</td></tr>
    <tr><td>发货地</td><td>{shipment.get('发货地', 'N/A')}</td>
      <td>发车时间</td><td>{shipment.get('发车时间', 'N/A')}</td></tr>
    <tr><td>收货地</td><td>{shipment.get('收货地', 'N/A')}</td>
      <td>到达时间</td><td>{shipment.get('到达时间', 'N/A')}</td></tr>'''

    summary_rows = f'''<tr><td>总记录数</td><td>{stats['总记录数']}</td>
      <td>异常率</td><td class="{'fail' if stats['异常率(%)'] > 0 else ''}">{stats['异常率(%)']}%</td></tr>
    <tr><td>异常点数</td><td class="{'fail' if stats['异常点数'] > 0 else ''}">{stats['异常点数']}</td>
      <td>严重超温事件</td><td class="{'fail' if stats['严重超温事件次数'] > 0 else ''}">{stats['严重超温事件次数']} 次</td></tr>
    <tr><td>最高温度</td><td>{stats['最高温度']}℃</td>
      <td>最低温度</td><td>{stats['最低温度']}℃</td></tr>
    <tr><td>平均温度</td><td>{stats['平均温度']}℃</td>
      <td>结论</td><td class="{pass_class}" style="font-weight:bold;">{pass_icon} {pass_status}</td></tr>'''

    door_timeline = generate_door_timeline_html(analyze_result['车门开关分析']['开门事件明细'])
    severe_html = generate_severe_events_html(stats['严重超温事件明细'])

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    report_id = shipment.get('运单号', 'RPT') + '-' + datetime.now().strftime('%Y%m%d%H%M%S')

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>冷链温控报告 - {shipment.get('运单号', '')}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: "Microsoft YaHei", "SimHei", sans-serif; max-width: 1100px; margin: 0 auto; padding: 20px; background:#f5f7fa; color:#333; }}
  .header {{ background: linear-gradient(135deg, #1f4e79, #2e75b6); color: white; padding: 25px 30px; border-radius: 10px; margin-bottom: 25px; }}
  .header h1 {{ margin: 0 0 8px 0; font-size: 26px; }}
  .header .meta {{ font-size: 13px; opacity: 0.9; display: flex; justify-content: space-between; }}
  .section {{ background: white; border-radius: 10px; padding: 25px 30px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
  .section h2 {{ color: #1f4e79; border-bottom: 2px solid #2e75b6; padding-bottom: 10px; margin-top: 0; font-size: 19px; }}
  .section h3 {{ color: #444; font-size: 16px; margin-top: 20px; }}
  .info-table, .data-table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
  .info-table td {{ padding: 10px 14px; border-bottom: 1px solid #eee; font-size: 14px; }}
  .info-table td:first-child {{ width: 14%; color: #666; font-weight: 500; background: #f9fbff; }}
  .info-table td:nth-child(3) {{ width: 14%; color: #666; font-weight: 500; background: #f9fbff; }}
  .data-table th {{ background: #2e75b6; color: white; padding: 10px; text-align: center; font-weight: 500; font-size: 13px; }}
  .data-table td {{ padding: 9px 12px; border-bottom: 1px solid #eef0f3; text-align: center; font-size: 13px; }}
  .data-table tr:hover td {{ background: #f9fbff; }}
  .conclusion-banner {{ padding: 18px 25px; border-radius: 8px; font-size: 18px; font-weight: bold; margin: 18px 0; text-align: center; }}
  .pass {{ color: #2ca02c; }}
  .fail {{ color: #d62728; }}
  .pass.banner {{ background: #e8f5e9; border: 1px solid #a5d6a7; }}
  .fail.banner {{ background: #ffebee; border: 1px solid #ef9a9a; }}
  .chart-box {{ text-align: center; margin: 18px 0; }}
  .chart-box img {{ max-width: 100%; border-radius: 6px; box-shadow: 0 2px 6px rgba(0,0,0,0.1); }}
  .two-col {{ display: flex; gap: 25px; margin-top: 18px; }}
  .two-col > div {{ flex: 1; }}
  .muted {{ color: #999; font-style: italic; }}
  .signature-area {{ display: flex; justify-content: space-between; margin-top: 35px; padding-top: 25px; border-top: 1px solid #e0e0e0; }}
  .signature-box {{ width: 42%; }}
  .signature-box .label {{ font-weight: bold; color: #555; margin-bottom: 35px; font-size: 14px; }}
  .signature-line {{ border-bottom: 1px solid #333; padding-bottom: 6px; margin-bottom: 8px; }}
  .signature-small {{ font-size: 12px; color: #888; }}
  .footer {{ text-align: center; color: #aaa; font-size: 12px; margin-top: 30px; padding-top: 15px; border-top: 1px solid #eee; }}
</style>
</head>
<body>
<div class="header">
  <h1>❄ 冷链运输温控报告</h1>
  <div class="meta"><span>报告编号: {report_id}</span><span>生成时间: {now}</span></div>
</div>

<div class="section">
  <h2>📋 运单基本信息</h2>
  <table class="info-table"><tbody>{ship_info_rows}</tbody></table>
</div>

<div class="section">
  <h2>✅ 温控达标结论</h2>
  <div class="conclusion-banner {'pass' if stats['达标'] else 'fail'} banner">{pass_icon} 本次运输温控<strong>{pass_status}</strong></div>
  <table class="info-table"><tbody>{summary_rows}</tbody></table>
</div>

<div class="section">
  <h2>📈 全程温度曲线图</h2>
  <div class="chart-box"><img src="data:image/png;base64,{chart_img_b64}" alt="温度曲线图"/></div>
  <p class="muted" style="text-align:center;">说明：蓝色折线为车厢温度，绿色/红色虚线为温度下限/上限，红色背景为超温异常区域，橙色区块为车门开启时段。</p>
</div>

<div class="section">
  <h2>🚪 车门开关事件时间线</h2>
  <p>平均温度上升速率: <strong>{analyze_result['车门开关分析']['平均温度上升速率(℃/min)']} ℃/min</strong></p>
  {door_timeline}
</div>

<div class="two-col">
  <div class="section" style="margin-bottom:0;">
    <h2>🗺 GPS行驶轨迹</h2>
    <div class="chart-box">{gps_svg}</div>
    <p style="text-align:center;font-size:13px;color:#555;">GPS累加总里程: <strong>{analyze_result['GPS总里程(km)']} km</strong></p>
  </div>
  <div class="section" style="margin-bottom:0;">
    <h2>🔥 严重超温事件明细</h2>
    {severe_html}
    <h3>🚗 车速与温度关联</h3>
    <table class="info-table"><tbody>
      <tr><td>停车平均温度</td><td>{analyze_result['车速温度关联分析']['停车时平均温度']}℃</td></tr>
      <tr><td>行驶平均温度</td><td>{analyze_result['车速温度关联分析']['行驶时平均温度']}℃</td></tr>
      <tr><td>停车-行驶温差</td><td class="{'fail' if analyze_result['车速温度关联分析']['平均温差(停车-行驶)'] and analyze_result['车速温度关联分析']['平均温差(停车-行驶)'] > 0.5 else ''}">{'+' if analyze_result['车速温度关联分析']['平均温差(停车-行驶)'] is not None and analyze_result['车速温度关联分析']['平均温差(停车-行驶)'] > 0 else ''}{analyze_result['车速温度关联分析']['平均温差(停车-行驶)']}℃</td></tr>
      <tr><td>停车偏高倾向</td><td class="{'fail' if analyze_result['车速温度关联分析']['停车时温度偏高倾向'] else 'pass'}">{'是' if analyze_result['车速温度关联分析']['停车时温度偏高倾向'] else '否'}</td></tr>
    </tbody></table>
  </div>
</div>

<div class="section">
  <h2>📝 签字确认</h2>
  <div class="signature-area">
    <div class="signature-box">
      <div class="label">承运方确认签字：</div>
      <div class="signature-line"></div>
      <div class="signature-small">签字：________________ &nbsp;&nbsp;&nbsp; 日期：____________</div>
    </div>
    <div class="signature-box">
      <div class="label">收货方确认签字：</div>
      <div class="signature-line"></div>
      <div class="signature-small">签字：________________ &nbsp;&nbsp;&nbsp; 日期：____________</div>
    </div>
  </div>
</div>

<div class="footer">本报告由冷链温控自动分析系统生成 · 数据仅供参考 · 如有异议请于3个工作日内提出</div>
</body>
</html>'''
    return html


def run_report(csv_path: str, json_path: str, output_path: str = None, verbose: bool = True) -> str:
    df = load_temperature_csv(csv_path)
    shipment = load_shipment_json(json_path)
    temp_min = shipment['温度下限']
    temp_max = shipment['温度上限']

    check_result = run_check(df, temp_min, temp_max, verbose=False)
    analyze_result = run_analyze(df, verbose=False)

    chart_b64 = generate_temperature_chart(
        check_result['数据'], temp_min, temp_max,
        check_result['统计']['严重超温事件明细'],
        analyze_result['车门开关分析']['开门事件明细']
    )
    gps_svg = generate_gps_svg(df)

    html_content = build_html_report(shipment, check_result, analyze_result, chart_b64, gps_svg)

    if output_path is None:
        base = Path(csv_path).stem
        output_path = str(Path(csv_path).parent / f'{base}_report.html')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    if verbose:
        print("=" * 50)
        print("HTML报告生成完成")
        print("=" * 50)
        print(f"输出文件: {output_path}")
        print(f"文件大小: {os.path.getsize(output_path) / 1024:.1f} KB")
        print(f"温控结论: {'✓ 达标' if check_result['统计']['达标'] else '✗ 不达标'} "
              f"(异常率 {check_result['统计']['异常率(%)']}%)")
        print(f"GPS里程: {analyze_result['GPS总里程(km)']} km")
        print(f"严重超温: {check_result['统计']['严重超温事件次数']} 次")

    return output_path
