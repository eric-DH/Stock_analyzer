import yfinance as yf


TICKER_SYMBOL = "AAPL"


def main() -> None:
    stock = yf.Ticker(TICKER_SYMBOL)
    info = stock.info

    company_name = info.get("longName") or info.get("shortName")
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    previous_close = info.get("previousClose") or info.get(
        "regularMarketPreviousClose"
    )

    if not company_name:
        raise ValueError(f"{TICKER_SYMBOL}의 회사명을 가져오지 못했습니다.")
    if current_price is None:
        raise ValueError(f"{TICKER_SYMBOL}의 현재가를 가져오지 못했습니다.")
    if previous_close is None or previous_close <= 0:
        raise ValueError(f"{TICKER_SYMBOL}의 전일 종가를 가져오지 못했습니다.")

    change_percent = (current_price / previous_close - 1) * 100

    history = stock.history(period="1mo")
    if history.empty:
        raise RuntimeError(f"{TICKER_SYMBOL}의 최근 1개월 데이터를 가져오지 못했습니다.")

    high_date = history["High"].idxmax()
    low_date = history["Low"].idxmin()
    high_row = history.loc[high_date]
    low_row = history.loc[low_date]
    news = stock.news

    print(f"회사명: {company_name}")
    currency = info.get("currency", "USD")
    print(f"현재가: {current_price:,.2f} {currency}")
    print(f"전일대비등락률: {change_percent:+.2f}%")
    print(
        f"최근 1개월 최고점가: {high_row['High']:,.2f} {currency} "
        f"({high_date.strftime('%Y-%m-%d')}, 거래량: {high_row['Volume']:,.0f})"
    )
    print(
        f"최근 1개월 최저점가: {low_row['Low']:,.2f} {currency} "
        f"({low_date.strftime('%Y-%m-%d')}, 거래량: {low_row['Volume']:,.0f})"
    )
    print("최근 이슈사항 (최신 뉴스):")
    if news:
        for item in news[:3]:
            content = item.get("content", item)
            title = content.get("title")
            if title:
                print(f"- {title}")
    else:
        print("- 조회된 최근 뉴스가 없습니다.")


if __name__ == "__main__":
    main()
