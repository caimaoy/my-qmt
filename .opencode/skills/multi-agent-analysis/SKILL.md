---
name: multi-agent-analysis
description: Use when performing comprehensive stock analysis using multiple agents. Dispatches market analyst, sentiment analyst, news analyst, fundamentals analyst, bull/bear researchers, research manager, and portfolio manager. Covers technical analysis, sentiment analysis, news analysis, fundamental analysis, investment debate, and final decision.
---

# Multi-Agent Stock Analysis

多 Agent 协作分析股票的完整流程，参考 TradingAgents 的 4 阶段决策框架。

## 流程概览

```
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Market Analyst │ │ Sentiment       │ │  News Analyst   │ │ Fundamentals    │
│  (技术分析)      │ │ Analyst (舆情)  │ │  (新闻分析)      │ │ Analyst (基本面) │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │                   │
         └───────────────────┴───────────────────┴───────────────────┘
                                             ▼
                                 ┌───────────────────────┐
                                 │  Context Aggregation  │
                                 │  (汇总分析师报告)       │
                                 └───────────┬───────────┘
                                             ▼
                        ┌────────────────────┴────────────────────┐
                        ▼                                         ▼
               ┌─────────────┐                           ┌─────────────┐
               │ Bull        │                           │ Bear        │
               │ Researcher  │                           │ Researcher  │
               │ (看多论证)   │                           │ (看空论证)   │
               └──────┬──────┘                           └──────┬──────┘
                      │                                         │
                      └─────────────────┬───────────────────────┘
                                        ▼
                             ┌────────────────────┐
                             │  Research Manager  │
                             │  (辩论裁判)         │
                             └─────────┬──────────┘
                                       ▼
                             ┌────────────────────┐
                             │  Portfolio Manager │
                             │  (最终投资决策)     │
                             └────────────────────┘
```

## Step 1: Market Analyst (技术分析)

**职责:** 分析 OHLCV 数据和技术指标，判断趋势、动量、波动率。

**调用方式:**
```
@market-analyst 分析 {SYMBOL} 的技术面
```

**或使用 Task 工具:**
```python
task(
    description="Technical analysis for {SYMBOL}",
    prompt="""
You are a market analyst. Analyze {SYMBOL} technical indicators.

Steps:
1. Fetch OHLCV data via yfinance (last 90-120 days)
2. Compute indicators: SMA, EMA, MACD, RSI, Bollinger Bands, ATR
3. Provide structured analysis covering:
   - Trend analysis (short-term vs long-term)
   - Momentum analysis (MACD, RSI)
   - Volatility analysis (Bollinger Bands, ATR)
   - Support and resistance levels
   - Volume analysis
   - Technical outlook (bullish/bearish/neutral)

Format as markdown with clear sections and data tables.
""",
    subagent_type="general"
)
```

**输出格式:**
```markdown
# {SYMBOL} Technical Analysis Report
**Date: {DATE} | Close: ${PRICE} | Change: {CHANGE}**

## 1. Trend Analysis
- Short-term: [Uptrend/Downtrend/Sideways]
- Long-term: [Uptrend/Downtrend/Sideways]
- Price vs SMA 20/50: [Above/Below]

## 2. Momentum Analysis
- RSI (14): {VALUE} — [Overbought/Neutral/Oversold]
- MACD: {VALUE} | Signal: {VALUE} | Histogram: {VALUE}

## 3. Volatility Analysis
- Bollinger Bands: Upper ${UPPER} | Middle ${MIDDLE} | Lower ${LOWER}
- ATR (14): ${ATR} ({PCT}% of price)

## 4. Support & Resistance
- Support: ${LEVEL1}, ${LEVEL2}
- Resistance: ${LEVEL1}, ${LEVEL2}

## 5. Volume Analysis
- Latest Volume: {VOL} (vs 20-day avg: {AVG})

## 6. Technical Outlook
**Verdict: [Bullish/Bearish/Neutral] (Short-term) → [Bullish/Bearish/Neutral] (Medium-term)**
```

---

## Step 2: News Analyst (新闻分析)

**职责:** 分析公司新闻和宏观新闻，评估新闻情绪。

**调用方式:**
```
@news-analyst 分析 {SYMBOL} 的新闻
```

