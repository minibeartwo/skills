# 项目结构与运行配置

## 一、必须保留的项目结构

```text
└── project/
    ├── 修改计划.md
    ├── environment/
    ├── dataset/
    │   ├── raw/
    │   │   ├── dataset1/
    │   │   └── dataset2/
    │   ├── processed/
    │   │   ├── process1/
    │   │   │   ├── dataset1/
    │   │   │   └── dataset2/
    │   │   └── process2/
    │   │       ├── dataset1/
    │   │       └── dataset2/
    │   ├── dataset1Split-process1.csv
    │   ├── dataset1Split-process2.csv
    │   ├── dataset2Split-process1.csv
    │   └── dataset2Split-process2.csv
    └── code/
        ├── preprocess-code/
        │   ├── config.yaml
        │   ├── processCode1.py
        │   └── processCode2.py
        ├── train-code/
        │   ├── outputs/
        │   │   └── checkpoints/
        │   │       ├── trainCode1/
        │   │       │   ├── best/
        │   │       │   │   ├── dataset1_exp001_best.pt
        │   │       │   │   └── dataset2_exp001_best.pt
        │   │       │   ├── periodic/
        │   │       │   │   ├── dataset1_exp001_epoch-0050.pt
        │   │       │   │   └── dataset1_exp001_epoch-0100.pt
        │   │       │   └── latest/
        │   │       │       ├── dataset1_exp001_latest.pt
        │   │       │       └── dataset2_exp001_latest.pt
        │   │       └── trainCode2/
        │   │           ├── best/
        │   │           │   └── dataset1-dataset2_exp001_best.pt
        │   │           ├── periodic/
        │   │           └── latest/
        │   ├── config.yaml
        │   ├── trainCode1.py
        │   └── trainCode2.py
        ├── evaluation-code/
        │   ├── outputs/
        │   │   ├── evalution1/
        │   │   │   ├── dataset1_exp001_best_metrics_20261109.csv
        │   │   │   ├── dataset1_exp001_best_predictions_20261109.csv
        │   │   │   ├── dataset1_exp001_best_config_20261109.yaml
        │   │   │   └── dataset2_exp002_epoch-0200_metrics_20261109.csv
        │   │   └── evalution2/
        │   │       ├── dataset1-dataset2_exp001_best_metrics_20261109.csv
        │   │       └── dataset1-dataset2_exp001_best_config_20261109.yaml
        │   ├── config.yaml
        │   └── evaluationCode.py
        └── inference-code/
            ├── outputs/
            │   ├── inference1/
            │   │   ├── dataset1_exp001_best_case001_20261109.png
            │   │   ├── dataset1_exp001_best_case002_20261109.png
            │   │   ├── dataset1_exp001_best_config_20261109.yaml
            │   │   └── dataset2_exp002_epoch-0200_case001_20261109.png
            │   └── inference2/
            │       └── dataset1_exp003_best_case001_20261109.png
            ├── config.yaml
            └── inferenceCode.py
```

这是**唯一基准结构模板，目录树仅以两套方法演示命名形式，并非要求实际生成两套方法**。`project/修改计划.md` 是任务执行前的计划与确认文件，不是实验输出。保留已使用的文件名及目录名（包括原有的 `evalution` 拼写），不为所谓“模块化”增加多余层级。通用规则是：`evalutionN`、`inferenceN` 固定对应**方法 N**，编号代表方法而非第几次运行。实际只有方法 1 时只保留其对应部分；若存在方法 3、方法 4 等，则按同样命名规则扩展 `processCodeN.py`、`trainCodeN.py` 及各自对应的既有类型输出目录，**不创建不存在或未经确认的方法**。树中的 `.pt`、`.csv`、`.png`、`.yaml` 结果文件是**命名示例，并非要求预先生成的文件**；其中 `20261109` 只是日期格式示例，实际结果使用运行当天的 `YYYYMMDD`。真实文件类型应与任务匹配。未经用户确认，不新增其他编号或改变编号含义。

## 项目 Conda 环境

