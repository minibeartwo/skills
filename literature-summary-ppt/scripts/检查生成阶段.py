from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


阶段顺序 = [
    "已初始化",
    "总结预览待确认",
    "总结预览已确认",
    "普通版预览待确认",
    "普通版预览已确认",
    "普通版PPT已完成",
    "深大版预览待确认",
    "深大版预览已确认",
    "深大版PPT已完成",
]

动作规则 = {
    "记录总结预览": (("已初始化", "总结预览待确认"), "总结预览待确认", "总结预览"),
    "确认总结预览": ("总结预览待确认", "总结预览已确认", "确认"),
    "记录普通版预览": (("总结预览已确认", "普通版预览待确认"), "普通版预览待确认", "图片目录"),
    "确认普通版预览": ("普通版预览待确认", "普通版预览已确认", "确认"),
    "记录普通版PPT": ("普通版预览已确认", "普通版PPT已完成", "演示文稿"),
    "记录深大版预览": (("普通版PPT已完成", "深大版预览待确认"), "深大版预览待确认", "图片目录"),
    "确认深大版预览": ("深大版预览待确认", "深大版预览已确认", "确认"),
    "记录深大版PPT": ("深大版预览已确认", "深大版PPT已完成", "演示文稿"),
}


def 读取状态(状态文件: Path) -> dict:
    if not 状态文件.exists():
        raise RuntimeError("尚未初始化生成阶段")
    return json.loads(状态文件.read_text(encoding="utf-8"))


def 保存状态(状态文件: Path, 数据: dict) -> None:
    状态文件.parent.mkdir(parents=True, exist_ok=True)
    状态文件.write_text(json.dumps(数据, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def 文件校验值(路径: Path) -> str:
    return hashlib.sha256(路径.read_bytes()).hexdigest()


def 检查图片目录(文件参数: str | None, 名称: str = "预览图") -> str:
    if not 文件参数:
        raise RuntimeError(f"必须提供{名称}路径")
    路径 = Path(文件参数).resolve()
    if not 路径.is_dir():
        raise RuntimeError(f"{名称}路径必须是已经存在的目录")
    图片 = [项 for 项 in 路径.iterdir() if 项.is_file() and 项.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}]
    if not 图片:
        raise RuntimeError(f"{名称}目录中没有图片")
    return str(路径)


def 检查普通文件(类型: str, 文件参数: str | None) -> str:
    if not 文件参数:
        raise RuntimeError("该动作必须提供 --文件")
    路径 = Path(文件参数).resolve()
    if 类型 == "演示文稿":
        if not 路径.is_file() or 路径.suffix.lower() != ".pptx":
            raise RuntimeError("演示文稿必须是已经存在的PPTX文件")
    elif 类型 == "图片目录":
        return 检查图片目录(文件参数)
    return str(路径)


def 检查总结预览(文档参数: str | None, 预览参数: str | None, 报告参数: str | None) -> dict:
    if not 文档参数:
        raise RuntimeError("记录总结预览必须通过 --文件 提供DOCX")
    文档 = Path(文档参数).resolve()
    if not 文档.is_file() or 文档.suffix.lower() != ".docx":
        raise RuntimeError("总结文件必须是已经存在的DOCX文件")

    预览 = 检查图片目录(预览参数, "总结预览")
    if not 报告参数:
        raise RuntimeError("记录总结预览必须提供 --质量报告")
    报告路径 = Path(报告参数).resolve()
    if not 报告路径.is_file():
        raise RuntimeError("总结质量报告不存在")
    报告 = json.loads(报告路径.read_text(encoding="utf-8"))
    if 报告.get("状态") != "通过":
        raise RuntimeError("总结质量报告未通过")
    if 报告.get("文档SHA256") != 文件校验值(文档):
        raise RuntimeError("总结质量报告与当前DOCX不匹配，请重新检查")
    return {"文件": str(文档), "预览": 预览, "质量报告": str(报告路径)}


def 检查确认(确认原文: str | None) -> str:
    if not 确认原文:
        raise RuntimeError("确认动作必须提供用户的 --确认原文")
    if re.search(r"不确认|不同意|不可以|不能|不要|暂不|先不|别生成|别制作|需要修改|还要修改|再改|有问题", 确认原文):
        raise RuntimeError("确认原文包含否定、暂缓或修改要求")
    if not re.search(r"确认|同意|可以.{0,8}(继续|生成|制作)|没问题|通过", 确认原文, re.IGNORECASE):
        raise RuntimeError("确认原文中没有明确同意继续")
    return 确认原文


def main() -> int:
    解析器 = argparse.ArgumentParser(description="强制总结、普通版和深大模板版按三重确认门禁串行生成")
    解析器.add_argument("--状态文件", required=True, type=Path)
    解析器.add_argument("--动作", required=True, choices=["初始化", "状态", *动作规则.keys()])
    解析器.add_argument("--文件")
    解析器.add_argument("--预览")
    解析器.add_argument("--质量报告")
    解析器.add_argument("--确认原文")
    参数 = 解析器.parse_args()

    try:
        if 参数.动作 == "初始化":
            数据 = {"当前阶段": "已初始化", "记录": [], "流程版本": 2}
            保存状态(参数.状态文件, 数据)
            print("通过：生成阶段已初始化")
            return 0

        数据 = 读取状态(参数.状态文件)
        if 参数.动作 == "状态":
            print(json.dumps(数据, ensure_ascii=False, indent=2))
            return 0

        允许前置, 下一阶段, 验证类型 = 动作规则[参数.动作]
        当前阶段 = 数据.get("当前阶段")
        允许集合 = {允许前置} if isinstance(允许前置, str) else set(允许前置)
        if 当前阶段 not in 允许集合:
            raise RuntimeError(f"动作“{参数.动作}”不能在“{当前阶段}”执行；必须先完成规定的前置阶段")

        记录内容: dict = {"动作": 参数.动作}
        if 验证类型 == "确认":
            记录内容["确认原文"] = 检查确认(参数.确认原文)
        elif 验证类型 == "总结预览":
            记录内容.update(检查总结预览(参数.文件, 参数.预览, 参数.质量报告))
        else:
            记录内容["文件"] = 检查普通文件(验证类型, 参数.文件)

        记录内容["时间"] = datetime.now(timezone.utc).isoformat()
        数据["当前阶段"] = 下一阶段
        数据.setdefault("记录", []).append(记录内容)
        数据["流程版本"] = 2
        保存状态(参数.状态文件, 数据)
        print(f"通过：当前阶段为“{下一阶段}”")
        return 0
    except Exception as 错误:
        print(f"错误：{错误}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