**或使用 Task 工具:**
```python
task(
    description="News analysis for {SYMBOL}",
    prompt="""
你是新闻分析师。分析 {SYMBOL} 的近期新闻。

步骤:
1. 根据市场选择新闻源:
   - A股 (600xxx/000xxx/300xxx): 使用东方财富公告、东方财富股吧、新浪财经
   - 美股/港股: 使用 Google Finance + yfinance
2. 获取新闻数据:
   ```python
   # A股专用
   from tradingagents.dataflows.china_news import get_news_eastmoney, get_guba_hot_posts, get_news_sina
   announcements = get_news_eastmoney("{SYMBOL}", limit=5)
   forum_posts = get_guba_hot_posts("{SYMBOL}", limit=5)
   sina_news = get_news_sina("{SYMBOL}", limit=5)

   # 美股/港股
   from tradingagents.dataflows.interface import route_to_vendor
   yf_news = route_to_vendor("get_news", "{SYMBOL}", 20)
   ```
3. 用 webfetch 获取 Google Finance 页面补充宏观新闻
4. 分析并输出结构化报告

输出格式 (中文):
## 1. 最具影响力的新闻 (TOP 5)
1. **{标题}** ({日期})
   {摘要和影响分析}

## 2. 宏观经济趋势
| 因素 | 状态 | 影响 |
|------|------|------|

## 3. 行业动态
- {发展1}
- {发展2}

## 4. 地缘政治风险
| 风险 | 严重程度 | 详情 |
|------|----------|------|

## 5. 新闻情绪
**整体情绪: [正面/负面/中性]**
""",
    subagent_type="general"
)
```

**输出格式:**
```markdown
# {SYMBOL} 新闻分析报告
**日期: {DATE}**

## 1. 最具影响力的新闻 (TOP 5)
1. **{标题}** ({日期})
   {摘要和影响分析}

## 2. 宏观经济趋势
| 因素 | 状态 | 影响 |
|------|------|------|
| 利率 | {STATUS} | {IMPACT} |
| 通胀 | {STATUS} | {IMPACT} |

## 3. 行业动态
- {发展1}
- {发展2}

## 4. 地缘政治风险
| 风险 | 严重程度 | 详情 |
|------|----------|------|

## 5. 新闻情绪
**整体情绪: [正面/负面/中性]**
```

---

## Step 2.5: Sentiment Analyst (舆情分析)

**职责:** 分析社交媒体和散户情绪，评估市场情绪。

**调用方式:**
```
@sentiment-analyst 分析 {SYMBOL} 的舆情
```

**或使用 Task 工具:**
```python
task(
    description="Sentiment analysis for {SYMBOL}",
    prompt="""
你是舆情分析师。分析 {SYMBOL} 的社交媒体和散户情绪。

步骤:
1. 根据市场选择数据源:
   - 美股: StockTwits + Reddit
   - A股: 东方财富股吧 + 雪球
2. 获取舆情数据:
   ```python
   # 美股
   from tradingagents.dataflows.social_media import fetch_stocktwits_messages, fetch_reddit_posts
   stw = fetch_stocktwits_messages("{SYMBOL}", limit=20)
   reddit = fetch_reddit_posts("{SYMBOL}", limit=10)

   # A股
   from tradingagents.dataflows.china_news import get_guba_hot_posts, get_news_xueqiu
   guba = get_guba_hot_posts("{SYMBOL}", limit=20)
   xq = get_news_xueqiu("{SYMBOL}", limit=10)
   ```
3. 分析情绪比例、热门话题、异常信号

输出格式 (中文):
## 1. 整体情绪
**情绪: [偏多/偏空/中性]**

## 2. 热门话题
- {话题1}: {讨论热度}

## 3. 关键讨论
- {帖子核心观点}

## 4. 投资启示
{散户情绪对投资决策的参考价值}
""",
    subagent_type="general"
)
```

---

## Step 2.6: Fundamentals Analyst (基本面分析)

**职责:** 分析财务报表和公司基本面，评估财务健康状况。

**调用方式:**
```
@fundamentals-analyst 分析 {SYMBOL} 的基本面
```

