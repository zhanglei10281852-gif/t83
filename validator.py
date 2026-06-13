import pandas as pd
from datetime import timedelta


def validate_continuity(df: pd.DataFrame, interval_minutes: int = None, tolerance_seconds: int = 30) -> list:
    issues = []
    if '时间戳' not in df.columns:
        return ["缺少时间戳列"]
    ts = df['时间戳'].sort_values().reset_index(drop=True)
    if interval_minutes is None:
        if len(ts) >= 2:
            diff = (ts.iloc[1] - ts.iloc[0]).total_seconds() / 60
            interval_minutes = int(round(diff))
        else:
            interval_minutes = 5
    expected = timedelta(minutes=interval_minutes)
    tol = timedelta(seconds=tolerance_seconds)
    for i in range(1, len(ts)):
        diff = ts[i] - ts[i-1]
        if abs(diff - expected) > tol:
            issues.append(
                f"时间间隔异常: 第{i-1}行到第{i}行 间隔{diff.total_seconds()/60:.1f}分钟"
                f" (时间: {ts[i-1]} -> {ts[i]})"
            )
    return issues


def validate_missing(df: pd.DataFrame) -> list:
    issues = []
    required_cols = ['时间戳', '车厢温度℃', '设定温度℃', '环境温度℃', '车门状态', 'GPS经度', 'GPS纬度', '车速km/h']
    for col in required_cols:
        if col not in df.columns:
            issues.append(f"缺少必需列: {col}")
            continue
        missing = df[col].isna().sum()
        if missing > 0:
            issues.append(f"列[{col}]存在{missing}个缺失值")
    return issues


def validate_temperature(df: pd.DataFrame, min_c: float = -40, max_c: float = 50) -> list:
    issues = []
    for col in ['车厢温度℃', '设定温度℃', '环境温度℃']:
        if col not in df.columns:
            continue
        invalid = df[(df[col] < min_c) | (df[col] > max_c)]
        if len(invalid) > 0:
            issues.append(f"列[{col}]有{len(invalid)}个值超出合理范围({min_c}~{max_c}℃)")
    return issues


def validate_gps(df: pd.DataFrame) -> list:
    issues = []
    if 'GPS经度' in df.columns:
        invalid_lon = df[(df['GPS经度'] < -180) | (df['GPS经度'] > 180)]
        if len(invalid_lon) > 0:
            issues.append(f"GPS经度有{len(invalid_lon)}个值超出范围(-180~180)")
    if 'GPS纬度' in df.columns:
        invalid_lat = df[(df['GPS纬度'] < -90) | (df['GPS纬度'] > 90)]
        if len(invalid_lat) > 0:
            issues.append(f"GPS纬度有{len(invalid_lat)}个值超出范围(-90~90)")
    return issues


def run_validate(df: pd.DataFrame, verbose: bool = True) -> dict:
    result = {
        '连续性': validate_continuity(df),
        '缺失值': validate_missing(df),
        '温度范围': validate_temperature(df),
        'GPS坐标': validate_gps(df)
    }
    total_issues = sum(len(v) for v in result.values())
    result['总问题数'] = total_issues
    result['通过'] = total_issues == 0
    if verbose:
        for cat, items in result.items():
            if isinstance(items, list):
                status = "✓" if len(items) == 0 else f"✗ ({len(items)}项)"
                print(f"[{cat}] {status}")
                for item in items:
                    print(f"  - {item}")
        print(f"\n总评: {'✓ 校验通过' if result['通过'] else f'✗ 共发现{total_issues}个问题'}")
    return result
