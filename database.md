## 数据库说明

数据库文件：`backend/data/stock_research_v2.db`（SQLite）

本文档描述系统中所有库表的结构、字段含义及数据来源。

---

### 1. stock_basic — 股票基本信息表

存储股票的基础信息和 10PS 估值结果。每只股票一条记录。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER (PK) | 自增主键 |
| stock_code | VARCHAR(12) | 股票代码，如 `600519.SH`，唯一索引 |
| stock_name | VARCHAR(20) | 股票名称，如 `贵州茅台` |
| exchange | VARCHAR(4) | 交易所，`SH`（上海）或 `SZ`（深圳） |
| board | VARCHAR(20) | 板块分类：创业板 / 主板 / 科创板 |
| industry | VARCHAR(200) | 所属行业 |
| extra_industry_count | INTEGER | 跨行业数量（公司涉及的业务领域数 - 1） |
| list_date | DATE | 上市日期 |
| pe_ttm | FLOAT | 滚动市盈率（PE TTM） |
| pb | FLOAT | 市净率（PB） |
| ps_ttm | FLOAT | 滚动市销率（PS TTM） |
| current_market_cap_yi | FLOAT | 当前市值（亿元） |
| latest_net_margin | FLOAT | 最近一期净利率（小数形式存储，如 0.22 表示 22%） |
| forecast_revenue_y1_yi | FLOAT | Y+1 年营收预测（亿元） |
| forecast_revenue_y2_yi | FLOAT | Y+2 年营收预测（亿元） |
| forecast_revenue_y3_yi | FLOAT | Y+3 年营收预测（亿元） |
| ten_ps_candidate | BOOLEAN | 是否满足 10PS 估值候选条件（净利率 ≥ 20%） |
| ten_ps_fair_market_cap_yi | FLOAT | 10PS 估值法下的合理市值（亿元） |
| ten_ps_current_to_y1 | FLOAT | 当前市值与 Y+1 合理市值的比值 |
| ten_ps_valuation_verdict | VARCHAR(20) | 10PS 估值结论：低估 / 合理/低估 / 泡沫 / 不适用 |
| ten_ps_valuation_detail | TEXT | 10PS 估值详细说明 |
| valuation_level | VARCHAR(10) | 综合估值等级 |
| data_source | VARCHAR(20) | 数据来源，默认 `baostock` |
| updated_at | DATE | 最近更新日期 |

**数据来源**：baostock `query_stock_basic` + 财务指标计算。

---

### 2. financial_quarterly — 季度财务数据表

存储每只股票的逐季度财务指标，是财务分析页面的核心数据表。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER (PK) | 自增主键 |
| stock_code | VARCHAR(12) | 股票代码（外键 → stock_basic.stock_code），索引 |
| quarter | VARCHAR(6) | 季度标签，如 `26Q1`、`25Q4` |
| report_date | DATE | 报告期日期，如 `2026-03-31` |
| revenue_yoy | FLOAT | 营收同比增速（%），已为单季度口径 |
| deducted_net_profit_yoy | FLOAT | 扣非净利润同比增速（%），已为单季度口径 |
| gross_margin | FLOAT | 毛利率（小数形式，如 0.35 表示 35%），单季度口径 |
| net_margin | FLOAT | 净利率（小数形式），单季度口径 |
| roe | FLOAT | 净资产收益率（小数形式） |
| roa | FLOAT | 总资产收益率（小数形式） |
| eps | FLOAT | 每股收益 |
| revenue | FLOAT | 营业收入（元），**存储为累计值**，展示时转为单季度 |
| net_profit | FLOAT | 净利润（元），**存储为累计值**，展示时转为单季度 |
| deducted_net_profit | FLOAT | 扣非净利润（元），来自 akshare，**存储为累计值**，展示时转为单季度 |
| deducted_net_profit_ttm | FLOAT | 扣非净利润 TTM（滚动四季合计，元） |
| total_assets | FLOAT | 总资产（元） |
| total_equity | FLOAT | 净资产 / 股东权益（元） |
| operating_cashflow | FLOAT | 经营活动现金流（元） |
| debt_ratio | FLOAT | 资产负债率（小数或百分比，展示时统一为百分比） |
| current_ratio | FLOAT | 流动比率 |

**索引**：`(stock_code, report_date)` 联合索引。

**数据来源**：
- 营收、净利润、毛利率、净利率、ROE、ROA、EPS、总资产、净资产、现金流、资产负债率、流动比率 → baostock（`query_profit_data`、`query_balance_data`、`query_growth_data`、`query_cash_flow_data`）
- 扣非净利润（deducted_net_profit）→ akshare（新浪财经），因 baostock 不提供此字段
- 营收同比优先使用 akshare 的总营业收入计算（比 baostock 的 MBRevenue 更准确）

**累计值转单季度**：revenue、net_profit、deducted_net_profit 三个字段在数据库中存储为累计值。在 `financial_calc.py` 的 `process_quarters_for_display` 中统一转换：Q1 保持不变，Q2–Q4 用当季累计值减去上一季度累计值。

---

### 3. invest_stock_pool — 自选股池

