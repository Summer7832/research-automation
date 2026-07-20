# daily_report_fetcher.py
# 每日抓取指定行业（证券、银行、保险）+ 从研报数据中统计热门板块补充，生成 Markdown 报告

import os
import re
import json
import requests
from datetime import datetime
from collections import Counter

# ========== 配置 ==========
TARGET_INDUSTRIES = ["证券", "银行", "保险"]      # 目标行业关键词
TARGET_COUNT = 10                                 # 期望总份数
# ==========================

def fetch_all_reports():
    """从行业研报页面获取所有研报列表（解析 initdata）"""
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
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        data_obj = json.loads(json_str)
        return data_obj.get("data", [])
    except Exception as e:
        print(f"获取研报列表失败: {e}")
        return []

def filter_reports_by_keywords(reports, keywords):
    """根据行业名称关键词过滤研报"""
    result = []
    for r in reports:
        industry = r.get("industryName", "")
        for kw in keywords:
            if kw in industry:
                result.append(r)
                break
    return result

def get_hot_industries_from_reports(reports, exclude_keywords, top_n=10):
    """
    从研报数据中统计各行业出现次数，排除目标行业关键词，返回出现次数最多的行业名称列表
    """
    # 统计所有研报的行业名称出现次数
    industry_counts = Counter()
    for r in reports:
        industry = r.get("industryName", "")
        if not industry:
            continue
        # 检查是否属于目标行业（排除）
        is_target = any(kw in industry for kw in exclude_keywords)
        if not is_target:
            industry_counts[industry] += 1
    
    # 按出现次数降序取前 top_n
    hot_industries = [item[0] for item in industry_counts.most_common(top_n)]
    print(f"从研报统计的热门行业: {hot_industries}")
    return hot_industries

def generate_markdown_report(reports, date_str, target_keywords, hot_industries):
    """生成 Markdown 格式的研报汇总"""
    lines = [
        f"# 行业研报汇总 - {date_str}",
        "",
        f"共收录 {len(reports)} 份研报（目标行业: {', '.join(target_keywords)}；补充来源: 研报统计热门行业）",
        "",
        "| 序号 | 标题 | 机构 | 评级 | 日期 | 行业 |",
        "| --- | --- | --- | --- | --- | --- |"
    ]
    for i, r in enumerate(reports, 1):
        title = r.get("title", "无标题")
        org = r.get("orgSName", "未知机构")
        rating = r.get("emRatingName", "-")
        date = r.get("publishDate", "")[:10]
        industry = r.get("industryName", "未知")
        lines.append(f"| {i} | {title} | {org} | {rating} | {date} | {industry} |")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("> 数据来源：东方财富研报中心")
    lines.append("> 补充行业基于当天研报的行业分布统计，反映当日市场关注热点。")
    
    return "\n".join(lines)

def main():
    print(f"========== {datetime.now()} 开始运行 ==========")
    
    # 1. 获取所有研报
    all_reports = fetch_all_reports()
    if not all_reports:
        print("❌ 未能获取到任何研报")
        return
    
    print(f"共获取到 {len(all_reports)} 条研报")
    
    # 2. 过滤目标行业（证券、银行、保险）
    target_reports = filter_reports_by_keywords(all_reports, TARGET_INDUSTRIES)
    print(f"目标行业研报: {len(target_reports)} 份")
    
    # 3. 如果目标行业研报数量 >= 目标数，直接取前目标数
    if len(target_reports) >= TARGET_COUNT:
        final_reports = target_reports[:TARGET_COUNT]
        hot_industries = []
    else:
        # 否则，先取全部目标行业研报
        final_reports = target_reports[:]
        # 从所有研报中统计热门行业（排除目标行业）
        hot_industries = get_hot_industries_from_reports(all_reports, TARGET_INDUSTRIES, top_n=10)
        # 从所有研报中过滤出热门行业的研报（排除已选中的）
        existing_titles = {r.get("title", "") for r in final_reports}
        extra_reports = []
        for industry in hot_industries:
            for r in all_reports:
                title = r.get("title", "")
                if title in existing_titles:
                    continue
                if r.get("industryName", "") == industry:
                    extra_reports.append(r)
                    existing_titles.add(title)
                    if len(final_reports) + len(extra_reports) >= TARGET_COUNT:
                        break
            if len(final_reports) + len(extra_reports) >= TARGET_COUNT:
                break
        final_reports.extend(extra_reports)
    
    # 4. 去重（按标题）
    seen = set()
    unique = []
    for r in final_reports:
        title = r.get("title", "")
        if title and title not in seen:
            seen.add(title)
            unique.append(r)
    final_reports = unique[:TARGET_COUNT]
    
    print(f"最终收录 {len(final_reports)} 份研报")
    
    # 5. 生成报告
    today = datetime.now().strftime("%Y-%m-%d")
    report_dir = "reports/daily"
    os.makedirs(report_dir, exist_ok=True)
    md_path = os.path.join(report_dir, f"{today}_研报汇总.md")
    
    content = generate_markdown_report(final_reports, today, TARGET_INDUSTRIES, hot_industries if 'hot_industries' in locals() else [])
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"✅ 汇总报告已生成：{md_path}")
    print("========== 运行结束 ==========")

if __name__ == "__main__":
    main()