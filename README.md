# beijing-housing-price-prediction

**基于机器学习的房价预测与可视化分析系统设计与实现**

---

## 项目简介

本项目以北京二手房市场为研究对象，基于 Kaggle 公开的北京链家二手房成交数据集（2011–2017 年，约 31.8 万条记录），构建一个集**数据可视化分析**与**房价预测**于一体的 Web 系统。

系统使用多种机器学习模型（线性回归、决策树、随机森林、XGBoost、MLP 神经网络）进行房价建模与对比，并通过可视化界面展示房价分布、区域差异、影响因素与预测结果。

- 专业：数据科学与大数据技术
- 项目性质：应用研究
- 当前阶段：开题报告已提交；数据清洗、EDA、模型实验与调参已完成，进入系统开发阶段

---

## 功能规划

| 模块 | 说明 | 状态 |
|---|---|---|
| 数据管理 | 数据导入、预览、缺失值与异常值统计、清洗结果对比 | 数据层已完成 |
| 可视化分析 | 房价分布、各区均价、面积与价格关系、相关性热力图、特征重要性 | 图表已产出，待接入前端 |
| 模型对比 | 多模型 RMSE / MAE / R² 对比、预测值 vs 实际值、残差分析 | 实验已完成（metrics_v1.json） |
| 房价预测 | 输入房屋特征，实时输出预测总价与折算单价 | 已接口化（M3.5） |
| 报表导出 | 分析与预测结果导出（可选） | 规划中 |

---

## 技术栈

| 层次 | 技术 |
|---|---|
| 后端 | Django 5 + Django REST Framework |
| 后台管理 | Django Admin |
| 前端 | Vue 3 + Element Plus |
| 可视化 | ECharts |
| 数据库 | MySQL 8（开发期可用 SQLite） |
| 数据处理 | pandas + numpy |
| 机器学习 | scikit-learn + XGBoost |
| 地理处理 | GeoPandas / Shapely |

---

## 数据来源

- 数据集：Kaggle 北京链家二手房成交数据（2011–2017 年，约 31.8 万条，26 个字段）
- 获取方式：请从 Kaggle 搜索 `Beijing housing price` / `Lianjia` 相关数据集下载
- 放置位置：下载后重命名为 `new.csv`，放入 `data/` 目录
- 编码格式：**GBK**，使用 pandas 读取时需指定 `encoding='gbk'`

> 数据集文件体积较大（约 58.7 MB），**不纳入版本控制**，请勿提交至仓库。

### 主要字段

| 字段 | 含义 |
|---|---|
| tradeTime | 交易时间 |
| totalPrice | 总价（万元） |
| price | 单价（元/平方米） |
| square | 面积（平方米） |
| livingRoom / drawingRoom | 卧室数 / 客厅数 |
| kitchen / bathRoom | 厨房数 / 卫生间数 |
| floor | 楼层信息（如「中 6」表示中层、共 6 层） |
| constructionTime | 建造年份 |
| renovationCondition | 装修情况编码 |
| buildingType / buildingStructure | 建筑类型 / 建筑结构编码 |
| elevator / subway / fiveYearsProperty | 电梯 / 近地铁 / 满五年 |
| district | 区域编码（1–13） |
| Lng / Lat | 经纬度 |
| communityAverage | 小区均价 |

---

## 目录结构

```
beijing-housing-price-prediction/
├── backend/               # Django 后端（API + Admin + SQLite）
├── frontend/              # Vue 3 + Element Plus + ECharts 前端
├── backend/ml/            # 特征工程、评估指标（训练/推理共用）
├── data/                  # 数据集与实验产物（大数据文件不入库）
├── docs/                  # 项目文档 + figures/ 图表
├── scripts/               # 01_清洗 / 02_EDA / 03_训练 / 04_调参
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 快速开始

> 数据工程、模型实验与 Django 后端（M3.5/M4a）已完成；前端 M4b 待开发。

```bash
# 1. 创建并激活虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 2. 安装依赖（依赖清单待生成）
pip install -r requirements.txt

# 3. 启动后端
python manage.py runserver

# 4. 启动前端
cd frontend
npm install
npm run dev
```

---

## 项目文档

- [项目计划书](docs/项目计划书.md)
- [毕设时间节点](docs/毕设时间节点.pdf)

---

## 开发规范

| 项 | 规则 |
|---|---|
| 分支策略 | 单 `main` 分支 |
| 提交规范 | Conventional Commits（`feat:` / `fix:` / `docs:` / `chore:`） |
| 不提交内容 | 数据集（`data/*.csv`）、模型文件（`*.pkl`）、`node_modules/`、虚拟环境、`.env` |
| 模型训练 | 训练脚本离线运行，模型产物不入库，可复现 |

---

## 数据与免责声明

本项目为本科毕业设计，仅用于学术研究与技术实践。数据集来源为 Kaggle 公开数据，版权归原作者所有。系统预测结果基于历史成交数据，**仅用于研究演示，不构成任何购房或投资建议**。
