---
name: a-share-analysis
description: Use when analyzing A-share stocks. Supports single stock technical analysis, batch scanning by indicators (RSI, MACD, Bollinger), and multi-board filtering (HS300, ChiNext, STAR). Uses AKShare as primary data source with Tencent Finance fallback.
---

# A股技术分析

A 股专用技术分析工具，支持单只分析和批量筛选。

## 数据源

### AKShare (主用)

| 函数 | 用途 | 数据源 |
|------|------|--------|
| `stock_zh_a_hist()` | 历史K线 | 东方财富 |
| `index_stock_cons_weight_csindex()` | 指数成分股 | 中证指数 |

### 腾讯财经 (备用)

| API | 用途 | 特点 |
|------|------|------|
| `qt.gtimg.cn` | 实时行情 | 快速、无需认证 |
| `web.ifzq.gtimg.cn` | 历史K线 | 前复权 |

### 缓存

- 目录: `~/.tradingagents/cache/`
- 有效期: 24 小时
- 格式: CSV 文件

---

## 功能 1: 获取指数成分股

```python
from tradingagents.dataflows.a_share_data import get_hs300_stocks, get_sz50_stocks, get_zz500_stocks

# 获取沪深300成分股 (300只)
hs300 = get_hs300_stocks()

# 获取上证50成分股 (50只)
sz50 = get_sz50_stocks()

# 获取中证500成分股 (500只)
zz500 = get_zz500_stocks()

# 返回格式:
# [{"code": "600519", "name": "贵州茅台", "weight": 5.23}, ...]
```

---

## 功能 2: 单只股票技术分析

```python
from tradingagents.dataflows.a_share_data import get_stock_data, get_realtime_quote
from tradingagents.indicators.technical import compute_all_indicators

# 获取历史数据 (自动选择数据源，带缓存)
df = get_stock_data("600519", days=120)

# 计算 8 个技术指标
df_indicators = compute_all_indicators(df)
latest = df_indicators.iloc[-1]

# 获取实时行情
quote = get_realtime_quote("600519")
print(f"现价: {quote['price']}, 涨跌幅: {quote['change_pct']}%")
```

---

## 功能 3: 批量扫描筛选

### 单条件筛选

```python
from tradingagents.dataflows.a_share_data import get_hs300_stocks, scan_stocks_by_indicator, format_scan_results_markdown

# 获取沪深300成分股
stocks = get_hs300_stocks()

# 扫描 RSI < 30 的股票
results = scan_stocks_by_indicator(stocks, indicator="rsi_below", threshold=30, limit=20)

# 输出 Markdown 表格
print(format_scan_results_markdown(results, "RSI < 30 的股票"))
```

### 多条件筛选

```python
from tradingagents.dataflows.a_share_data import get_hs300_stocks, scan_multiple_conditions, format_scan_results_markdown

stocks = get_hs300_stocks()

# 同时满足 RSI < 40 且 MACD 金叉
conditions = [
    {"indicator": "rsi_below", "threshold": 40},
    {"indicator": "macd_golden"},
]
results = scan_multiple_conditions(stocks, conditions=conditions, limit=20)
print(format_scan_results_markdown(results, "RSI < 40 且 MACD 金叉"))
```

### 筛选条件

| 条件 | 说明 | 阈值 |
|------|------|------|
| `rsi_below` | RSI < 阈值 (超卖) | 30 |
| `rsi_above` | RSI > 阈值 (超买) | 70 |
| `macd_golden` | MACD 金叉 | - |
| `macd_dead` | MACD 死叉 | - |
| `price_below_bb_lower` | 价格低于布林带下轨 | - |

---

## 输出格式

### Markdown 表格

```markdown
# 扫描结果

**结果数量:** 15

| 代码 | 名称 | 现价 | 涨跌幅 | 指标详情 |
|------|------|------|--------|----------|
| 000001 | 平安银行 | 10.50 | -1.23% | RSI=28.45 |
```

### HTML 表格

```python
from tradingagents.dataflows.a_share_data import format_scan_results_html
html = format_scan_results_html(results, "扫描结果")
```

---

## 调用方式 (opencode subagent)

```
@a-share-analyst 分析 600519 的技术面
@a-share-analyst 扫描沪深300中RSI低于30的股票
@a-share-analyst 扫描沪深300中RSI低于40且MACD金叉的股票
@a-share-analyst 扫描创业板中价格跌破布林带下轨的股票
```

---

## 技术指标说明

| 指标 | 全称 | 用途 | 超买/超卖 |
|------|------|------|-----------|
| SMA | Simple Moving Average | 趋势判断 | - |
| EMA | Exponential Moving Average | 趋势判断 (近期权重更高) | - |
| MACD | Moving Average Convergence Divergence | 趋势+动量 | 金叉/死叉 |
| RSI | Relative Strength Index | 超买超卖 | >70 超买, <30 超卖 |
| BB | Bollinger Bands | 波动率+支撑阻力 | 突破上/下轨 |
| ATR | Average True Range | 波动率 | - |
| VWAP | Volume Weighted Average Price | 成交量加权均价 | - |
| OBV | On Balance Volume | 量价关系 | - |
