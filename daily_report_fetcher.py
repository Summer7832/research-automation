# daily_report_fetcher.py
# 每日18:00自动抓取指定板块研报并生成AI摘要
# 修正版：从研报详情页获取真实PDF下载链接

import os
import re
import json
import time
import requests
from datetime import datetime, timedelta
import glob
import subprocess

# ================== 配置 ==================
TARGET_SECTORS = {
    "证券Ⅱ": "473",
    "保险Ⅱ": "474",
}
PDF_FOLDER = "data/pdfs/"
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
        pattern = r'var initdata\s*=\s*({.*?});\s*</script>'
        match = re.search(pattern, html, re.DOTALL)
        if not match:
            print("未找到 initdata，可能页面结构已变化")
            return []
        json_str = match.group(1)
        try:
            data_obj = json.loads(json_str)
        except json.JSONDecodeError:
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            data_obj = json.loads(json_str)
        reports = data_obj.get("data", [])
        print(f"从页面获取到 {len(reports)} 条研报")
        return reports
    except Exception as e:
        print(f"获取研报列表失败: {e}")
        return []

def get_pdf_url_from_detail(info_code):
    """从研报详情页获取PDF下载链接"""
    detail_url = f"https://data.eastmoney.com/report/{info_code}.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://data.eastmoney.com/report/"
    }
    try:
        resp = requests.get(detail_url, headers=headers, timeout=10)
        resp.encoding = "utf-8"
        # 在页面中搜索 .pdf 链接
        # 常见格式：https://pdf.dfcfw.com/pdf/H3_xxx.pdf 或 /pdf/xxx.pdf
        pdf_pattern = r'(https?://[^\s"\']+\.pdf)'
        match = re.search(pdf_pattern, resp.text, re.IGNORECASE)
        if match:
            pdf_url = match.group(1)
            # 如果链接是相对路径，补全
            if pdf_url.startswith('/'):
                pdf_url = 'https://data.eastmoney.com' + pdf_url
            return pdf_url
        # 备选：搜索 encodeUrl 并构造
        encode_match = re.search(r'"encodeUrl":"([^"]+)"', resp.text)
        if encode_match:
            encode_url = encode_match.group(1)
            return f"https://pdf.dfcfw.com/pdf/H3_{encode_url}.pdf"
        return None
    except Exception as e:
        print(f"获取详情页失败 {info_code}: {e}")
        return None

def download_pdf(pdf_url, save_path):
    """下载PDF文件"""
    if not pdf_url:
        return False
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://data.eastmoney.com/report/"
        }
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

    target_ids = set(TARGET_SECTORS.values())
    filtered = [r for r in all_reports if r.get("industryCode") in target_ids]
    print(f"根据板块过滤后，共 {len(filtered)} 份研报")

    filtered.sort(key=lambda x: x.get("publishDate", ""), reverse=True)
    seen = set()
    unique = []
    for r in filtered:
        title = r.get("title", "")
        if title and title not in seen:
            seen.add(title)
            unique.append(r)
    unique = unique[:MAX_TOTAL]
    print(f"去重后最终下载 {len(unique)} 份研报")

    downloaded = 0
    for report in unique:
        title = report.get("title", "未命名")
        info_code = report.get("infoCode", "")
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", title)
        date_str = report.get("publishDate", "")[:10]
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
        pdf_url = get_pdf_url_from_detail(info_code)
        if pdf_url and download_pdf(pdf_url, filepath):
            downloaded += 1
            print(f"  ✅ 下载成功")
        else:
            print(f"  ❌ 下载失败")
        time.sleep(1)

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