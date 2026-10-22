# 数据目录说明

本目录混合存放公开数据集、清洗结果、实验指标与本地模型产物。大文件默认不入库。

| 路径 | 说明 | Git |
|---|---|---|
| `new.csv` | Kaggle 原始北京链家数据（GBK） | 忽略 |
| `clean.csv` | 清洗后 UTF-8-SIG 数据，供 Excel 查看 | 忽略 |
| `clean.parquet` | 建模与后端导入使用的清洗数据 | 忽略 |
| `cleaning_report.json` | 清洗过程与数据质量报告 | 跟踪 |
| `feature_columns_v1.json` | 冻结特征列定义 | 跟踪 |
| `metrics_v1.json` | ES-1～ES-4 基线实验指标 | 跟踪 |
| `metrics_tuned_v1.json` | 调参后指标 | 跟踪 |
| `stability_v1.json` | 3 种子稳定性与区间校准结果 | 跟踪 |
| `train_log.txt` / `tune_log.txt` | 训练与调参日志 | 跟踪 |
| `models/tuned_rf_es3.joblib` | 系统部署模型 | 忽略 |

## 数据约定

- 原始数据下载后命名为 `new.csv`。
- 训练和 API 统一读取 `clean.parquet`。
- 模型与大数据文件不提交到 GitHub。
- 部署模型缺失时，运行 `scripts/04_tune.py` 与 `scripts/05_stability.py` 重建。
