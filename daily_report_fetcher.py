# daily_report_fetcher.py
# 每日抓取指定行业（证券、银行、保险）+ 补足热门板块研报，生成 Markdown 报告
# 使用 requests 直接调用东方财富 API 获取热门板块

import os
import re
import json
import requests
from datetime import datetime

# ========== 配置 ==========
TARGET_INDUSTRIES = ["证券", "银行", "保险"]      # 目标行业关键词
TARGET_COUNT = 10                                 # 期望总份数
HOT_SECTOR_COUNT = 5                              # 补充用的热门板块个数
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
        # 处理可能的不合规JSON
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        data_obj = json.loads(json_str)
        return data_obj.get("data", [])
    except Exception as e:
        print(f"获取研报列表失败: {e}")
        return []

def get_hot_sectors_from_api():
    """
    从东方财富 API 获取当日涨幅前 N 的行业板块名称
    使用公开接口，无需登录
    """
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": 1,
        "pz": 100,
        "po": 1,
        "np": 1,
        "ut": "bd1d9ddb04089788cf9c27a6c742273c",
        "fltt": 2,
        "invt": 2,
        "fid": "f3",          # 按涨跌幅排序
        "fs": "m:90+t:2",     # 行业板块
        "fields": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f19,f20,f21,f22,f23,f24,f25,f26,f27,f28,f29,f30,f31,f32,f33,f34,f35,f36,f37,f38,f39,f40,f41,f42,f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65,f66,f67,f68,f69,f70,f71,f72,f73,f74,f75,f76,f77,f78,f79,f80,f81,f82,f83,f84,f85,f86,f87,f88,f89,f90,f91,f92,f93,f94,f95,f96,f97,f98,f99,f100"
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        data = resp.json()
        if data.get('data') and data['data'].get('diff'):
            items = data['data']['diff']
            # 提取名称和涨跌幅，按涨跌幅降序排列（API已排序，但为确保）
            # 取前 HOT_SECTOR_COUNT 个
            hot = []
            for item in items[:HOT_SECTOR_COUNT]:
                name = item.get('f14')
                if name:
                    hot.append(name)
            print(f"从API获取热门板块: {hot}")
            return hot
        else:
            print("API返回数据为空")
            return []
    except Exception as e:
        print(f"获取热门板块API失败: {e}")
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

def generate_markdown_report(reports, date_str, target_keywords, hot_keywords):
    """生成 Markdown 格式的研报汇总，并标注来源"""
    lines = [
        f"# 行业研报汇总 - {date_str}",
        "",
        f"共收录 {len(reports)} 份研报（目标行业: {', '.join(target_keywords)}；补充热点: {', '.join(hot_keywords) if hot_keywords else '无'}）",
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
    lines.append("> 数据来源：东方财富研报中心 & 行业资金流向API")
    lines.append("> 本报告仅包含研报元数据，不含PDF原文。如需详情，请访问东方财富研报中心。")
    
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
        hot_keywords = []
    else:
        # 否则，先取全部目标行业研报
        final_reports = target_reports[:]
        # 获取热门板块
        hot_sectors = get_hot_sectors_from_api()
        # 从所有研报中过滤出热门板块的研报（排除已选中的）
        existing_titles = {r.get("title", "") for r in final_reports}
        extra_reports = []
        for sector in hot_sectors:
            # 注意：热门板块名称可能和研报中的 industryName 不完全一致，但通常包含关键词
            for r in all_reports:
                title = r.get("title", "")
                if title in existing_titles:
                    continue
                industry = r.get("industryName", "")
                if sector in industry or industry in sector:
                    extra_reports.append(r)
                    existing_titles.add(title)
                    if len(final_reports) + len(extra_reports) >= TARGET_COUNT:
                        break
            if len(final_reports) + len(extra_reports) >= TARGET_COUNT:
                break
        final_reports.extend(extra_reports)
        hot_keywords = hot_sectors[:len(extra_reports)] if extra_reports else []
    
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
    
    content = generate_markdown_report(final_reports, today, TARGET_INDUSTRIES, hot_keywords)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"✅ 汇总报告已生成：{md_path}")
    print("========== 运行结束 ==========")

if __name__ == "__main__":
    main()