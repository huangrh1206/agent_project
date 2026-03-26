import os
import fitz  # PyMuPDF

# 1. 约定属性
tool_name = "PDFParser"
tool_desc = "读取并解析本地 .pdf 文档内容。参数为文件的绝对路径。"

def tool_func(file_path: str) -> str:
    """
    解析 PDF 文档。确保在文档关闭前完成所有数据提取。
    """
    print(f"📑 正在解析 PDF 文档: {file_path}")
    
    # 路径规范化：处理 Windows/Linux 路径差异
    file_path = os.path.abspath(file_path.strip().strip('"').strip("'"))
    
    if not os.path.exists(file_path):
        return f"错误：找不到文件 {file_path}。"
    
    if not file_path.lower().endswith('.pdf'):
        return "错误：该工具仅支持 .pdf 格式。"

    try:
        # 使用 with 语句，Python 会自动管理 doc.open() 和 doc.close()
        with fitz.open(file_path) as doc:
            # 检查文档是否损坏或加密
            if doc.is_closed or doc.is_encrypted:
                return "错误：文档已关闭、损坏或被加密保护。"

            full_text = []
            
            # 遍历每一页
            for page_num in range(len(doc)):
                # 核心修正：在 doc 句柄依然打开时，立即提取文本
                page = doc.load_page(page_num)
                page_text = page.get_text("text").strip()
                
                if page_text:
                    full_text.append(f"--- 第 {page_num + 1} 页 ---\n{page_text}")
                else:
                    full_text.append(f"--- 第 {page_num + 1} 页 ---\n[本页无文字内容，可能是扫描件]")

            # 在 with 缩进内完成字符串合并，确保不依赖 doc 对象
            result = "\n\n".join(full_text)
            
            # 统计总页数以便返回
            total_pages = len(doc)

        # 此时 with 块结束，doc 已经安全关闭
        if not result.strip():
            return "解析完成，但文档中没有提取到任何文字。"
            
        # 返回前 10000 字，避免 Token 溢出
        return f"✅ 解析成功 (共 {total_pages} 页)：\n\n{result[:10000]}"

    except Exception as e:
        # 捕获详细错误
        return f"解析 PDF 时发生异常: {str(e)}"
