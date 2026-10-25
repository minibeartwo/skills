# Skills

可复用的 AI 技能包集合。每个技能在仓库根目录使用独立文件夹，包含 `SKILL.md` 和所需的脚本、参考资料与模板。

## 技能列表

| 技能 | 用途 |
| --- | --- |
| [literature-summary-ppt](literature-summary-ppt/README.md) | 完整阅读学术文献，先确认中文极简总结，再串行生成普通版与深圳大学模板版文献汇报 PPT。 |
| [annotate-project-zh](annotate-project-zh/SKILL.md) | 为完整项目原地补充五项中文文件头及逐函数三项说明，解释全部参数、返回结果和专业术语，并提供 Python 函数注释覆盖检查。 |
| [project-diagrams-zh](project-diagrams-zh/SKILL.md) | 根据项目真实代码生成中文架构图、流程图和时序图 PNG，附图说明与代码依据，无需模型生图能力。 |

## 安装

下载仓库或运行：

```bash
git clone https://github.com/minibeartwo/skills.git
```

将所需技能的整个目录安装到客户端配置的个人 Skills 目录，保留其内部结构。例如，安装文献汇报技能时应复制整个 `literature-summary-ppt/`，而不是仅复制 `SKILL.md`。

也可以让支持 GitHub 技能安装的客户端从以下目录安装：

<https://github.com/minibeartwo/skills/tree/main/literature-summary-ppt>

<https://github.com/minibeartwo/skills/tree/main/annotate-project-zh>

<https://github.com/minibeartwo/skills/tree/main/project-diagrams-zh>

安装后按客户端要求重新加载技能或开启新对话。每个技能的执行规则见对应 `SKILL.md`；额外的运行条件、使用示例和校验命令见技能目录中的 `README.md`（如有）。

## 目录约定

- `SKILL.md`：技能触发条件与执行指令。
- `agents/`：客户端展示配置。
- `references/`：工作流规则、原始提示词与来源文件。
- `scripts/`：辅助脚本和自动校验。
- `assets/`：执行所需模板等资源。

论文、生成成果、预览图、运行状态及缓存保存在任务目录中，不作为技能包的一部分提交。
