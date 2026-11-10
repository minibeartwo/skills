# 评估、推理与结果保存

### ④ 统一评估与推理代码，通过 config 精确选模型

- 所有方法共用一个 `evaluationCode.py` 和一个 `inferenceCode.py`，**不新增 `evaluationCode1.py`、`inferenceCode2.py` 等按方法拆分的入口**。
- `evaluation-code/config.yaml` 和 `inference-code/config.yaml` 必须能够配置：方法编号（1/2）、选定数据集（单个或联合评估时的多个数据集）、**具体 Checkpoint 文件路径**以及本阶段需要的参数。
- **`evaluationCode.py` 只负责测试集（`test`）的最终评估**，必须根据选定数据集对应 CSV 的固定划分选取测试样本，不得默认读取 `train` 或 `val` 样本，也不得重新划分。训练期间的验证集（`val`）评估由对应 `trainCode1.py` / `trainCode2.py` 内部完成，用于模型选择；测试集结果不得参与选择 `best` 权重。
- 统一入口根据配置选择 `trainCode1.py` 或 `trainCode2.py` 中**已经定义好的模型构建/加载函数**；只加载选定方法的实现，不得随意复用另一方法，也不得在评估/推理代码中另造一份不同的模型结构。
- **评估与推理输入必须与方法编号保持一致**：方法 1 使用 `dataset/processed/process1/<dataset_id>/`，方法 2 使用 `dataset/processed/process2/<dataset_id>/`。不得让方法 2 的模型读取 process1 数据，反之亦然。
- 模型 Checkpoint 必须包含训练时实际使用的模型结构参数及必要的配置，使评估、推理能按该 Checkpoint 对应的结构构建模型，**不能简单依赖后来可能已修改的 `train-code/config.yaml`**。读取时检查方法、数据集组合、模型结构与权重是否匹配；不匹配或文件不存在应明确报错，不能自动换模型，也不能静默忽略不匹配的参数。
- 评估用于有真实标签/参考图像的数据并计算指标；推理用于生成预测结果，可以没有真实标签。两者的输出均写入各自 `outputs/`。
- **联合评估**是对配置指定的多个数据集（如 dataset1 + dataset2）各自固定的**测试集**一起计算评估结果，而不是对各数据集分别生成同名文件；联合训练模型的联合评估使用一个汇总结果文件，例如`dataset1-dataset2_exp001_best_metrics_20261109.csv`。联合数据集的指标如何汇总必须沿用已明确的算法定义；无法确定时写入 `修改计划.md` 请求确认，不擅自决定加权方式。
- 每次评估和推理在各自已有的 `outputs/evalutionN/`、`outputs/inferenceN/` 内保存**实际生效的配置快照**，同时记录所用 Checkpoint 的确切路径及模型文件信息，以保证后来修改 YAML 也能追溯当次运行。不新增专门的配置、元数据文件夹；命名示例见[项目结构与运行配置](project-layout.md)。


### ⑧ evalutionN 和 inferenceN 的编号固定代表方法编号

- `evalution1/` 只能保存方法 1 的评估结果，`evalution2/` 只能保存方法 2 的评估结果。
- `inference1/` 只能保存方法 1 的推理结果，`inference2/` 只能保存方法 2 的推理结果。
- 共用的 `evaluationCode.py`、`inferenceCode.py` 根据配置中选定的方法编号，自动选择对应的输出目录；不能把方法 1 的结果写入编号 2 的目录，反之亦然。
- **同一方法已成功保存的评估或推理结果必须保留，不新增任何子目录**；在对应的 `evalutionN/` 或 `inferenceN/` 内，使用不同文件名区分数据集、训练实验编号、所用模型权重及结果类型。若同一天发生文件名冲突，则本次运行报错，不得为了保留本次结果而覆盖旧文件。
- 单数据集结果使用文件名规则 `<dataset_id>_<experiment_id>_<checkpoint_id>_<result_type>_<YYYYMMDD>.<ext>`；**联合评估的汇总结果**使用 `<dataset1-dataset2>_<experiment_id>_<checkpoint_id>_<result_type>_<YYYYMMDD>.<ext>`，例如 `dataset1-dataset2_exp001_best_metrics_20261109.csv`，该文件对应两个数据集共同参与的一次联合评估。其中 `checkpoint_id` 可为 `best`、`latest`、`epoch-0200` 等能够准确指向选定权重的标识；对逐样本推理结果，在日期前加入样本标识（例如 `case001`）。
- 日期后缀**仅精确到年月日**，格式固定为 `YYYYMMDD`，不追加时分秒、不自动添加运行序号。同一天使用相同数据集、实验、权重及结果类型再次运行时，如果目标文件名已存在，必须**明确报错并停止本次写入**，不得静默覆盖，也不得自动改名。
- 评估和推理正式写入结果前，必须先确定本次将生成的目标文件名并**统一检查是否有命名冲突**；如存在冲突，应在写入任何本次结果文件前停止并报错，避免已写入部分结果后才发现重名。不得通过新增文件夹或自动改名规避冲突。
- 命名示例见[项目结构与运行配置](project-layout.md)。文件扩展名按实际数据格式确定。
- 不同数据集、训练实验或模型权重的结果不得互相覆盖。若生成的目标文件名已经存在，不能静默覆盖；应明确报告冲突，并由用户确认如何处理，不得擅自新增编号层级。
