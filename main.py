#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

from data_loader import load_temperature_csv, load_shipment_json
from validator import run_validate
from checker import run_check
from analyzer import run_analyze
from reporter import run_report
from generate_sample import generate_sample_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='coldchain',
        description='冷链物流温控报告批处理工具 - 检查/分析/报告/校验',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''示例用法:
  coldchain sample                           # 生成示例数据
  coldchain validate -c temperature_records.csv
  coldchain check -c temperature_records.csv -j shipment.json
  coldchain analyze -c temperature_records.csv
  coldchain report -c temperature_records.csv -j shipment.json -o report.html
'''
    )
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    p_sample = sub.add_parser('sample', help='生成示例数据（上海→杭州冷冻运输3小时180行）')
    p_sample.add_argument('-o', '--output', default='.', help='输出目录 (默认: 当前目录)')

    p_val = sub.add_parser('validate', help='校验CSV完整性（时间连续性/缺失值/温区/GPS坐标）')
    p_val.add_argument('-c', '--csv', required=True, help='温度记录CSV文件路径')

    p_chk = sub.add_parser('check', help='温控达标检查（逐点判断+严重超温事件）')
    p_chk.add_argument('-c', '--csv', required=True, help='温度记录CSV文件路径')
    p_chk.add_argument('-j', '--json', required=True, help='运单信息JSON文件路径')

    p_ana = sub.add_parser('analyze', help='深入分析（车门关联/车速关联/GPS里程）')
    p_ana.add_argument('-c', '--csv', required=True, help='温度记录CSV文件路径')

    p_rep = sub.add_parser('report', help='生成HTML报告（图表嵌入+签字确认栏）')
    p_rep.add_argument('-c', '--csv', required=True, help='温度记录CSV文件路径')
    p_rep.add_argument('-j', '--json', required=True, help='运单信息JSON文件路径')
    p_rep.add_argument('-o', '--output', default=None, help='输出HTML文件路径 (默认: 同目录_{csv名}_report.html)')

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == 'sample':
        generate_sample_data(args.output)
        return

    if args.command == 'validate':
        csv_path = Path(args.csv)
        if not csv_path.exists():
            print(f'错误: 找不到CSV文件 {csv_path}', file=sys.stderr)
            sys.exit(1)
        df = load_temperature_csv(str(csv_path))
        result = run_validate(df)
        sys.exit(0 if result['通过'] else 1)

    if args.command == 'check':
        csv_path = Path(args.csv)
        json_path = Path(args.json)
        if not csv_path.exists():
            print(f'错误: 找不到CSV文件 {csv_path}', file=sys.stderr)
            sys.exit(1)
        if not json_path.exists():
            print(f'错误: 找不到JSON文件 {json_path}', file=sys.stderr)
            sys.exit(1)
        df = load_temperature_csv(str(csv_path))
        shipment = load_shipment_json(str(json_path))
        result = run_check(df, shipment['温度下限'], shipment['温度上限'])
        sys.exit(0 if result['统计']['达标'] else 2)

    if args.command == 'analyze':
        csv_path = Path(args.csv)
        if not csv_path.exists():
            print(f'错误: 找不到CSV文件 {csv_path}', file=sys.stderr)
            sys.exit(1)
        df = load_temperature_csv(str(csv_path))
        run_analyze(df)
        return

    if args.command == 'report':
        csv_path = Path(args.csv)
        json_path = Path(args.json)
        if not csv_path.exists():
            print(f'错误: 找不到CSV文件 {csv_path}', file=sys.stderr)
            sys.exit(1)
        if not json_path.exists():
            print(f'错误: 找不到JSON文件 {json_path}', file=sys.stderr)
            sys.exit(1)
        out = run_report(str(csv_path), str(json_path), output_path=args.output)
        print(f'\n请用浏览器打开: {out}')
        return


if __name__ == '__main__':
    main()
