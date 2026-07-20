# daily_report_fetcher.py
# 每日抓取指定板块研报列表，生成 Markdown 汇总报告（不下载PDF）
import os
import re
import json
import requests
from datetime import datetime

TARGET_SECTORS = {
    "证券Ⅱ": "473",
    "保险Ⅱ": "474",
}

def fetch_reports_from_page():
    """从行业研报页面提取所有研报数据（解析initdata）"""
    url = "https://data.eastmoney.com/report/industry.jshtml"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = "utf-8"
        html = resp.text
        pattern = r'var initdata\s*=\s*({.*?});\s*</script>'
        match = re.search(pattern, html, re.DOTALL)
        if not match:
            return []
        json_str = match.group(1)
        try:
            data_obj = json.loads(json_str)
        except:
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            data_obj = json.loads(json_str)
        return data_obj.get("data", [])
    except Exception as e:
        print(f"获取研报列表失败: {e}")
        return []

def generate_markdown_report(reports, date_str):
    """生成 Markdown 格式的研报汇总"""
    lines = [
        f"# 行业研报汇总 - {date_str}",
        "",
        f"共收录 {len(reports)} 份研报（证券Ⅱ/保险Ⅱ）",
        "",
        "| 序号 | 标题 | 机构 | 评级 | 日期 |",
        "| --- | --- | --- | --- | --- |"
    ]
    for i, r in enumerate(reports, 1):
        title = r.get("title", "无标题")
        org = r.get("orgSName", "未知机构")
        rating = r.get("emRatingName", "-")
        date = r.get("publishDate", "")[:10]
        lines.append(f"| {i} | {title} | {org} | {rating} | {date} |")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("**注**：本报告仅包含研报元数据，不包含PDF原文。如需详细内容，请点击东方财富研报中心查看。")
    
    return "\n".join(lines)

def main():
    print(f"========== {datetime.now()} 开始运行 ==========")
    
    all_reports = fetch_reports_from_page()
    if not all_reports:
        print("未能获取到任何研报")
        return
    
    target_ids = set(TARGET_SECTORS.values())
    filtered = [r for r in all_reports if r.get("industryCode") in target_ids]
    print(f"获取到 {len(filtered)} 份研报（证券Ⅱ/保险Ⅱ）")
    
    # 按日期降序排列
    filtered.sort(key=lambda x: x.get("publishDate", ""), reverse=True)
    
    # 去重
    seen = set()
    unique = []
    for r in filtered:
        title = r.get("title", "")
        if title and title not in seen:
            seen.add(title)
            unique.append(r)
    
    # 生成报告
    today = datetime.now().strftime("%Y-%m-%d")
    report_dir = "reports/daily"
    os.makedirs(report_dir, exist_ok=True)
    md_path = os.path.join(report_dir, f"{today}_研报汇总.md")
    content = generate_markdown_report(unique, today)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"✅ 汇总报告已生成：{md_path}")
    print("========== 运行结束 ==========")

if __name__ == "__main__":
    main()