# llm_summarizer.py
# 安全版本：API Key 从环境变量读取，不写入代码

import os
import requests
import json
import glob
from pypdf import PdfReader

# ================== 配置区 ==================
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise ValueError("❌ 未找到环境变量 DEEPSEEK_API_KEY，请先设置。")

PDF_FOLDER = "data/pdfs/"
OUTPUT_FILE = "reports/llm_abstracts.md"
# ============================================

def extract_text_from_pdf(pdf_path, max_pages=5):
    """提取PDF前N页文本"""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        pages_to_read = min(len(reader.pages), max_pages)
        for i in range(pages_to_read):
            page = reader.pages[i]
            text += page.extract_text()
        if len(text) > 4000:
            text = text[:4000] + "...(截断)"
        return text
    except Exception as e:
        print(f"读取PDF失败 {pdf_path}: {e}")
        return None

def summarize_with_deepseek(text, filename):
    """调用DeepSeek API进行结构化摘要"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
    这是一份券商研究报告（文件名为{filename}），请按以下格式提取关键信息：
    
    1. **核心观点**：该报告的核心结论是什么？（50字以内）
    2. **推荐标的**：报告推荐或看好的具体股票/板块（如有，列出名称）
    3. **关键数据**：报告提到的关键财务预测或估值数据（如有）
    4. **风险提示**：报告中提到的最大不确定性因素（30字以内）
    
    报告原文片段如下：
    {text}
    """
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是金融分析助理，擅长提取研报核心信息。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 800
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return f"API调用失败: {response.status_code} - {response.text}"
    except Exception as e:
        return f"请求异常: {str(e)}"

def main():
    pdf_files = glob.glob(os.path.join(PDF_FOLDER, "*.pdf"))
    
    if not pdf_files:
        print("❌ 没有在 data/pdfs/ 下找到任何PDF文件")
        print("请先下载一份券商研报PDF放到该文件夹")
        return
    
    print(f"✅ 找到 {len(pdf_files)} 份研报，开始处理...")
    
    results = []
    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        print(f"⏳ 正在处理: {filename}")
        
        text = extract_text_from_pdf(pdf_path)
        if text:
            summary = summarize_with_deepseek(text, filename)
            results.append(f"### {filename}\n\n{summary}\n\n---\n")
        else:
            results.append(f"### {filename}\n\n❌ 读取失败，请检查文件格式\n\n---\n")
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# AI研报摘要分析\n\n")
        f.write("> 以下内容由DeepSeek AI自动生成，仅供参考。\n\n")
        f.writelines(results)
    
    print(f"✅ 处理完成！摘要已保存至: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
