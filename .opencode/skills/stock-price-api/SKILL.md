---
name: stock-price-api
description: Use when fetching stock price data (OHLCV). Three methods available: yfinance (default, no auth), Alpha Vantage (requires API key), and Google Finance (web scraping fallback). Covers usage, parameters, rate limiting, and vendor routing.
---

# Stock Price API

获取股票价格数据的三种方式，基于 TradingAgents 的 vendor 抽象层。

## Method 1: yfinance (默认)

无需 API Key，直接使用。

```python
import yfinance as yf
from datetime import datetime

def get_stock_price(symbol: str, start_date: str, end_date: str) -> str:
    """
    symbol: 股票代码，如 "AAPL", "NVDA", "9988.T"
    start_date: 开始日期，格式 "yyyy-mm-dd"
    end_date: 结束日期，格式 "yyyy-mm-dd"
    返回: CSV 格式的 OHLCV 数据
    """
    ticker = yf.Ticker(symbol.upper())
    data = ticker.history(start=start_date, end=end_date)

    if data.empty:
        return f"No data for {symbol}"

    # 去除时区信息
    if data.index.tz is not None:
        data.index = data.index.tz_localize(None)

    # 保留2位小数
    for col in ["Open", "High", "Low", "Close", "Adj Close"]:
        if col in data.columns:
            data[col] = data[col].round(2)

    return data.to_csv()
```

**带重试的版本**（处理 429 限流）：

```python
import time
import yfinance as yf

def yf_retry(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if "429" in str(e) and attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            raise
```

## Method 2: Alpha Vantage

需要设置环境变量 `ALPHA_VANTAGE_API_KEY`。

```python
import os
import requests
from datetime import datetime

ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"

def get_stock_price_alpha_vantage(symbol: str, start_date: str, end_date: str) -> str:
    """
    symbol: 股票代码，如 "IBM", "AAPL"
    start_date: 开始日期，格式 "yyyy-mm-dd"
    end_date: 结束日期，格式 "yyyy-mm-dd"
    返回: CSV 格式的每日调整后数据
    """
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    days_diff = (datetime.now() - start_dt).days
    outputsize = "compact" if days_diff < 100 else "full"

    params = {
        "function": "TIME_SERIES_DAILY_ADJUSTED",
        "symbol": symbol,
        "outputsize": outputsize,
        "datatype": "csv",
        "apikey": os.environ["ALPHA_VANTAGE_API_KEY"],
        "source": "trading_agents",
    }

    response = requests.get(ALPHA_VANTAGE_BASE_URL, params=params)
    response.raise_for_status()

    # 按日期范围过滤
    lines = response.text.strip().split("\n")
    header = lines[0]
    filtered = [header] + [
        line for line in lines[1:]
        if start_date <= line.split(",")[0] <= end_date
    ]
    return "\n".join(filtered)
```

## Method 3: Google Finance (备用)

无 API，通过网页抓取。适合快速查询单只股票当前价格。

**编码格式注意：**
- 美股: `AAPL:NASDAQ`, `MSFT:NASDAQ`
- 港股: `0700:HKG`, `9988:HKG`
- A股上海: `600519:SHA` (不是 `.SS`)
- A股深圳: `000001:SHE` (不是 `.SZ`)

```python
import re
import requests

def get_stock_price_google(symbol: str) -> dict:
    """
    symbol: 股票代码，如 "0700:HKG", "AAPL:NASDAQ", "600519:SHA"
    返回: dict 包含当前价格、涨跌幅等
    """
    url = f"https://www.google.com/finance/quote/{symbol}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    html = response.text
    # 提取价格（网页结构可能变化）
    price_match = re.search(r'data-last-price="([\d.]+)"', html)
    change_match = re.search(r'data-last-normal-market-change-percent="([-\d.]+)"', html)

    return {
        "price": float(price_match.group(1)) if price_match else None,
        "change_pct": float(change_match.group(1)) if change_match else None,
    }
```

**注意：**
- 无官方 API，依赖网页结构，可能随时失效
- 历史数据有限
- 有 15-20 分钟延迟
- 适合快速查询，不适合批量或历史数据获取

## 对比

| 特性 | yfinance | Alpha Vantage | Google Finance |
|------|----------|---------------|----------------|
| 认证 | 无需 | 需要 `ALPHA_VANTAGE_API_KEY` | 无需 |
| API | 有 (Python 库) | 有 (HTTP REST) | 无 (网页抓取) |
| 实时性 | 15分钟延迟 | 实时 | 15-20分钟延迟 |
| 历史数据 | 完整 | 完整 | 有限 |
| 稳定性 | 中（可能被限流） | 高 | 低（网页结构变化） |
| 限流处理 | 指数退避重试 (3次) | 触发 fallback 到其他 vendor | 无 |
| 默认 | 是 | 否 | 备用 |

## Vendor 路由

TradingAgents 使用 `interface.py` 中的 `route_to_vendor()` 进行路由：

```python
# 默认配置 (default_config.py)
data_vendors = {
    "core_stock_apis": "yfinance",       # 或 "alpha_vantage"
    "technical_indicators": "yfinance",
    "fundamental_data": "yfinance",
}
```

切换 vendor：修改 `data_vendors` 配置中的对应类别。

## 使用建议

- **日常开发/测试**：使用 yfinance，无需配置
- **生产环境/需要稳定性**：配置 Alpha Vantage 作为 fallback
- **快速查询当前价格**：使用 Google Finance（无需安装依赖）
- **A股/港股**：yfinance 支持，代码后缀如 `.SS`(上海), `.SZ`(深圳), `.HK`(香港)
- **港股查询**：Google Finance 格式为 `0700:HKG`，yfinance 格式为 `0700.HK`