存储用户自选股及其估值、行情快照，用于"投资池"页面。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER (PK) | 自增主键 |
| stock_code | VARCHAR(12) | 股票代码，索引 |
| stock_name | VARCHAR(20) | 股票名称 |
| pool_type | VARCHAR(20) | 池类型：`quality`（优质）/ `tech_vc`（科技风投） |
| pool_type_label | VARCHAR(20) | 池类型中文标签 |
| memo | TEXT | 用户备注 |
| undervalued_price | FLOAT | 低估价格 |
| fair_price | FLOAT | 合理价格 |
| overvalued_price | FLOAT | 高估价格 |
| target_buy_price | FLOAT | 目标买入价 |
| target_sell_price | FLOAT | 目标卖出价 |
| target_price | FLOAT | 目标价 |
| revenue_forecast_y0 | FLOAT | 当年营收预测 |
| revenue_forecast_y1 | FLOAT | 下一年营收预测 |
| revenue_forecast_y2 | FLOAT | 下两年营收预测 |
| revenue_2023 | FLOAT | 2023 年营收 |
| revenue_2024 | FLOAT | 2024 年营收 |
| revenue_2025 | FLOAT | 2025 年营收 |
| q1_gross_margin | FLOAT | 最近 Q1 毛利率 |
| q1_net_margin | FLOAT | 最近 Q1 净利率 |
| q1_revenue_growth | FLOAT | 最近 Q1 营收增速 |
| min_ps_5y | FLOAT | 近 5 年最低市销率 |
| target_market_cap | FLOAT | 目标市值 |
| current_market_cap | FLOAT | 当前市值 |
| ytd_gain_pct | FLOAT | 年初至今涨幅（%） |
| display_order | INTEGER | 显示排序 |
| pool_update_error | TEXT | 最近更新错误信息 |
| profit_level | VARCHAR(20) | 盈利等级 |
| valuation_range | VARCHAR(10) | 估值区间：合理 / 低估 / 泡沫 |
| status | VARCHAR(10) | 状态，默认 `watching` |
| status_label | VARCHAR(10) | 状态中文标签 |
| alert_state | VARCHAR(20) | 告警状态，默认 `none` |
| last_alert_at | DATETIME | 最近告警时间 |
| latest_price | FLOAT | 最新价格 |
| ytd_gain | FLOAT | 年初至今收益 |
| market_cap | FLOAT | 市值 |
| latest_revenue_yoy | FLOAT | 最新营收同比 |
| latest_profit_yoy | FLOAT | 最新利润同比 |
| latest_level | VARCHAR(10) | 最新等级 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 最近更新时间 |

---

### 4. big_yang_signals — 大阳线信号表

记录大阳线策略产生的交易信号。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER (PK) | 自增主键 |
| stock_code | VARCHAR(12) | 股票代码，索引 |
| stock_name | VARCHAR(20) | 股票名称 |
| signal_type | VARCHAR(20) | 信号类型：`watching` / `triggered` / `expired` |
| trigger_price | FLOAT | 触发价格 |
| base_price | FLOAT | 基准价格 |
| trigger_at | DATETIME | 触发时间 |
| status | VARCHAR(20) | 状态，默认 `watching` |
| expire_days | INTEGER | 过期天数，默认 10 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 最近更新时间 |

---

### 5. big_yang_alerts — 大阳线告警表

记录大阳线信号触发的告警通知。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER (PK) | 自增主键 |
| signal_id | INTEGER (FK) | 关联信号 ID（外键 → big_yang_signals.id） |
| stock_code | VARCHAR(12) | 股票代码，索引 |
| stock_name | VARCHAR(20) | 股票名称 |
| title | VARCHAR(100) | 告警标题 |
| message | TEXT | 告警详情 |
| read | BOOLEAN | 是否已读，默认 `false` |
| trigger_at | DATETIME | 触发时间 |
| created_at | DATETIME | 创建时间 |

---

### 6. practical_select_records — 实战精选记录表

存储实战精选功能的分析记录。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER (PK) | 自增主键 |
| stock_code | VARCHAR(12) | 股票代码，索引 |
| stock_name | VARCHAR(20) | 股票名称 |
| trend_score | FLOAT | 趋势评分 |
| financial_score | FLOAT | 财务评分 |
| scarcity_stars | INTEGER | 稀缺性星级（1-5） |
| growth_stars | INTEGER | 成长性星级（1-5） |
| ten_ps_verdict | VARCHAR(20) | 10PS 估值结论 |
| summary_one_liner | TEXT | AI 一句话点评 |
| verdict | VARCHAR(10) | 综合判定：买入 / 观望 / 回避 |
| ai_model | VARCHAR(30) | 使用的 AI 模型，默认 `local` |
| analysis_json | JSON | 完整分析结果（JSON 格式） |
| status | VARCHAR(10) | 状态，默认 `SUCCESS` |
| submitted_at | DATETIME | 提交时间 |
| completed_at | DATETIME | 完成时间 |

---

### 表关系

```
stock_basic (1) ──── (N) financial_quarterly
     通过 stock_code 关联

big_yang_signals (1) ──── (N) big_yang_alerts
     通过 signal_id 关联

invest_stock_pool、practical_select_records 为独立表，
通过 stock_code 与 stock_basic 逻辑关联（无外键约束）。
```