**或使用 Task 工具:**
```python
task(
    description="Fundamentals analysis for {SYMBOL}",
    prompt="""
你是基本面分析师。分析 {SYMBOL} 的财务报表和公司基本面。

步骤:
1. 获取财务数据:
   ```python
   from tradingagents.dataflows.interface import route_to_vendor
   fundamentals = route_to_vendor("get_fundamentals", "{SYMBOL}")
   balance_sheet = route_to_vendor("get_balance_sheet", "{SYMBOL}", 4)
   income_stmt = route_to_vendor("get_income_statement", "{SYMBOL}", 4)
   cashflow = route_to_vendor("get_cashflow", "{SYMBOL}", 4)
   ```
2. 分析盈利能力、财务健康、估值、增长潜力

输出格式 (中文):
## 1. 公司概况
| 指标 | 数值 |

## 2. 盈利能力
| 指标 | 最新值 | 趋势 | 评价 |

## 3. 财务健康
| 指标 | 数值 | 评价 |

## 4. 估值分析
| 指标 | 当前 | 历史均值 | 同行 | 判断 |

## 5. 基本面评级
**评级: [优秀/良好/一般/较差]**
""",
    subagent_type="general"
)
```

---

## Step 3: Bull/Bear Debate (多空辩论)

**职责:** 牛市研究员和熊市研究员分别论证，形成投资辩论。

**调用方式:**
```
@bull-researcher 和 @bear-researcher 辩论 {SYMBOL} 是否值得投资
```

**或使用 Task 工具 (并行调用):**
```python
# 牛市研究员
task(
    description="Bull case for {SYMBOL}",
    prompt="""
You are a BULLISH stock researcher. Build the strongest case FOR investing in {SYMBOL}.

Context: {TECHNICAL_REPORT + NEWS_REPORT}

Focus on:
1. Positive catalysts and growth opportunities
2. Strong fundamentals and technical signals
3. Counter bearish arguments with data
4. Present compelling investment thesis

Format as structured markdown.
""",
    subagent_type="general"
)

# 熊市研究员 (并行)
task(
    description="Bear case for {SYMBOL}",
    prompt="""
You are a BEARISH stock researcher. Build the strongest case AGAINST investing in {SYMBOL}.

Context: {TECHNICAL_REPORT + NEWS_REPORT}

Focus on:
1. Risks, challenges, and potential downside
2. Weaknesses in fundamentals and technical signals
3. Counter bullish arguments with data
4. Present compelling case for caution or selling

Format as structured markdown.
""",
    subagent_type="general"
)
```

**输出格式:**
```markdown
# {SYMBOL} Bull/Bear Case

## Bull Case
1. **{Argument 1}**
   {Supporting evidence}
2. **{Argument 2}**
   {Supporting evidence}

## Bear Case
1. **{Argument 1}**
   {Supporting evidence}
2. **{Argument 2}**
   {Supporting evidence}
```

---

## Step 3.5: Research Manager (辩论裁判)

**职责:** 评判牛熊辩论，综合所有分析师报告，输出结构化投资建议。

**调用方式:**
```
@research-manager 评判辩论并给出投资建议
```

**或使用 Task 工具:**
```python
task(
    description="Research manager judgment for {SYMBOL}",
    prompt="""
你是研究经理。评判牛熊辩论，综合所有分析师报告，输出结构化投资建议。

上下文:
- 技术分析: {TECHNICAL_REPORT}
- 新闻分析: {NEWS_REPORT}
- 舆情分析: {SENTIMENT_REPORT}
- 基本面分析: {FUNDAMENTALS_REPORT}
- 牛方论据: {BULL_CASE}
- 熊方论据: {BEAR_CASE}

评判标准:
1. 数据支撑: 论点是否有数据支持？
2. 逻辑一致性: 论证逻辑是否自洽？
3. 反驳有效性: 对方反驳是否有力？
4. 前瞻性: 是否考虑了未来变化？

权重分配:
- 基本面: 30%
- 技术面: 20%
- 新闻/舆情: 20%
- 辩论质量: 30%

输出格式 (中文):
## 1. 辩论评判
### 牛方论点评分
| 论点 | 数据支撑 | 逻辑 | 前瞻性 | 总分 |

### 熊方论点评分
| 论点 | 数据支撑 | 逻辑 | 前瞻性 | 总分 |

### 辩论胜者
**胜者: [牛方/熊方]**

## 2. 综合评估
| 维度 | 权重 | 评分 | 加权分 |

## 3. 投资建议
**推荐: [强烈买入/买入/持有/减持/卖出]**
""",
    subagent_type="general"
)
```

---

## Step 4: Portfolio Manager (最终决策)

**职责:** 综合所有分析师报告和辩论结果，做出最终投资决策。

**调用方式:**
```
@portfolio-manager 做出最终投资决策
```

