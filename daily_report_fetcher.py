# daily_report_fetcher.py
# 每日18:00自动抓取指定板块研报并生成AI摘要
# 修正版：直接从页面嵌入式数据中提取研报列表

import os
import re
import json
import time
import requests
from datetime import datetime, timedelta
import glob
import subprocess

# ================== 配置 ==================
# 关注的板块ID（从东方财富行业研报页面确认）
TARGET_SECTORS = {
    "证券Ⅱ": "473",
    "保险Ⅱ": "474",
    # "银行Ⅱ": 暂未找到正确ID，可先忽略或后续补充
}
PDF_FOLDER = "data/pdfs/"
MAX_REPORTS_PER_SECTOR = 10
MAX_TOTAL = 20
# ==========================================

def fetch_reports_from_page():
    """从行业研报页面提取所有研报数据（解析initdata）"""
    url = "https://data.eastmoney.com/report/industry.jshtml"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://data.eastmoney.com/report/"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = "utf-8"
        html = resp.text
        # 使用正则提取 initdata 的 JSON 字符串
        pattern = r'var initdata\s*=\s*({.*?});\s*</script>'
        match = re.search(pattern, html, re.DOTALL)
        if not match:
            print("未找到 initdata，可能页面结构已变化")
            return []
        json_str = match.group(1)
        # 处理JavaScript中的一些非标准格式（如注释、尾部逗号），但一般可以直接解析
        try:
            data_obj = json.loads(json_str)
        except json.JSONDecodeError:
            # 如果直接解析失败，尝试去除尾部多余逗号
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            data_obj = json.loads(json_str)
        reports = data_obj.get("data", [])
        print(f"从页面获取到 {len(reports)} 条研报")
        return reports
    except Exception as e:
        print(f"获取研报列表失败: {e}")
        return []

def download_pdf(report, save_path):
    """下载研报PDF（根据 report 中的 encodeUrl 构造下载链接）"""
    encode_url = report.get("encodeUrl")
    if not encode_url:
        return False
    # 构造PDF下载链接（东方财富研报PDF下载地址模式）
    pdf_url = f"https://pdf.dfcfw.com/pdf/H3_{encode_url}.pdf"
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(pdf_url, headers=headers, timeout=30, stream=True)
        if resp.status_code == 200:
            with open(save_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        else:
            print(f"下载失败，状态码: {resp.status_code}")
            return False
    except Exception as e:
        print(f"下载异常: {e}")
        return False

def clean_old_pdfs(days=30):
    """清理超过指定天数的旧PDF"""
    cutoff = datetime.now() - timedelta(days=days)
    for pdf_file in glob.glob(os.path.join(PDF_FOLDER, "*.pdf")):
        mtime = datetime.fromtimestamp(os.path.getmtime(pdf_file))
        if mtime < cutoff:
            os.remove(pdf_file)
            print(f"已清理旧文件: {os.path.basename(pdf_file)}")

def main():
    print(f"========== {datetime.now()} 开始运行 ==========")
    os.makedirs(PDF_FOLDER, exist_ok=True)

    all_reports = fetch_reports_from_page()
    if not all_reports:
        print("未能获取到任何研报，请检查网络或页面结构。")
        return

    # 按行业ID过滤
    target_ids = set(TARGET_SECTORS.values())
    filtered = [r for r in all_reports if r.get("industryCode") in target_ids]
    print(f"根据板块过滤后，共 {len(filtered)} 份研报")

    # 按日期排序（最新的在前）
    filtered.sort(key=lambda x: x.get("publishDate", ""), reverse=True)
    # 去重（按标题去重）
    seen = set()
    unique = []
    for r in filtered:
        title = r.get("title", "")
        if title and title not in seen:
            seen.add(title)
            unique.append(r)
    # 限制数量
    unique = unique[:MAX_TOTAL]
    print(f"去重后最终下载 {len(unique)} 份研报")

    downloaded = 0
    for report in unique:
        title = report.get("title", "未命名")
        # 生成安全的文件名
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", title)
        date_str = report.get("publishDate", "")[:10]  # 取日期部分
        if date_str:
            filename = f"{date_str}_{safe_title}.pdf"
        else:
            filename = f"{datetime.now().strftime('%Y%m%d')}_{safe_title}.pdf"
        filepath = os.path.join(PDF_FOLDER, filename)
        if os.path.exists(filepath):
            print(f"已存在: {filename}")
            downloaded += 1
            continue
        print(f"正在下载: {title} ...")
        if download_pdf(report, filepath):
            downloaded += 1
            print(f"  ✅ 下载成功")
        else:
            print(f"  ❌ 下载失败")
        time.sleep(1)  # 避免请求过快

    print(f"下载完成: {downloaded}/{len(unique)}")
    clean_old_pdfs(30)

    # 调用AI摘要生成
    print("正在生成AI摘要...")
    try:
        subprocess.run(["python", "llm_summarizer.py"], check=True)
        print("✅ AI摘要生成完成")
    except Exception as e:
        print(f"AI摘要生成失败: {e}")

    print("========== 运行结束 ==========")

if __name__ == "__main__":
    main()