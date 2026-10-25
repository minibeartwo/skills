#!/usr/bin/env python3
"""Render code-backed graph specifications into PNG without running the target.

Drawing primitives adapted from minibeartwo/hello-agents,
Co-creation-projects/minibeartwo-CodeAssistantAgent/backend/analysis_documents.py.
This standalone helper requires only Pillow; no HelloAgents or model API is used.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import sys
import tempfile
from urllib.parse import quote

from PIL import Image, ImageDraw, ImageFont

MAX_FILE = 4 * 1024 * 1024
TYPES = ("architecture", "workflow", "sequence")
COLORS = {"background": "#f6f9ff", "ink": "#173759", "muted": "#506b88",
          "line": "#557dac", "fill": "#e7f0ff", "border": "#5686bf", "gold": "#fff3d3"}

def _object(value, required, optional=(), name="对象"):
    if not isinstance(value, dict) or not set(required) <= value.keys() or not value.keys() <= set(required) | set(optional):
        raise ValueError(f"{name} 必须包含 {list(required)}，且不能包含未知字段。")
    return value


def _text(value, name, maximum=80, *, empty=False):
    if (not isinstance(value, str) or len(value) > maximum or (not empty and not value.strip())
            or any(ord(char) < 32 and char not in "\n\t" for char in value)):
        raise ValueError(f"{name} 必须为{'0' if empty else '1'}–{maximum}字符的文本。")
    return value.strip()


def _id(value):
    value = _text(value, "节点 id", 40)
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,39}", value):
        raise ValueError("图 id 须以英文字母开头，仅使用字母、数字、下划线或连字符。")
    return value


def _font(size):
    override = os.getenv("PROJECT_DIAGRAM_FONT_PATH")
    candidates = ([override] if override else []) + [
        "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/simsun.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", "/System/Library/Fonts/PingFang.ttc",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                pass
    raise ValueError("未找到中文绘图字体。请安装微软雅黑/Noto Sans CJK，或设置 PROJECT_DIAGRAM_FONT_PATH 指向中文字体文件。")


def _wrap(draw, text, font, width):
    lines = []
    for paragraph in text.split("\n"):
        current = ""
        for char in paragraph:
            if current and draw.textlength(current + char, font=font) > width:
                lines.append(current)
                current = char
            else:
                current += char
        lines.append(current)
    return lines


def _label(draw, text, center, width=260, font=None, fill=None, background=False, max_height=None):
    font = font or _font(24)
    lines = _wrap(draw, text, font, width)
    while max_height and len(lines) * (font.size + 7) > max_height and font.size > 8:
        font = _font(font.size - 1)
        lines = _wrap(draw, text, font, width)
    height = len(lines) * (font.size + 7)
    x, y = center
    if background:
        draw.rounded_rectangle((x - width / 2 - 5, y - height / 2 - 3, x + width / 2 + 5, y + height / 2 + 3),
                               radius=5, fill=COLORS["background"])
    for index, line in enumerate(lines):
        draw.text((x - draw.textlength(line, font=font) / 2, y - height / 2 + index * (font.size + 7)),
                  line, font=font, fill=fill or COLORS["ink"])


def _arrow(draw, points, *, dashed=False):
    for start, end in zip(points, points[1:]):
        if dashed:
            distance = math.dist(start, end)
            for offset in range(0, int(distance), 15):
                ratios = (offset / max(distance, 1), min(offset + 8, distance) / max(distance, 1))
                segment = [(start[0] + (end[0] - start[0]) * r, start[1] + (end[1] - start[1]) * r) for r in ratios]
                draw.line(segment, fill=COLORS["line"], width=3)
        else:
            draw.line([start, end], fill=COLORS["line"], width=3)
    tip, previous = points[-1], points[-2]
    angle = math.atan2(tip[1] - previous[1], tip[0] - previous[0])
    draw.polygon([tip, (tip[0] - 14 * math.cos(angle - .4), tip[1] - 14 * math.sin(angle - .4)),
                  (tip[0] - 14 * math.cos(angle + .4), tip[1] - 14 * math.sin(angle + .4))], fill=COLORS["line"])


def _png(image):
    stream = io.BytesIO()
    image.save(stream, format="PNG", optimize=True)
    raw = stream.getvalue()
    if len(raw) > MAX_FILE:
        stream = io.BytesIO()
        image.convert("P", palette=Image.Palette.ADAPTIVE, colors=128).save(stream, format="PNG", optimize=True)
        raw = stream.getvalue()
    if len(raw) > MAX_FILE:
        raise ValueError("图表 PNG 超过 4 MiB，请减少节点、消息或标签。")
    return raw


def _graph(spec):
    _object(spec, ("title", "description", "nodes", "edges"), name="架构/流程图")
    title = _text(spec["title"], "图标题", 80)
    _text(spec["description"], "图说明", 2500)
    if not isinstance(spec["nodes"], list) or not 1 <= len(spec["nodes"]) <= 14:
        raise ValueError("架构/流程图须包含1–14个节点。")
    if not isinstance(spec["edges"], list) or not 0 <= len(spec["edges"]) <= 24:
        raise ValueError("架构/流程图最多24条边。")
    nodes, names = [], set()
    for item in spec["nodes"]:
        _object(item, ("id", "label"), ("level", "kind"), "图节点")
        name = _id(item["id"])
        if name in names:
            raise ValueError("图节点 id 重复。")
        names.add(name)
        level = item.get("level")
        if level is not None and (type(level) is not int or not 0 <= level <= 8):
            raise ValueError("节点 level 必须为0–8的整数。")
        kind = item.get("kind", "process")
        if kind not in {"process", "decision"}:
            raise ValueError("节点 kind 仅支持process或decision。")
        nodes.append({"id": name, "label": _text(item["label"], "节点标签", 80), "level": level, "kind": kind})
    edges = []
    for item in spec["edges"]:
        _object(item, ("from", "to"), ("label",), "图连线")
        source, target = _id(item["from"]), _id(item["to"])
        if source not in names or target not in names:
            raise ValueError("图连线引用不存在的节点。")
        edges.append({"from": source, "to": target, "label": _text(item.get("label", ""), "连线标签", 50, empty=True)})
    # Infer a bounded level for unspecified nodes; cycles get a stable fallback.
    levels = {node["id"]: node["level"] for node in nodes if node["level"] is not None}
    roots = names - {edge["to"] for edge in edges}
    for name in roots:
        levels.setdefault(name, 0)
    for _ in nodes:
        changed = False
        for edge in edges:
            if edge["from"] in levels and edge["to"] not in levels:
                levels[edge["to"]] = min(8, levels[edge["from"]] + 1)
                changed = True
        if not changed:
            break
    groups = {}
    for node in nodes:
        groups.setdefault(levels.get(node["id"], 0), []).append(node)
    rows = []
    for _, group in sorted(groups.items()):
        rows.extend(group[start:start + 3] for start in range(0, len(group), 3))
    width, height = 1440, max(430, 170 + len(rows) * 180)
    if height > 2600:
        raise ValueError("图表层级超过安全画布范围。")
    image = Image.new("RGB", (width, height), COLORS["background"])
    draw = ImageDraw.Draw(image)
    _label(draw, title, (width / 2, 55), width=1260, font=_font(34))
    positions = {}
    for row_index, row in enumerate(rows):
        spacing = width / (len(row) + 1)
        for col, node in enumerate(row):
            positions[node["id"]] = (int(spacing * (col + 1)), 180 + row_index * 180)
    geometry = {node["id"]: ((166, 67) if node["kind"] == "decision" else (155, 57))
                for node in nodes}
    for index, edge in enumerate(edges):
        sx, sy = positions[edge["from"]]
        tx, ty = positions[edge["to"]]
        sw, sh = geometry[edge["from"]]
        tw, th = geometry[edge["to"]]
        label_width = 200
        if edge["from"] == edge["to"]:
            points = [(sx + sw, sy), (sx + sw + 25, sy), (sx + sw + 25, sy + 85),
                      (sx, sy + 85), (sx, sy + sh)]
            label = (sx + 80, sy + 105)
        elif sy < ty and ty - sy == 180:
            mid = (sy + ty) / 2
            points = [(sx, sy + sh), (sx, mid), (tx, mid), (tx, ty - th)]
            label = ((sx + tx) / 2, mid - 16)
        elif sy == ty and abs(tx - sx) < 600:
            direction = 1 if sx < tx else -1
            points = [(sx + sw * direction, sy), (tx - tw * direction, ty)]
            label = ((sx + tx) / 2, sy - 21)
        elif sy == ty:
            # A same-row edge spanning a middle node must use the row gap.
            mid = sy + 90
            points = [(sx, sy + sh), (sx, mid), (tx, mid), (tx, ty + th)]
            label = ((sx + tx) / 2, mid + 16)
        else:
            # Long forward edges and back edges use an outer gutter and
            # row gaps rather than crossing intermediate boxes or labels.
            right = sx + tx > width
            lane = width - 45 - (index % 4) * 16 if right else 45 + (index % 4) * 16
            outgoing, incoming = sy + 90, ty - 90
            direction = 1 if right else -1
            elbow = sx + direction * (sw + 18)
            points = [(sx + direction * sw, sy), (elbow, sy), (elbow, outgoing),
                      (lane, outgoing), (lane, incoming), (tx, incoming), (tx, ty - th)]
            label = (width - 120 if right else 120, (sy + ty) / 2)
            label_width = 160
        _arrow(draw, points)
        if edge["label"]:
            _label(draw, edge["label"], label, label_width, _font(18), background=True, max_height=54)
    for node in nodes:
        x, y = positions[node["id"]]
        if node["kind"] == "decision":
            draw.polygon([(x, y - 67), (x + 166, y), (x, y + 67), (x - 166, y)],
                         fill=COLORS["gold"], outline=COLORS["border"], width=3)
            label_width = 230
        else:
            draw.rounded_rectangle((x - 155, y - 57, x + 155, y + 57), radius=15,
                                   fill=COLORS["fill"], outline=COLORS["border"], width=3)
            label_width = 280
        _label(draw, node["label"], (x, y), label_width, _font(23),
               max_height=85 if node["kind"] == "decision" else 98)
    return _png(image)


def _sequence(spec):
    _object(spec, ("title", "description", "participants", "messages"), name="时序图")
    title = _text(spec["title"], "图标题", 80)
    _text(spec["description"], "图说明", 2500)
    if not isinstance(spec["participants"], list) or not 1 <= len(spec["participants"]) <= 7:
        raise ValueError("时序图须包含1–7个参与者。")
    if not isinstance(spec["messages"], list) or not 1 <= len(spec["messages"]) <= 20:
        raise ValueError("时序图须包含1–20条消息。")
    actors = {}
    for item in spec["participants"]:
        _object(item, ("id", "label"), name="时序参与者")
        name = _id(item["id"])
        if name in actors:
            raise ValueError("时序参与者 id 重复。")
        actors[name] = _text(item["label"], "参与者标签", 50)
    messages = []
    for item in spec["messages"]:
        _object(item, ("from", "to", "label"), ("dashed",), "时序消息")
        source, target = _id(item["from"]), _id(item["to"])
        if source not in actors or target not in actors:
            raise ValueError("时序消息引用不存在的参与者。")
        dashed = item.get("dashed", False)
        if type(dashed) is not bool:
            raise ValueError("时序消息 dashed 必须为布尔值。")
        messages.append((source, target, _text(item["label"], "消息标签", 100), dashed))
    width, height = max(1080, len(actors) * 230 + 100), 220 + len(messages) * 92
    image = Image.new("RGB", (width, height), COLORS["background"])
    draw = ImageDraw.Draw(image)
    _label(draw, title, (width / 2, 50), width=width - 100, font=_font(34))
    positions = {name: 90 + index * (width - 180) / max(1, len(actors) - 1) for index, name in enumerate(actors)}
    for name, label in actors.items():
        x = positions[name]
        if len(actors) == 1:
            x = positions[name] = width / 2
        _arrow(draw, [(x, 175), (x, height - 35)], dashed=True)
        draw.rounded_rectangle((x - 85, 105, x + 85, 175), radius=12,
                               fill=COLORS["fill"], outline=COLORS["border"], width=3)
        _label(draw, label, (x, 140), 155, _font(22), max_height=60)
    for index, (source, target, label, dashed) in enumerate(messages):
        sx, tx, y = positions[source], positions[target], 230 + index * 92
        if source == target:
            direction = -1 if sx + 210 > width else 1
            points = [(sx, y), (sx + direction * 100, y),
                      (sx + direction * 100, y + 30), (sx, y + 30)]
            center = (sx + direction * 105, y - 18)
        else:
            points = [(sx, y), (tx, y)]
            center = ((sx + tx) / 2, y - 27)
        _arrow(draw, points, dashed=dashed)
        _label(draw, label, center, min(700, max(200, abs(tx - sx) - 20)), _font(20),
               background=True, max_height=64)
    return _png(image)



def _evidence(spec, project_root, selected):
    entries = spec.get("evidence")
    if not isinstance(entries, list) or not 1 <= len(entries) <= 100:
        raise ValueError("evidence 须包含1–100条真实代码依据。")
    result, covered, line_counts = [], set(), {}
    for item in entries:
        _object(item, ("path", "start_line", "end_line", "supports", "note"), name="代码依据")
        relative = _text(item["path"], "依据路径", 500).replace(chr(92), "/")
        path_parts = PurePosixPath(relative).parts
        if (PurePosixPath(relative).is_absolute() or PureWindowsPath(relative).drive
                or ".." in path_parts or not path_parts):
            raise ValueError("依据路径必须为项目内的相对文件路径，不能包含 ..。")
        path = (project_root / relative).resolve(strict=True)
        if not path.is_relative_to(project_root) or not path.is_file():
            raise ValueError(f"代码依据不是项目内的文件：{relative}")
        if any(part.lower() in {".git", ".venv", "venv", "node_modules", "__pycache__"}
               for part in path.relative_to(project_root).parts):
            raise ValueError(f"代码依据不能来自依赖、缓存或 Git 目录：{relative}")
        name = path.name.lower()
        if (name == ".env" or (name.startswith(".env.") and not name.endswith(".example"))
                or path.suffix.lower() in {".pem", ".key", ".sqlite", ".sqlite3", ".db"}):
            raise ValueError(f"代码依据不能使用密钥或数据库文件：{relative}")
        start, end = item["start_line"], item["end_line"]
        if type(start) is not int or type(end) is not int or not 1 <= start <= end:
            raise ValueError(f"代码依据行号无效：{relative}")
        if path not in line_counts:
            if path.stat().st_size > 2 * 1024 * 1024:
                raise ValueError(f"单条依据文件超过2 MiB，请使用相关入口或拆分后的实际模块：{relative}")
            line_counts[path] = len(path.read_text(encoding="utf-8-sig").splitlines())
        if end > line_counts[path]:
            raise ValueError(f"代码依据行号超过文件真实范围：{relative}:{start}–{end}")
        supports = item["supports"]
        if (not isinstance(supports, list) or not supports
                or any(not isinstance(kind, str) or kind not in TYPES for kind in supports)):
            raise ValueError("evidence.supports 只能包含 architecture、workflow、sequence。")
        covered.update(supports)
        result.append({"path": relative, "resolved": path, "start_line": start, "end_line": end,
                       "supports": supports, "note": _text(item["note"], "依据说明", 800)})
    missing = set(selected) - covered
    if missing:
        raise ValueError("以下图缺少代码依据：" + "、".join(sorted(missing)))
    return result


def _notes(spec, evidence, selected, output_dir):
    sections = ["# " + spec["project"] + " · 项目设计图",
                "以下图表依据项目文件静态整理；未执行目标项目、测试或构建。"]
    for kind in selected:
        item = spec[kind]
        sections.append(f"## {item['title'].strip()}\n\n{item['description'].strip()}\n\n![{kind}]({kind}.png)")
    sections.append("## 代码依据")
    for item in evidence:
        if not set(item["supports"]).intersection(selected):
            continue
        label = f"{item['path']}:L{item['start_line']}–L{item['end_line']}"
        try:
            relative = Path(os.path.relpath(item["resolved"], output_dir)).as_posix()
        except ValueError:  # Different Windows drives have no relative hyperlink.
            location = "`" + label + "`"
        else:
            location = f"[{label}]({quote(relative, safe='/')}#L{item['start_line']}-L{item['end_line']})"
        sections.append(f"- {location}：{item['note']}")
    sections.append("## 未验证或未覆盖范围")
    limitations = spec.get("limitations", [])
    sections.extend("- " + item for item in limitations)
    if not limitations:
        sections.append("- 图表反映已读取文件；未验证运行时行为。")
    return ("\n\n".join(sections) + "\n").encode("utf-8")


def _snapshot(path):
    if path.is_symlink():
        raise ValueError(f"拒绝覆盖链接文件：{path}")
    if not path.exists():
        return None
    if not path.is_file() or path.stat().st_size > MAX_FILE:
        raise ValueError(f"已有输出不是文件或超过4 MiB：{path}")
    return path.read_bytes()


def _atomic_write(path, data):
    handle, temporary = tempfile.mkstemp(prefix=".project-diagrams-", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def generate(spec, project_root, output_dir, selected=TYPES, *, overwrite=False, validate_only=False):
    project_root, output_dir = Path(project_root).resolve(strict=True), Path(output_dir).resolve()
    if not project_root.is_dir():
        raise ValueError("project-root 必须为真实项目目录。")
    skill_root = Path(__file__).resolve().parent.parent
    if output_dir == project_root or output_dir.is_relative_to(skill_root):
        raise ValueError("请选择独立的图表输出目录，不要使用项目根目录或技能包内部目录。")
    _object(spec, ("project", "evidence"), (*TYPES, "limitations"), "图表计划")
    spec = {**spec, "project": _text(spec["project"], "项目名称", 120)}
    if (not isinstance(selected, (list, tuple)) or not selected or len(set(selected)) != len(selected)
            or any(kind not in TYPES for kind in selected)):
        raise ValueError("types 必须为不重复的有效图类型。")
    for kind in selected:
        if kind not in spec:
            raise ValueError(f"缺少图字段：{kind}")
    limitations = spec.get("limitations", [])
    if not isinstance(limitations, list) or len(limitations) > 30:
        raise ValueError("limitations 必须为最多30项的文本列表。")
    spec["limitations"] = [_text(item, "未覆盖说明", 1000) for item in limitations]
    evidence = _evidence(spec, project_root, selected)
    names = [kind + ".png" for kind in selected] + ["README.md"]
    # Capture versions before rendering, then check all versions before writing.
    before = {name: _snapshot(output_dir / name) for name in names}
    if not validate_only and not overwrite and any(value is not None for value in before.values()):
        raise ValueError("输出已存在。确认需要更新后使用 --overwrite，或指定新的输出目录。")
    files = {kind + ".png": (_sequence(spec[kind]) if kind == "sequence" else _graph(spec[kind]))
             for kind in selected}
    files["README.md"] = _notes(spec, evidence, selected, output_dir)
    if validate_only:
        return {"status": "validated", "types": list(selected), "evidence_count": len(evidence)}
    for name in names:
        if _snapshot(output_dir / name) != before[name]:
            raise ValueError(f"生成期间输出发生变化，未写入：{name}")
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    try:
        for name, data in files.items():
            path = output_dir / name
            if _snapshot(path) != before[name]:
                raise ValueError(f"写入前检测到输出版本冲突：{name}")
            if data != before[name]:
                _atomic_write(path, data)
                written.append(name)
    except BaseException as exc:
        unrecovered = []
        for name in reversed(written):
            path = output_dir / name
            try:
                # Do not erase a third party's edit while rolling back our writes.
                if _snapshot(path) != files[name]:
                    unrecovered.append(name)
                elif before[name] is None:
                    path.unlink()
                else:
                    _atomic_write(path, before[name])
            except (OSError, ValueError):
                unrecovered.append(name)
        if unrecovered:
            raise RuntimeError("写入失败，以下文件因外部修改或恢复错误需人工核对：" + "、".join(unrecovered)) from exc
        raise
    return {"status": "written", "output_dir": str(output_dir), "types": list(selected),
            "files": [{"path": str(output_dir / name), "sha256": hashlib.sha256(data).hexdigest()}
                      for name, data in files.items()]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--spec", required=True, type=Path, help="UTF-8 JSON 图表计划")
    parser.add_argument("--project-root", required=True, type=Path, help="只读分析的真实项目目录")
    parser.add_argument("--output-dir", type=Path, help="默认使用项目 docs/diagrams")
    parser.add_argument("--types", nargs="+", choices=TYPES, default=list(TYPES))
    parser.add_argument("--font", type=Path, help="中文字体文件；也可设 PROJECT_DIAGRAM_FONT_PATH")
    parser.add_argument("--overwrite", action="store_true", help="更新已有输出，仍检查生成期间的版本冲突")
    parser.add_argument("--validate-only", action="store_true", help="校验代码依据、图结构和渲染，不写文件")
    args = parser.parse_args(argv)
    try:
        if args.spec.stat().st_size > 256 * 1024:
            raise ValueError("图表计划超过256 KiB，请聚合模块并精简说明。")
        spec = json.loads(args.spec.read_text(encoding="utf-8-sig"))
        if args.font:
            if not args.font.is_file():
                raise ValueError("指定的中文字体文件不存在。")
            os.environ["PROJECT_DIAGRAM_FONT_PATH"] = str(args.font.resolve())
        output_dir = args.output_dir or args.project_root / "docs" / "diagrams"
        result = generate(spec, args.project_root, output_dir, args.types,
                          overwrite=args.overwrite, validate_only=args.validate_only)
    except (ValueError, OSError, RuntimeError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