- 在项目根目录下使用 `environment/` 作为 Conda 环境的安装路径。在修改计划中列明 Python 版本、项目运行依赖和安装方式，获批后创建环境并安装依赖。
- 已有 Conda 环境清单时，从项目根目录运行 `conda env create --prefix ./environment --file <清单路径>`。按包创建时，运行 `conda create --prefix ./environment python=<版本> <所需的 Conda 包>`。这些命令中的占位符应替换为项目实际值。
- 从项目根目录运行 `conda activate ./environment`。运行这条命令需要终端已启用 Conda。其他目录可使用 `conda activate "<项目根目录绝对路径>/environment"`。
- 将项目所需的 Python 和运行库装入此环境。用 Conda 补装依赖时指定 `--prefix ./environment`，用 pip 时在激活后运行 `python -m pip`，并核对当前解释器位于 `environment/` 下。系统级依赖（如 GPU 驱动）在修改计划中注明。
- 对 Git 项目，将生成的 `/environment/` 加入忽略规则，依赖清单按项目现有约定管理。

### ⑤ 所有超参数只放在当前阶段的 config.yaml

- 四个阶段分别维护自己的 `config.yaml`，不得在运行命令后增加一系列 `--dataset`、`--epochs`、`--batch-size` 等参数。
- `preprocess-code/config.yaml` 负责数据集选择、输入输出位置、预处理参数；`train-code/config.yaml` 负责训练方法、数据集、优化器、学习率、Epoch、Batch Size、设备、随机种子、Checkpoint 策略及断点恢复；`evaluation-code/config.yaml` 与 `inference-code/config.yaml` 各自负责方法、具体权重与本阶段运行参数。
- `train-code/config.yaml` 中每套训练方法都必须包含 `dataset_mode`（只能为 `single` 或 `joint`）和 `datasets`（明确列出数据集编号）：`single` 要求 `datasets` 恰好含一个数据集；`joint` 要求至少两个明确列出的数据集。配置缺失或矛盾时直接报错，不自行推断训练模式。联合训练仍须逐数据集使用各自编号所对应的固定 CSV，并严格隔离训练、验证、测试样本。
- 同一 `train-code/config.yaml` 仅需包含**实际存在的 `trainCodeN` 方法配置**，各编号独立；运行 `trainCodeN.py` 时只能读取其对应配置，不得误读其他方法参数。不应为了补齐示例中的两个方法而创建多余配置段。
- **必须支持无附加超参数的直接运行**：

以下命令只演示方法 1、方法 2；实际项目只运行已存在的入口。若有方法 3 等，按相同规则直接运行 `python processCode3.py`、`python trainCode3.py`，不增加额外 CLI 超参数。

```bash
python processCode1.py
python processCode2.py
python trainCode1.py
python trainCode2.py
python evaluationCode.py
python inferenceCode.py
```

- 所有路径以脚本或配置文件所在位置为基准可靠解析，不依赖终端当前工作目录。缺失配置、非法编号或路径错误，应及时报错。

### ⑥ 所有运行结果只保存到规定的位置

- 预处理阶段有且仅有两类目录例外：任意实际存在的 `processCodeN.py` 的处理后数据保存到 `dataset/processed/processN/`，以及该方法与每个所选数据集对应的固定划分 CSV 保存到 `dataset/` 根目录；两者均不得写入预处理代码所在目录。
- 任意实际存在的 `trainCodeN.py` 生成的权重、日志、曲线、统计结果等全部保存在 `train-code/outputs/` 内；Checkpoint 按方法 N 保存到 `checkpoints/trainCodeN/{best,periodic,latest}`，不要求创建不存在的方法的输出目录。
- `evaluationCode.py` 选择方法 N 时只写入 `evaluation-code/outputs/evalutionN/`。
- `inferenceCode.py` 选择方法 N 时只写入 `inference-code/outputs/inferenceN/`。
- **不得在其他目录生成代码主动写出的中间实验文件或最终结果；尤其不得污染 `raw/`、源码所在目录或其他阶段的输出目录。** Python 自身的字节码缓存不视为实验结果；若必须禁用该缓存，可单独设置运行环境。
- 不新增 `logs/`、`figures/`、`experiments/` 等额外层级。需要区分日志或实验时，在现有 `outputs/` 目录中用明确文件名管理。
