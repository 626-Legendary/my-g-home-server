from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
import yfinance as yf

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI backend!"}

@app.get("/api/stocks")
def get_stocks():
    # 简单 mock，前端如果只用详细接口也可以不管这个
    return [
        {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "price": 195.42,
            "change": -1.23,
            "change_percent": -0.63,
        },
        {
            "symbol": "TSLA",
            "name": "Tesla Inc.",
            "price": 240.10,
            "change": 5.12,
            "change_percent": 2.18,
        },
    ]


@app.get("/api/stocks/{symbol}")
def get_stock(symbol: str):
    try:
        symbol = symbol.upper()
        ticker = yf.Ticker(symbol)

        # 1) 用 get_info 拿完整信息（核心改动：完全不用 get_fast_info）
        raw_info = ticker.get_info() or {}

        if not raw_info:
            raise HTTPException(
                status_code=404,
                detail=f"Symbol '{symbol}' not found or has no info",
            )

        # 2) 名称优先级：displayName > shortName > longName > symbol
        display_name = (
            raw_info.get("displayName")
            or raw_info.get("shortName")
            or raw_info.get("longName")
            or symbol
        )

        # 3) 价格相关字段（完全基于 get_info 返回）
        #    尽量靠近 Yahoo Finance 的逻辑
        price = (
            raw_info.get("regularMarketPrice")
            or raw_info.get("currentPrice")
        )

        regular_prev_close = raw_info.get("regularMarketPreviousClose")
        prev_close = raw_info.get("previousClose") or regular_prev_close

        day_high = raw_info.get("dayHigh")
        day_low = raw_info.get("dayLow")
        year_high = raw_info.get("fiftyTwoWeekHigh")
        year_low = raw_info.get("fiftyTwoWeekLow")

        currency = raw_info.get("currency")
        exchange = raw_info.get("exchange")

        # 4) 涨跌额/涨跌幅 —— 优先用 API 自带字段，没有就自己算
        change = raw_info.get("regularMarketChange")
        change_percent = raw_info.get("regularMarketChangePercent")

        if change is None and price is not None and regular_prev_close is not None:
            change = price - regular_prev_close

        if change_percent is None and change is not None and regular_prev_close:
            change_percent = (change / regular_prev_close) * 100

        # 5) 新闻：可选字段，拿不到就空列表
        try:
            raw_news = ticker.get_news() or []
        except Exception:
            raw_news = []

        # 6) 整理一个前端友好的 info 结构（用 get_info 的字段拼出来）
        info = {
            "currency": currency,
            "exchange": exchange,
            "lastPrice": price,
            "previousClose": prev_close,
            "regularMarketPreviousClose": regular_prev_close,
            "dayHigh": day_high,
            "dayLow": day_low,
            "yearHigh": year_high,
            "yearLow": year_low,
            "regularMarketChange": change,
            "regularMarketChangePercent": change_percent,
        }

        return {
            "symbol": symbol,
            "displayName": display_name,
            "info": jsonable_encoder(info),
            "news": jsonable_encoder(raw_news),
        }

    except HTTPException:
        raise
    except Exception as e:
        print("ERROR in /api/stocks/{symbol}:", e)
        raise HTTPException(status_code=500, detail=str(e))
