"""Streamlit 기반 주식 시세 조회, 차트 표시, 과거 데이터 테이블 앱."""

# Plotly Graph Objects는 캔들스틱/거래량/이동평균 등 그래프 요소를 세밀하게 만든다.
import plotly.graph_objects as go
# Plotly Express는 종가 선 그래프를 간결하게 생성한다.
import plotly.express as px
# make_subplots는 가격과 거래량 그래프를 한 그림 안에 위아래로 배치한다.
from plotly.subplots import make_subplots
# Streamlit은 입력 위젯과 결과 화면을 제공하는 웹 앱 프레임워크다.
import streamlit as st
# yfinance는 Yahoo Finance에서 주가와 종목 정보를 가져오는 라이브러리다.
import yfinance as yf


# 화면에 보이는 기간을 Yahoo Finance가 받는 기간 문자열로 연결한다.
PERIODS = {
    "1개월": "1mo",  # 최근 1개월 조회에 쓰는 API 기간 코드
    "3개월": "3mo",  # 최근 3개월 조회에 쓰는 API 기간 코드
    "6개월": "6mo",  # 최근 6개월 조회에 쓰는 API 기간 코드
    "1년": "1y",  # 최근 1년 조회에 쓰는 API 기간 코드
}


def _first_available(*values):
    """인수 중 None이 아닌 첫 값을 반환해 대체 데이터 후보를 선택한다."""
    return next((value for value in values if value is not None), None)


# 페이지 제목, 아이콘, 넓은 레이아웃을 브라우저에 적용한다.
st.set_page_config(page_title="주식데이터분석기", page_icon="📈", layout="wide")
# 앱 상단에 표시할 메인 제목이다.
st.title("주식데이터분석기")

# 종목과 기간 입력, 조회 버튼을 하나의 제출 폼으로 묶는다.
with st.form("stock_lookup"):
    # 사용자가 입력한 Yahoo Finance 종목 코드이며 공백은 앞뒤에서 제거한다.
    ticker_symbol = st.text_input(
        "종목 코드 (쉼표로 구분)",
        value="005930.KS",
        help="여러 종목은 쉼표로 구분해 입력하세요. 예: 005930.KS, 000660.KS",
    ).strip()
    # PERIODS의 한국어 표시명을 선택해 조회 기간을 정한다.
    selected_period = st.selectbox("기간선택", options=list(PERIODS))
    # 버튼 제출 시에만 새 주가 데이터를 요청하도록 하는 불리언 값이다.
    submitted = st.form_submit_button("데이터조회")

# 입력한 쉼표 구분 코드를 정리하고 중복 티커를 제거한다.
ticker_symbols = list(
    dict.fromkeys(
        symbol.strip().upper()
        for symbol in ticker_symbol.split(",")
        if symbol.strip()
    )
)

# 이번 rerun이 새 데이터 조회 요청인지 기억해 캐시 결과와 구분한다.
new_lookup = submitted
# 새 조회 전에는 이전 응답이 화면에 남지 않도록 저장 결과를 지운다.
if new_lookup:
    st.session_state.pop("stock_lookup_result", None)
# 버튼을 다시 누르지 않아도 체크박스 조작 때 저장된 결과를 다시 그린다.
submitted = submitted or "stock_lookup_result" in st.session_state

