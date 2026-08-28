"""灌入知识库：扫描 ../data 下分类目录，解析切块后写入 Chroma"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.rag.loader import load_data_dir  # noqa: E402
from app.rag.store import add_documents  # noqa: E402


def main() -> None:
    docs = load_data_dir()
    if not docs:
        print("未发现知识库文件（检查 ../data 目录）")
        return
    add_documents(docs)
    from collections import Counter

    cats = Counter(d.metadata.get("category", "?") for d in docs)
    print(f"入库完成：共 {len(docs)} 个片段")
    for cat, n in cats.items():
        print(f"  - {cat}: {n} 片段")


if __name__ == "__main__":
    main()