**或使用 Task 工具:**
```python
task(
    description="Portfolio decision for {SYMBOL}",
    prompt="""
You are the Portfolio Manager. Make the FINAL investment decision for {SYMBOL}.

Context:
- Technical Analysis: {TECHNICAL_REPORT}
- News Analysis: {NEWS_REPORT}
- Bull Case: {BULL_CASE}
- Bear Case: {BEAR_CASE}

Make your decision using this exact format:

## Decision
**Rating:** [Buy/Overweight/Hold/Underweight/Sell]

## Executive Summary
[2-3 sentence summary]

## Investment Thesis
[Detailed reasoning, 3-5 paragraphs]

## Price Target
[Your price target with reasoning]

## Time Horizon
[Recommended holding period]

## Key Risks
[Top 3 risks to monitor]
""",
    subagent_type="general"
)
```

**输出格式:**
```markdown
## Decision
**Rating:** [Buy/Overweight/Hold/Underweight/Sell]

## Executive Summary
{Summary}

## Investment Thesis
{Detailed reasoning}

## Price Target
${TARGET} ({UPSIDE}% upside)

## Time Horizon
{HORIZON}

## Key Risks
1. {Risk 1}
2. {Risk 2}
3. {Risk 3}
```

---

## 完整调用示例

```python
from tradingagents.main import run_analysis

# 方式 1: Python 代码调用
result = run_analysis(
    symbol="AAPL",
    trade_date="2026-06-14",
    max_debate_rounds=1,
)

# 方式 2: 通过 opencode subagent 逐步调用
# Step 1: @market-analyst 分析 AAPL 的技术面
# Step 2: @news-analyst 分析 AAPL 的新闻
# Step 3: @bull-researcher 和 @bear-researcher 辩论
# Step 4: @portfolio-manager 做出最终决策
```

## 支持的市场

| 市场 | Ticker 格式 | 示例 |
|------|-------------|------|
| 美股 | {SYMBOL} | AAPL, NVDA |
| 港股 | {SYMBOL}.HK | 0700.HK, 9988.HK |
| A股 (上海) | {SYMBOL}.SS | 600519.SS |
| A股 (深圳) | {SYMBOL}.SZ | 000001.SZ |

---

## 新闻数据源

### 国际源 (默认)

| 源 | API | 数据类型 | 需要 Key |
|------|------|----------|----------|
| **Google Finance** | 网页抓取 | 公司新闻、宏观新闻 | 否 |
| **yfinance** | Python 库 | 公司新闻、全球新闻 | 否 |

### 国内源 (A股/港股)

| 源 | 状态 | 数据类型 | 需要 Key |
|------|------|----------|----------|
| **东方财富公告** | ✅ 已验证 | 公司公告、股东大会、董事会决议 | 否 |
| **东方财富股吧** | ✅ 已修复 | 投资者讨论、热帖 | 否 |
| **新浪财经** | ✅ 已修复 | 个股新闻 | 否 |
| **雪球** | ⚠️ 需 Token | 投资者讨论 | 否 (有备用方案) |

> **注意:** yfinance 可能被限流 (429 错误)，A 股优先使用国内源。

### 调用方式

```python
# 东方财富 - 公司公告 (最可靠)
from tradingagents.dataflows.china_news import get_news_eastmoney
news = get_news_eastmoney("600519", limit=10)

# 东方财富 - 股吧热帖
from tradingagents.dataflows.china_news import get_guba_hot_posts
posts = get_guba_hot_posts("600519", limit=10)

# 东方财富 - 全球财经快讯
from tradingagents.dataflows.china_news import get_global_news_eastmoney
global_news = get_global_news_eastmoney(limit=20)

# 新浪财经 - 个股新闻
from tradingagents.dataflows.china_news import get_news_sina
news = get_news_sina("600519", limit=10)

# 雪球 - 投资者讨论 (需要有效 Token，无 Token 时使用备用方案)
from tradingagents.dataflows.china_news import get_news_xueqiu
discussions = get_news_xueqiu("SH600519", limit=10)

# 聚合所有国内源 (推荐)
from tradingagents.dataflows.china_news import get_china_news_aggregated
all_news = get_china_news_aggregated("600519", limit_per_source=10)
```

### Vendor 路由配置

```python
# 切换到东方财富作为默认新闻源
from tradingagents.dataflows.interface import set_vendor_config
set_vendor_config({"news_data": "eastmoney"})
```

或通过环境变量:
```bash
export TRADINGAGENTS_VENDOR_GET_NEWS=eastmoney
```