# 새 조회 또는 세션에 저장된 직전 결과가 있을 때 결과 화면을 구성한다.
if submitted:
    # 새 요청에서 종목 코드가 비어 있으면 외부 조회 없이 안내한다.
    if new_lookup and not ticker_symbols:
        st.error("종목 코드를 하나 이상 입력해 주세요.")
    else:
        # 네트워크 및 데이터 형식 문제를 앱의 오류 메시지로 보여준다.
        try:
            # 새 제출 때만 외부 통신을 수행하고 결과를 세션에 저장한다.
            if new_lookup:
                # 첫 번째 티커를 기존 지표/상세 차트에서 사용할 대표 종목으로 삼는다.
                ticker_symbol = ticker_symbols[0]
                # 느린 네트워크 요청 중 사용자에게 진행 상태를 알린다.
                with st.spinner("주식 데이터를 조회하고 있습니다..."):
                    # ticker_symbol 종목에 대한 yfinance 조회 객체다.
                    stock = yf.Ticker(ticker_symbol)
                    # history는 선택한 화면 기간에 해당하는 OHLCV DataFrame이다.
                    history = stock.history(period=PERIODS[selected_period])
                    # 이동평균 계산에 필요한 직전 거래일을 포함하도록 1년 데이터를 읽는다.
                    moving_average_history = stock.history(period="1y")
                    # info는 회사명, 통화, 현재가와 전일 종가 등의 메타데이터다.
                    info = stock.info

                    # 비교 차트에 그릴 티커별 선택 기간 종가와 회사명을 수집한다.
                    comparison_data = []
                    for comparison_symbol in ticker_symbols:
                        if comparison_symbol == ticker_symbol:
                            comparison_history = history
                            comparison_info = info
                        else:
                            comparison_stock = yf.Ticker(comparison_symbol)
                            comparison_history = comparison_stock.history(
                                period=PERIODS[selected_period]
                            )
                            comparison_info = comparison_stock.info

                        if (
                            comparison_history.empty
                            or "Close" not in comparison_history
                            or comparison_history["Close"].dropna().empty
                        ):
                            raise ValueError(
                                f"{comparison_symbol}의 "
                                f"{selected_period} 종가 데이터를 찾을 수 없습니다."
                            )

                        comparison_name = _first_available(
                            comparison_info.get("longName"),
                            comparison_info.get("shortName"),
                            comparison_symbol,
                        )
                        comparison_data.append(
                            {
                                "ticker": comparison_symbol,
                                "name": comparison_name,
                                "close": comparison_history["Close"].dropna(),
                            }
                        )

                # 위젯을 조작할 때 재조회하지 않도록 새 응답을 세션 상태에 보관한다.
                st.session_state["stock_lookup_result"] = {
                    "ticker_symbol": ticker_symbol,  # 조회 응답에 대응하는 종목 코드
                    "selected_period": selected_period,  # 응답 데이터의 선택 기간
                    "history": history,  # 표와 차트에 사용할 선택 기간 OHLCV 기록
                    "moving_average_history": moving_average_history,  # 평균선 계산용 1년 종가 기록
                    "info": info,  # 회사명, 가격, 통화 등 종목 정보
                    "ticker_symbols": ticker_symbols,  # 비교할 전체 티커 목록
                    "comparison_data": comparison_data,  # 비교할 티커별 회사명 및 종가
                }
            else:
                # 체크박스/탭 조작으로 rerun된 경우 이전 API 결과를 복원한다.
                lookup_result = st.session_state["stock_lookup_result"]
                # 표시할 종목 코드를 기존 응답의 값으로 복원한다.
                ticker_symbol = lookup_result["ticker_symbol"]
                # 표시할 조회 기간을 기존 응답의 값으로 복원한다.
                selected_period = lookup_result["selected_period"]
                # 차트와 표에서 쓸 가격/거래량 기록을 기존 응답에서 가져온다.
                history = lookup_result["history"]
                # 5/20/60 거래일 평균 계산을 위해 저장한 1년 자료를 가져온다.
                moving_average_history = lookup_result["moving_average_history"]
                # 회사명과 시세 metadata를 기존 응답에서 가져온다.
                info = lookup_result["info"]
                # 비교 데이터가 없는 구버전 세션이면 대표 종목 하나로 대체한다.
                ticker_symbols = lookup_result.get("ticker_symbols", [ticker_symbol])
                comparison_data = lookup_result.get(
                    "comparison_data",
                    [
                        {
                            "ticker": ticker_symbol,
                            "name": _first_available(
                                info.get("longName"),
                                info.get("shortName"),
                                ticker_symbol,
                            ),
                            "close": history["Close"].dropna(),
                        }
                    ],
                )

            # 데이터가 비었거나 종가 열이 없으면 잘못된 티커/응답으로 처리한다.
            if history.empty or "Close" not in history:
                # 호출자가 알아볼 수 있도록 종목과 선택 기간을 오류에 포함한다.
                raise ValueError(
                    f"{ticker_symbol}의 {selected_period} 역사적 데이터를 찾을 수 없습니다."
                )

            # 우선 긴 회사명을 사용하고 없으면 짧은 이름으로 대체한다.
            company_name = _first_available(
                info.get("longName"), info.get("shortName")
            )
            # 현재가 메타데이터가 없으면 선택 기간 마지막 종가를 대체 값으로 쓴다.
            current_price = _first_available(
                info.get("currentPrice"),
                info.get("regularMarketPrice"),
                history["Close"].iloc[-1],
            )
            # 전일 종가 메타데이터가 없으면 기록에서 직전 종가를 사용한다.
            previous_close = _first_available(
                info.get("previousClose"),
                info.get("regularMarketPreviousClose"),
                history["Close"].iloc[-2] if len(history) > 1 else None,
            )

            # 유효한 전일 종가가 없으면 등락률 계산을 중단한다.
            if previous_close is None or previous_close <= 0:
                # 0으로 나누거나 의미 없는 등락률을 표시하지 않도록 오류 처리한다.
                raise ValueError("전일 종가 정보를 찾을 수 없어 등락률을 계산할 수 없습니다.")

            # 전일 종가 대비 현재가의 변화를 퍼센트로 환산한다.
            change_percent = (current_price / previous_close - 1) * 100
            # Yahoo 통화 코드를 우선 쓰고 없으면 한국 종목 코드에 KRW를 적용한다.
            currency = info.get("currency") or (
                "KRW" if ticker_symbol.upper().endswith((".KS", ".KQ")) else ""
            )
            # 원화는 소수점 없이, 그 외 통화는 소수점 둘째 자리까지 표시한다.
            decimals = 0 if currency == "KRW" else 2
            # 천 단위 구분과 통화 단위를 적용해 화면용 현재가 문자열을 만든다.
            price_text = f"{current_price:,.{decimals}f} {currency}".strip()

            # 사이드바 계산기는 상세 종목인 첫 번째 티커의 거래 기록을 기준으로 한다.
            purchase_dates = list(history.index)
            st.sidebar.header("수익률 계산기")
            st.sidebar.caption(f"{company_name or ticker_symbol} ({ticker_symbol})")
            # 조회된 거래일 중에서 매수일을 고른다.
            purchase_date = st.sidebar.selectbox(
                "매수 날짜 선택",
                options=purchase_dates,
                format_func=lambda date: date.strftime("%Y-%m-%d"),
                key=f"purchase_date_{ticker_symbol}_{selected_period}",
            )
            # 매수에 사용한 금액이며, 현재가치 계산에 사용한다.
            investment_amount = st.sidebar.number_input(
                f"매수 금액 ({currency or '통화 단위'})",
                min_value=1.0,
                value=1_000_000.0 if currency == "KRW" else 1_000.0,
                step=10_000.0 if currency == "KRW" else 100.0,
                key="investment_amount",
            )
            # 매수일 종가를 기준 가격으로 사용한다.
            purchase_price = float(history.loc[purchase_date, "Close"])
            if purchase_price <= 0:
                raise ValueError("선택한 매수일의 종가가 올바르지 않아 계산할 수 없습니다.")

            # 매수 금액 전체를 매수일 종가에 투자했다고 가정해 현재 가치를 환산한다.
            current_value = investment_amount * current_price / purchase_price
            # 손익 금액과 매수 금액 대비 수익률(%)을 계산한다.
            profit_loss = current_value - investment_amount
            investment_return = profit_loss / investment_amount * 100
            # 수익은 빨간색, 손실은 파란색으로 표시한다.
            return_color = "red" if profit_loss >= 0 else "blue"
            st.sidebar.metric(
                "현재 가치",
                f"{current_value:,.{decimals}f} {currency}".strip(),
            )
            st.sidebar.markdown(
                f":{return_color}[수익률: {investment_return:+.2f}%]"
            )
            st.sidebar.caption(
                f"손익: {profit_loss:+,.{decimals}f} {currency}".strip()
            )

            # 조회 성공을 사용자에게 명시한다.
            st.success("데이터 조회가 완료되었습니다.")
            # 회사명이 없으면 회사명 정보 없음과 티커를 함께 표시한다.
            st.subheader(company_name or f"회사명 정보 없음 ({ticker_symbol})")
            # 현재가/등락률 지표를 나란히 배치할 두 칸이다.
            col1, col2 = st.columns(2)
            # 첫 번째 칸에 통화와 함께 현재가를 표시한다.
            col1.metric("현재가", price_text)
            # 두 번째 칸에 부호와 소수점 두 자리로 등락률을 표시한다.
            col2.metric("전일대비 등락률", f"{change_percent:+.2f}%")

            # 그래프 제목용 회사명이며, 없을 때는 티커를 쓴다.
            display_name = company_name or ticker_symbol
            # yfinance 날짜 인덱스를 차트에서 범주형으로 쓸 날짜 문자열로 변환한다.
            trading_dates = history.index.strftime("%Y-%m-%d")
            # 1년 기록에서 계산한 단순 이동평균을 차트 표시 날짜로 맞춘다.
            moving_averages = {
                # 최근 5 거래일 종가 평균을 선택 기간 날짜에 정렬한다.
                5: moving_average_history["Close"].rolling(window=5).mean().reindex(
                    history.index
                ),
                # 최근 20 거래일 종가 평균을 선택 기간 날짜에 정렬한다.
                20: moving_average_history["Close"].rolling(window=20).mean().reindex(
                    history.index
                ),
                # 최근 60 거래일 종가 평균을 선택 기간 날짜에 정렬한다.
                60: moving_average_history["Close"].rolling(window=60).mean().reindex(
                    history.index
                ),
            }
            # 각 평균선 기간을 사용자가 구분할 색상으로 연결한다.
            ma_colors = {5: "orange", 20: "green", 60: "red"}
            # 체크박스를 가로로 정렬해 세 개 놓을 컬럼을 만든다.
            checkbox_columns = st.columns(3)
            # 각 체크박스의 현재 표시 여부를 기간별 불리언 값으로 저장한다.
            show_moving_averages = {
                # period 값으로 체크박스 이름/상태 키를 만들고 지정 컬럼에 출력한다.
                period: checkbox_columns[index].checkbox(
                    f"{period}일 이동평균선",  # 체크박스에 보여줄 선 이름
                    value=True,  # 처음에는 해당 평균선을 표시하도록 한다.
                    key=f"show_ma_{period}",  # Streamlit rerun 사이에도 체크 상태를 유지한다.
                )
                # 이동평균 기간을 0부터 시작하는 컬럼 위치와 함께 순회한다.
                for index, period in enumerate(moving_averages)
            }
            # 동일한 평균선 체크 상태가 두 차트에 적용되도록 탭을 만든다.
            line_tab, candlestick_tab, comparison_tab = st.tabs(
                ["선 차트", "캔들스틱 차트", "종목 비교"]  # 탭 이름 및 출력 순서
            )
            # 첫 번째 탭에는 종가 선과 체크된 이동평균선을 표시한다.
            with line_tab:
                # 종가 열을 날짜별로 연결하는 Plotly Express 선 그래프다.
                chart = px.line(
                    history,  # 선택 기간의 OHLCV 데이터
                    x=trading_dates,  # 실제 거래가 있었던 날짜만 범주 축으로 사용
                    y="Close",  # 종가를 세로축 값으로 사용
                    title=f"{display_name} 주가 추이",  # 회사명 기반 그래프 제목
                    labels={"x": "날짜", "Close": f"가격 ({currency})".strip()},  # 축에 표시할 한국어 이름
                )
                # 종가 선에 날짜/가격 형식을 적용해 hover 정보를 읽기 쉽게 한다.
                chart.update_traces(
                    hovertemplate=(
                        f"%{{x}}<br>"  # 마우스가 가리킨 거래 날짜
                        f"가격: %{{y:,.{decimals}f}} {currency}<extra></extra>"  # 통화 형식 종가
                    )
                )
                # 체크된 이동평균만 종가 선 그래프 위에 추가한다.
                for period, average in moving_averages.items():
                    # show_moving_averages는 해당 기간 체크박스의 표시 여부다.
                    if show_moving_averages[period]:
                        # average 시계열을 점 없이 선으로 그리고 기간별 색으로 구분한다.
                        chart.add_scatter(
                            x=trading_dates,  # 종가와 같은 실제 거래 날짜 축
                            y=average,  # 현재 loop의 기간별 이동평균 값
                            mode="lines",  # 점 기호 없이 선만 그린다.
                            name=f"{period}일 이동평균선",  # 범례에 표시할 선 이름
                            line={"color": ma_colors[period]},  # 기간별로 지정한 색상
                            hovertemplate=(  # 이동평균 값에 맞는 마우스 오버 문구
                                "%{x}<br>"  # 이동평균 값의 거래 날짜
                                f"{period}일 평균: "  # 선 기간을 표시하는 이름
                                f"%{{y:,.{decimals}f}} {currency}<extra></extra>"  # 포맷한 이동평균 가격
                            ),
                        )
                # x축 날짜 범주와 통합 hover를 설정하고 그래프 너비를 화면에 맞춘다.
                chart.update_layout(
                    xaxis_title="날짜",  # 가로축의 한국어 제목
                    xaxis_type="category",  # 거래가 없는 휴일 간격을 차트에서 제거
                    hovermode="x unified",  # 같은 날짜의 종가/평균선을 함께 hover 표시
                )
                # 전체 너비의 인터랙티브 선 차트를 Streamlit 페이지에 그린다.
                st.plotly_chart(chart, width="stretch")

            # 두 번째 탭에는 가격 캔들, 평균선, 거래량을 함께 표시한다.
            with candlestick_tab:
                # 선택 기간에 관측된 일별 거래량의 산술 평균이다.
                average_volume = history["Volume"].mean()
                # 평균 초과 거래일은 금색, 나머지는 상승 빨강/하락 파랑으로 칠한다.
                volume_colors = [
                    "gold"  # 평균보다 거래량이 많은 날을 두드러지게 표시한다.
                    if volume > average_volume  # volume은 이번 거래일의 거래량이다.
                    else ("red" if close >= open_price else "blue")  # 캔들 상승/하락 색상
                    for open_price, close, volume in zip(  # 같은 행의 시가/종가/거래량을 묶는다.
                        history["Open"], history["Close"], history["Volume"]  # 색 결정에 필요한 세 열
                    )
                ]
                # 두 그래프를 위아래로 쌓고 날짜 축과 확대/이동을 공유하게 만든다.
                candlestick_chart = make_subplots(
                    rows=2,  # 1행은 가격, 2행은 거래량 그래프
                    cols=1,  # 두 그래프 모두 한 개의 열에 배치
                    shared_xaxes=True,  # 위/아래 그래프가 날짜 축을 공유
                    vertical_spacing=0.04,  # 두 그래프 사이의 간격 비율
                    row_heights=[0.7, 0.3],  # 차트 높이 중 가격 70%, 거래량 30%
                )
                # 1행에 시가/고가/저가/종가 기반 캔들스틱을 추가한다.
                candlestick_chart.add_trace(
                    go.Candlestick(
                        x=trading_dates,  # 휴일을 제외한 거래 날짜
                        open=history["Open"],  # 각 거래일의 시가
                        high=history["High"],  # 각 거래일의 고가
                        low=history["Low"],  # 각 거래일의 저가
                        close=history["Close"],  # 각 거래일의 종가
                        showlegend=False,  # 캔들 자체는 범례를 차지하지 않게 한다.
                        increasing_line_color="red",  # 종가가 시가 이상인 상승 캔들 색
                        decreasing_line_color="blue",  # 종가가 시가보다 낮은 하락 캔들 색
                        hovertemplate=(  # 캔들에 마우스를 올렸을 때 표시할 값 형식
                            "%{x}<br>"  # 캔들의 거래 날짜
                            f"시가: %{{open:,.{decimals}f}} {currency}<br>"  # 시작 가격
                            f"고가: %{{high:,.{decimals}f}} {currency}<br>"  # 해당 거래일 최고 가격
                            f"저가: %{{low:,.{decimals}f}} {currency}<br>"  # 해당 거래일 최저 가격
                            f"종가: %{{close:,.{decimals}f}} {currency}"  # 종료 가격
                            "<extra></extra>"  # Plotly 기본 trace 이름 박스를 숨긴다.
                        ),
                    ),
                    row=1,  # 가격 그래프 행
                    col=1,  # 첫 번째 그래프 열
                )
                # 체크된 이동평균선만 캔들 가격 행에 겹쳐 그린다.
                for period, average in moving_averages.items():
                    # 체크박스가 켜진 평균선만 이 탭에서도 표시한다.
                    if show_moving_averages[period]:
                        # 기간별 이동평균 시계열을 첫 번째 행에 선으로 추가한다.
                        candlestick_chart.add_trace(
                            go.Scatter(
                                x=trading_dates,  # 캔들과 동일한 거래 날짜
                                y=average,  # 해당 기간의 이동평균 값
                                mode="lines",  # 평균을 선으로 표시
                                name=f"{period}일 이동평균선",  # Plotly 범례 텍스트
                                line={"color": ma_colors[period]},  # 선 기간에 대응하는 색
                                hovertemplate=(  # 마우스 오버 시 평균값을 표시하는 형식
                                    "%{x}<br>"  # 평균값이 계산된 거래 날짜
                                    f"{period}일 평균: "  # 이동평균 기간 표시
                                    f"%{{y:,.{decimals}f}} {currency}<extra></extra>"  # 평균 가격
                                ),
                            ),
                            row=1,  # 가격 및 캔들이 있는 윗 행
                            col=1,  # 첫 번째 열
                        )
                # 2행에 거래량 막대를 추가하고 평균 초과 날짜는 금색으로 강조한다.
                candlestick_chart.add_trace(
                    go.Bar(
                        x=trading_dates,  # 캔들과 공유하는 거래 날짜
                        y=history["Volume"],  # 일별 거래량
                        name="거래량",  # trace 이름; 아래에서 범례는 숨긴다.
                        showlegend=False,  # 이동평균 범례만 유지하고 거래량 항목은 생략
                        marker_color=volume_colors,  # 평균/상승/하락 규칙으로 계산한 막대색
                        hovertemplate=(  # 날짜별 거래량 hover 문구
                            "%{x}<br>거래량: %{y:,.0f}<extra></extra>"  # 날짜와 천 단위 거래량
                        ),
                    ),
                    row=2,  # 거래량 그래프 행
                    col=1,  # 첫 번째 열
                )
                # 거래량 평균을 점선으로 그려 높은 거래량의 기준을 제공한다.
                candlestick_chart.add_hline(
                    y=average_volume,  # 조회 구간 평균 거래량의 세로 좌표
                    line_dash="dash",  # 평균선은 막대와 구분되게 점선 처리
                    line_color="gray",  # 기준선 색상
                    annotation_text="평균 거래량",  # 기준선 설명
                    row=2,  # 거래량 그래프에만 기준선을 배치
                    col=1,  # 첫 번째 열에 배치
                )
                # 차트 제목, 공통 hover, 범례와 캔들 하단 슬라이더를 설정한다.
                candlestick_chart.update_layout(
                    title=f"{display_name} 캔들스틱 차트",  # 회사명 기반 캔들 그래프 제목
                    hovermode="x unified",  # 같은 날짜의 캔들/평균값/거래량을 함께 hover 표시
                    xaxis_rangeslider_visible=False,  # 캔들 차트 기본 하단 범위 선택기를 감춘다.
                    showlegend=True,  # 표시 중인 이동평균을 범례에서 켜고 끌 수 있다.
                )
                # 두 행의 x축을 범주형으로 만들어 휴일 날짜 간격을 생략한다.
                candlestick_chart.update_xaxes(type="category")
                # 하단 거래량 행의 가로축 제목을 날짜로 지정한다.
                candlestick_chart.update_xaxes(
                    title_text="날짜",  # 하단 공유 날짜 축의 제목
                    row=2,  # 거래량 행의 x축에 제목 표시
                    col=1,  # 첫 번째 열의 축
                )
                # 위쪽 가격 행의 세로축에 통화 단위를 표시한다.
                candlestick_chart.update_yaxes(
                    title_text=f"가격 ({currency})".strip(),  # 가격축 이름と 통화
                    row=1,  # 캔들과 이동평균이 있는 가격 행
                    col=1,  # 첫 번째 열
                )
                # 아래쪽 거래량 행의 세로축을 거래량으로 표시한다.
                candlestick_chart.update_yaxes(
                    title_text="거래량",  # 거래량축의 한국어 제목
                    row=2,  # 거래량 막대가 있는 아래 행
                    col=1,  # 첫 번째 열
                )
                # 화면 너비에 맞는 인터랙티브 캔들/거래량 차트를 그린다.
                st.plotly_chart(candlestick_chart, width="stretch")

            # 선택 기간 시작일 기준 수익률을 여러 종목 한 그래프에 비교한다.
            with comparison_tab:
                # Plotly의 색상 팔레트에서 티커마다 다른 선 색을 선택한다.
                comparison_colors = px.colors.qualitative.Plotly
                comparison_chart = go.Figure()
                for index, item in enumerate(comparison_data):
                    # close_series는 현재 티커의 결측 종가를 제외한 가격 시계열이다.
                    close_series = item["close"].dropna()
                    if close_series.empty or close_series.iloc[0] == 0:
                        raise ValueError(
                            f"{item['ticker']}의 시작 종가로 수익률을 계산할 수 없습니다."
                        )

                    # 첫 거래일 종가를 0% 기준으로 하여 이후 변화를 백분율로 계산한다.
                    normalized_return = (
                        close_series / close_series.iloc[0] - 1
                    ) * 100
                    # 같은 회사명이 여럿이면 티커를 덧붙여 범례를 구별한다.
                    legend_name = item["name"]
                    if sum(
                        entry["name"] == legend_name for entry in comparison_data
                    ) > 1:
                        legend_name = f"{legend_name} ({item['ticker']})"

                    comparison_chart.add_trace(
                        go.Scatter(
                            x=normalized_return.index.strftime("%Y-%m-%d"),
                            y=normalized_return,
                            mode="lines",
                            name=legend_name,
                            line={
                                "color": comparison_colors[
                                    index % len(comparison_colors)
                                ]
                            },
                            hovertemplate=(
                                "%{x}<br>시작일 대비 수익률: "
                                "%{y:+.2f}%<extra></extra>"
                            ),
                        )
                    )

                comparison_chart.update_layout(
                    title=f"{selected_period} 종목별 시작일 기준 수익률 비교",
                    xaxis_title="날짜",
                    xaxis_type="category",
                    yaxis_title="시작일 대비 수익률 (%)",
                    hovermode="x unified",
                )
                st.caption(
                    "각 종목의 선택 기간 첫 거래일 종가를 기준으로 수익률을 계산합니다."
                )
                st.plotly_chart(comparison_chart, width="stretch")

            # 차트 아래에 선택 기간 이름을 붙인 역사 데이터 섹션을 만든다.
            st.subheader(f"역사적 데이터 ({selected_period})")
            # Yahoo Finance의 영문 열 이름을 사용자에게 친숙한 한국어로 바꾼다.
            display_history = history.rename(
                columns={
                    "Open": "시가",  # 해당 날짜 첫 거래 가격
                    "High": "고가",  # 해당 날짜 최고 가격
                    "Low": "저가",  # 해당 날짜 최저 가격
                    "Close": "종가",  # 해당 날짜 마지막 가격
                    "Adj Close": "수정종가",  # 배당/분할을 반영한 조정 가격
                    "Volume": "거래량",  # 해당 날짜 거래된 주식 수
                    "Dividends": "배당금",  # 해당 날짜 배당 정보
                    "Stock Splits": "주식분할",  # 해당 날짜 주식분할 비율
                }
            )
            # 전체 너비의 데이터프레임으로 조회된 역사 데이터를 표시한다.
            st.dataframe(display_history, use_container_width=True)
        # 조회/가공/표시 중 발생한 예외를 사용자에게 숨기지 않고 알린다.
        except Exception as exc:
            # 오류 내용을 화면에 출력해 종목 코드/API/데이터 문제를 진단할 수 있다.
            st.error(f"데이터 조회에 실패했습니다: {exc}")
