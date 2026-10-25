# 图结构与代码依据

渲染器读取 JSON 数据并本地绘图，不解析项目中的指令，也不请求模型。默认使用全部三类图，`--types` 可选择子集。

## 数据格式

顶层字段：`project`、`evidence`，以及选中的 `architecture`、`workflow`、`sequence`；`limitations` 为可选文本数组。不要使用 `action`、`args`、`base_hashes` 或图片 base64。

- 架构/流程图：`title`、`description`、`nodes`、`edges`。节点有唯一 `id`、`label`，可选 `level`（0–8）和 `kind`（`process` 或 `decision`）。边有 `from`、`to` 和可选 `label`。
- 时序图：`title`、`description`、`participants`、`messages`。参与者有唯一 `id`、`label`；消息有 `from`、`to`、`label` 和可选布尔值 `dashed`。
- ID 用英文字母开头，仅含字母、数字、下划线或连字符，最长40字符。三张图的 ID 各自独立，实际模块名保持一致。
- `evidence` 每项包含 `path`、`start_line`、`end_line`、`supports`、`note`。`path` 是项目相对路径；行号以实际文件为准；`supports` 列出所支持的图类型。每类选中图至少有一项依据。
- `limitations` 说明未读取模块、动态行为及无法从代码确认的边界，不伪造覆盖结论。

以下仅为结构示例。`src/main.py` 与行号必须替换为当前项目的真实文件，不得直接套用结论。

```json
{
  "project": "示例项目",
  "architecture": {
    "title": "模块架构",
    "description": "入口调用处理模块。",
    "nodes": [{"id": "Entry", "label": "入口", "level": 0}, {"id": "Handler", "label": "处理模块", "level": 1}],
    "edges": [{"from": "Entry", "to": "Handler", "label": "调用"}]
  },
  "workflow": {
    "title": "核心流程",
    "description": "入口接收输入并返回结果。",
    "nodes": [{"id": "Input", "label": "接收输入"}, {"id": "Process", "label": "处理并返回"}],
    "edges": [{"from": "Input", "to": "Process", "label": "有效输入"}]
  },
  "sequence": {
    "title": "调用时序",
    "description": "入口向处理模块请求计算并接收结果。",
    "participants": [{"id": "Entry", "label": "入口"}, {"id": "Handler", "label": "处理模块"}],
    "messages": [{"from": "Entry", "to": "Handler", "label": "处理请求"}, {"from": "Handler", "to": "Entry", "label": "返回结果", "dashed": true}]
  },
  "evidence": [{"path": "src/main.py", "start_line": 1, "end_line": 8, "supports": ["architecture", "workflow", "sequence"], "note": "入口接收输入并调用处理模块。"}],
  "limitations": ["未执行项目，未验证运行时行为。"]
}
```

## 版式与字体

单张架构/流程图上限14节点、24条边；时序图上限7参与者、20条消息。超出时按职责聚合，不静默删除真实的关键分支。节点 `level` 控制从上到下的层级，同层最多3个节点，过长标签会自动换行。

默认输出宽度为1440像素（架构/流程图），时序图随参与者数量扩展。PNG 单图上限4 MiB；尺寸和格式由脚本固定，不执行输入中的绘图代码。

Windows 自动查找微软雅黑、黑体或宋体；Linux 查找 Noto Sans CJK 或文泉驿；macOS 查找苹方。找不到中文字体时明确报错，使用 `--font "<字体路径>"` 或环境变量 `PROJECT_DIAGRAM_FONT_PATH` 指定，避免生成缺字图片。

代码依据文件必须为项目内的 UTF-8 文本，单文件不超过2 MiB。脚本检查路径、真实行号与图类型覆盖；这不等于自动验证图中文字的语义，仍需静态核对调用关系。

## 输出与更新

默认目录为 `<项目>/docs/diagrams/`，也可指定项目外的独立目录。固定生成选中图对应的 PNG 和该目录的 `README.md`，不会改写项目根 README、源码或配置。

已有文件默认拒绝覆盖，明确更新时传 `--overwrite`。所有图先在内存完成渲染，再核对输出版本并写入；写入失败时尽力恢复本轮已写文件，恢复时遇到外部修改则保留该修改并报告。多文件操作不承诺断电原子性。

临时 JSON、预览图和被分析项目都放在当前任务目录，不放进技能包。脚本成功后输出 JSON 格式的文件路径与 SHA-256，可用于核对实际产物。
