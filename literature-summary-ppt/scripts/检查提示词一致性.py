from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from docx import Document


技能目录 = Path(__file__).resolve().parents[1]
对应文件 = [
    (
        技能目录 / "references" / "原始文件" / "AI 提示词 - 由文献生成500字左右的极简文献简述.docx",
        技能目录 / "references" / "总结文档原始提示词.md",
    ),
    (
        技能目录 / "references" / "原始文件" / "gpt制作文献汇报PPT提示词(1) (1).docx",
        技能目录 / "references" / "文献汇报PPT原始提示词.md",
    ),
]


def 提取正文(路径: Path) -> str:
    文档 = Document(路径)
    段落 = [段落.text for 段落 in 文档.paragraphs if 段落.text.strip()]
    return "\n\n".join(段落) + "\n"


def 文件校验值(路径: Path) -> str:
    return hashlib.sha256(路径.read_bytes()).hexdigest()


def 正文校验值(正文: str) -> str:
    return hashlib.sha256(正文.encode("utf-8")).hexdigest()


def main() -> int:
    解析器 = argparse.ArgumentParser(description="检查两份提示词是否与原始文档逐字一致")
    解析器.add_argument("--写入", action="store_true", help="从原始文档重新生成提示词文件")
    参数 = 解析器.parse_args()

    记录 = {}
    错误 = []
    for 原始文档, 提示词文件 in 对应文件:
        if not 原始文档.exists():
            错误.append(f"缺少原始文档：{原始文档}")
            continue

        原始正文 = 提取正文(原始文档)
        if 参数.写入:
            提示词文件.write_text(原始正文, encoding="utf-8", newline="\n")

        if not 提示词文件.exists():
            错误.append(f"缺少提示词文件：{提示词文件}")
            continue

        提示词正文 = 提示词文件.read_text(encoding="utf-8")
        if 提示词正文 != 原始正文:
            错误.append(f"提示词与原始文档不一致：{提示词文件.name}")

        记录[原始文档.name] = {
            "原始文档校验值": 文件校验值(原始文档),
            "提取正文校验值": 正文校验值(原始正文),
            "提示词文件": 提示词文件.name,
            "提示词文件校验值": 文件校验值(提示词文件),
        }

    校验值文件 = 技能目录 / "references" / "原始文件" / "校验值.json"
    校验值文件.write_text(
        json.dumps(记录, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    if 错误:
        for 信息 in 错误:
            print(f"错误：{信息}")
        return 1

    print("通过：两份提示词与原始文档逐字一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
