import datetime
from pathlib import Path

def log_markdown(content):
    """将内容写入按日期命名的Markdown日志文件"""
    log_dir = Path("log")
    log_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.date.today().strftime("%Y-%m-%d")
    log_file = log_dir / f"{date_str}.md"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(content + "\n\n")
