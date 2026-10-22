# 数据与模型流水线

脚本按编号执行。训练与评估产物写入 `data/`，文档图表写入 `docs/assets/figures/`。

| 脚本 | 作用 | 主要输入 | 主要输出 |
|---|---|---|---|
| `01_clean_data.py` | 字段规范化、异常值清洗、派生特征 | `data/new.csv` | `clean.csv`、`clean.parquet`、清洗报告 |
| `02_eda.py` | 8 张探索性分析图与摘要 | `clean.parquet` | `docs/assets/figures/`、EDA 说明 |
| `03_train.py` | ES-1～ES-4 五模型基线实验 | `clean.parquet` | `metrics_v1.json`、实验模型 |
| `04_tune.py` | ratio 口径超参数搜索与重训 | `clean.parquet` | `metrics_tuned_v1.json`、调参模型 |
| `05_stability.py` | 3 种子稳定性、部署模型、区间校准 | `clean.parquet`、调参指标 | `stability_v1.json`、部署模型 |

执行顺序：

```powershell
.\.venv\Scripts\python.exe scripts\01_clean_data.py
.\.venv\Scripts\python.exe scripts\02_eda.py
.\.venv\Scripts\python.exe scripts\03_train.py
.\.venv\Scripts\python.exe scripts\04_tune.py
.\.venv\Scripts\python.exe scripts\05_stability.py
```

`scripts/config/` 存放清洗脚本使用的行政区映射配置。
