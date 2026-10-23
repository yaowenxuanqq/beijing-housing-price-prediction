# beijing-housing-price-prediction

**基于机器学习的房价预测与可视化分析系统设计与实现**

本科毕业设计项目。基于北京链家二手房成交数据（2011–2017，317,718 条清洗后记录），完成数据清洗、EDA、四组模型实验、Django API 与 Vue 可视化系统。

## 当前状态

| 模块 | 状态 | 说明 |
|---|---|---|
| 数据清洗与 EDA | 已完成 | `scripts/01`、`scripts/02`，8 张 EDA 图 |
| 模型实验 | 已完成 | ES-1～ES-4，五种模型 + 朴素基线 |
| 模型调优 | 已完成 | ratio 口径调参，3 种子稳定性验证 |
| 部署模型 | 已完成 | `tuned_rf_es3.joblib`，版本 `tuned_rf_es3_v2` |
| 后端 | 已完成 | Django 5 + DRF，SQLite；模型健康检查与可解释推理 |
| 前端 | 已完成 | Vue 3 + Element Plus + ECharts |
| 预测区间 | 已完成 | 训练集时序 5 折残差校准，测试覆盖率 78.32% |
| 工程测试 | 已完成 | 后端 11/11，前端 10/10，lint/build 通过 |

## 功能

- **数据管理**：区域、价格、面积、地铁、电梯筛选，排序、分页、详情。
- **可视化分析**：价格分布、面积关系、相关矩阵、特征重要性、空间散点、年度趋势。
- **模型对比**：ES-1～ES-4 分组切换，统一单价 R²、MAE、MAPE 与稳定性。
- **房价预测**：relative ratio 估值，输出单价、总价、80% 校准区间与 TreeSHAP 局部解释。\n- **相似成交**：按区域、面积、户型和配套检索历史可比案例。\n- **预测记录**：保存 request_id、推理耗时和响应快照，支持筛选与 CSV 导出。\n- **模型状态**：展示模型版本、文件指纹、特征数和近期推理统计。
- **工程能力**：图表导出、URL 筛选同步、独立错误重试、响应式布局。

## 技术栈

| 层次 | 技术 |
|---|---|
| 数据处理 | Python 3.12、pandas、NumPy、PyArrow |
| 机器学习 | scikit-learn、XGBoost、SHAP、joblib |
| 后端 | Django 5.2、Django REST Framework、SQLite |
| 前端 | Vue 3.5、Vite 6、Element Plus、ECharts、Pinia、Axios |
| 测试 | Django TestCase、Vitest、ESLint、Prettier |

> Python 依赖已锁定。本机实测新版 NumPy/pandas/scikit-learn 会触发 DLL 加载失败，请勿随意升级。

## 目录结构

```text
beijing-housing-price-prediction/
├── backend/                 # Django API、数据模型、推理封装
├── data/                    # 原始数据、清洗数据、指标 JSON、模型产物
├── docs/                    # 分类文档与静态素材
│   ├── 01-课题材料/
│   ├── 02-模型实验/
│   ├── 03-系统开发/
│   ├── 04-运行维护/
│   └── assets/
├── frontend/                # Vue 3 前端
├── scripts/                 # 清洗、EDA、训练、调参、稳定性脚本
├── .env.example
├── requirements.txt
└── README.md
```

## 快速开始

### 1. 环境

- Python **3.12**
- Node.js 24 / npm 11
- Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd frontend
npm install
cd ..
```

### 2. 数据与模型

原始数据放入：

```text
data/new.csv
```

完整重建流程：

```powershell
.\.venv\Scripts\python.exe scripts\01_clean_data.py
.\.venv\Scripts\python.exe scripts\02_eda.py
.\.venv\Scripts\python.exe scripts\03_train.py
.\.venv\Scripts\python.exe scripts\04_tune.py
.\.venv\Scripts\python.exe scripts\05_stability.py
```

部署模型输出为 `data/models/tuned_rf_es3.joblib`。模型与大体积数据不入库。

### 3. 启动后端

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py load_data
..\.venv\Scripts\python.exe manage.py runserver
```

后端：`http://127.0.0.1:8000/api/v1/`

### 4. 启动前端

```powershell
cd frontend
npm run dev
```

前端：`http://127.0.0.1:5173/`

## 模型口径

| 实验 | 划分 | 目标 | 用途 |
|---|---|---|---|
| ES-1 | 随机 | log1p(总价) | 同分布能力 |
| ES-2 | 时序 | log1p(总价) | 时间外推局限 |
| ES-3 | 时序 | ratio | 部署口径 |
| ES-4 | 随机 | ratio | 乐观上界对照 |

部署模型预测的是**相对行情估值**，不是未来房价走势。绝对价格依赖输入的当期区域中位单价。TreeSHAP 解释描述模型关联，不是因果结论。

当前区间采用训练集内部 `TimeSeriesSplit(5)` 折外残差校准，独立测试集覆盖率 **78.32%**，属于经验校准区间，不是严格置信区间。

## 项目文档

完整文档见 [docs/README.md](docs/README.md)。

- [项目计划书](docs/01-课题材料/项目计划书.md)
- [开题报告](docs/01-课题材料/开题报告.md)
- [模型实验结果](docs/02-模型实验/模型实验结果-v1.md)
- [模型调参结果](docs/02-模型实验/模型调参结果-v1.md)
- [EDA 图表说明](docs/02-模型实验/EDA图表说明.md)
- [后端接口说明](docs/03-系统开发/后端接口说明-v1.md)
- [前端说明](docs/03-系统开发/前端说明-v1.md)
- [运行指南](docs/04-运行维护/运行指南.md)

## 数据与免责声明

数据来源于 Kaggle 公开北京二手房成交数据，版权归原作者所有。本项目仅用于本科毕业设计与学术演示，预测结果不构成购房或投资建议。
