from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from docx import Document


固定标题 = ["极简文献简述", "背景", "方法", "结果", "总结"]
章节标题 = 固定标题[1:]
结论词 = ("说明", "表明", "提示", "支持", "显示", "证明")
队列词 = ("例", "队列", "数据集", "测试集", "验证集", "分析集", "病例", "患者", "样本", "变异")
指标词 = (
    "一致", "评分", "敏感度", "特异度", "准确", "召回", "相关", "AUC", "HR", "CI",
    "Dice", "P=", "P＝", "优于", "高于", "低于", "升至", "降至", "对照", "比较",
)


def 文件校验值(路径: Path) -> str:
    return hashlib.sha256(路径.read_bytes()).hexdigest()


def 提取章节(段落: list[str]) -> tuple[dict[str, list[str]], list[str]]:
    错误: list[str] = []
    非空 = [文本.strip() for 文本 in 段落 if 文本.strip()]
    if not 非空 or 非空[0] != "极简文献简述":
        错误.append("文档第一项必须是“极简文献简述”")

    标题位置: dict[str, int] = {}
    for 标题 in 固定标题:
        匹配 = [索引 for 索引, 文本 in enumerate(非空) if 文本 == 标题]
        if len(匹配) != 1:
            错误.append(f"标题“{标题}”必须且只能出现一次")
        elif 匹配:
            标题位置[标题] = 匹配[0]

    if all(标题 in 标题位置 for 标题 in 固定标题):
        位置 = [标题位置[标题] for 标题 in 固定标题]
        if 位置 != sorted(位置):
            错误.append("标题顺序必须为：极简文献简述、背景、方法、结果、总结")

    章节: dict[str, list[str]] = {标题: [] for 标题 in 章节标题}
    当前章节: str | None = None
    for 文本 in 非空:
        if 文本 in 章节标题:
            当前章节 = 文本
            continue
        if 文本 == "极简文献简述":
            continue
        if 当前章节:
            章节[当前章节].append(文本)

    for 标题 in 章节标题:
        if not 章节[标题]:
            错误.append(f"章节“{标题}”没有正文")
    return 章节, 错误


def 提取结果条目(段落: list[str]) -> list[str]:
    条目: list[str] = []
    当前 = ""
    起始 = re.compile(r"^\s*(?:\d{1,2}\s*[.、．)]|【[^】]{1,24}】)")
    for 文本 in 段落:
        文本 = 文本.strip()
        if not 文本:
            continue
        if 起始.search(文本):
            if 当前:
                条目.append(当前)
            当前 = 文本
        elif 当前:
            当前 += 文本
        else:
            当前 = 文本
    if 当前:
        条目.append(当前)
    return 条目


def 检查文档(路径: Path, 最少汉字: int, 最多汉字: int) -> dict:
    if not 路径.is_file() or 路径.suffix.lower() != ".docx":
        raise RuntimeError("输入必须是已经存在的DOCX文件")

    文档 = Document(路径)
    原始段落 = [段落.text for 段落 in 文档.paragraphs]
    章节, 错误 = 提取章节(原始段落)
    正文 = "".join("".join(章节[标题]) for 标题 in 章节标题)
    汉字数 = len(re.findall(r"[\u4e00-\u9fff]", 正文))
    拉丁字母数 = len(re.findall(r"[A-Za-z]", 正文))
    中文比例 = 汉字数 / max(1, 汉字数 + 拉丁字母数)

    if 汉字数 < 最少汉字:
        错误.append(f"正文信息量不足：仅{汉字数}个汉字，最低要求为{最少汉字}")
    if 汉字数 > 最多汉字:
        错误.append(f"正文超过500字要求：共{汉字数}个汉字")
    if 中文比例 < 0.55:
        错误.append(f"中文占比过低：{中文比例:.1%}")

    方法 = "".join(章节["方法"])
    方法检查 = {
        "包含样本量": bool(re.search(r"\d", 方法)),
        "包含输入或数据类型": any(词 in 方法 for 词 in ("输入", "病历", "文档", "影像", "数据", "样本", "序列", "临床")),
        "包含模型或方法": any(词 in 方法 for 词 in ("模型", "方法", "系统", "智能体", "网络", "算法", "LLM", "HemaGuide")),
        "包含输出或任务": any(词 in 方法 for 词 in ("输出", "建议", "预测", "分类", "识别", "评估", "诊断", "治疗", "任务")),
        "包含队列或验证划分": any(词 in 方法 for 词 in ("训练", "验证", "测试", "外部", "前瞻", "队列", "消融", "基准", "病例")),
    }
    for 名称, 通过 in 方法检查.items():
        if not 通过:
            错误.append(f"方法部分未通过检查：{名称}")

    结果条目 = 提取结果条目(章节["结果"])
    if not 3 <= len(结果条目) <= 5:
        错误.append(f"结果条目应为3—5条，当前识别到{len(结果条目)}条")

    条目检查 = []
    for 序号, 条目 in enumerate(结果条目, 1):
        检查项 = {
            "包含队列或样本来源": any(词 in 条目 for 词 in 队列词),
            "包含指标或比较": any(词.lower() in 条目.lower() for 词 in 指标词),
            "包含关键数值": bool(re.search(r"\d", 条目)),
            "包含解释性结论": any(词 in 条目 for 词 in 结论词),
            "包含两句或两个分句": len(re.findall(r"[；;。]", 条目)) >= 1,
        }
        条目检查.append({"序号": 序号, "检查": 检查项})
        for 名称, 通过 in 检查项.items():
            if not 通过:
                错误.append(f"结果第{序号}条未通过检查：{名称}")

    占位表达 = re.compile(r"根据PPT|根据汇报材料|TODO|待补充|这里填写|【[^】]*(?:用\d*段话|数据集|队列|核心结论)[^】]*】", re.IGNORECASE)
    if 占位表达.search(正文):
        错误.append("正文包含占位符、提示词说明或外部材料表述")

    return {
        "状态": "通过" if not 错误 else "失败",
        "文档": str(路径.resolve()),
        "文档SHA256": 文件校验值(路径),
        "指标": {
            "正文汉字数": 汉字数,
            "中文比例": round(中文比例, 4),
            "结果条目数": len(结果条目),
            "方法检查": 方法检查,
            "结果条目检查": 条目检查,
        },
        "错误": 错误,
        "说明": "自动检查只验证结构和信息量，不证明论文事实正确；仍需事实复核和Word渲染检查。",
    }


def main() -> int:
    解析器 = argparse.ArgumentParser(description="检查极简文献简述DOCX的结构、信息量和结果完整性")
    解析器.add_argument("文档", type=Path)
    解析器.add_argument("--报告", type=Path)
    解析器.add_argument("--最少汉字", type=int, default=420)
    解析器.add_argument("--最多汉字", type=int, default=500)
    参数 = 解析器.parse_args()

    try:
        结果 = 检查文档(参数.文档.resolve(), 参数.最少汉字, 参数.最多汉字)
    except Exception as 错误:
        结果 = {"状态": "失败", "文档": str(参数.文档.resolve()), "错误": [str(错误)]}

    if 参数.报告:
        参数.报告.parent.mkdir(parents=True, exist_ok=True)
        参数.报告.write_text(json.dumps(结果, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(json.dumps(结果, ensure_ascii=False, indent=2))
    return 0 if 结果.get("状态") == "通过" else 1


if __name__ == "__main__":
    sys.exit(main())
