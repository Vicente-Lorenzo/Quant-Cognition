import yfinance as yf
from datetime import timedelta

from Library.Formulas import formula

@formula
def historical_price(tickers, start_date, stop_date, series, adjust):
    stop_date = stop_date or start_date+timedelta(days=1)
    data = yf.download(tickers=tickers, start=start_date, end=stop_date, auto_adjust=adjust)
    if data.empty:
        return None
    return data[series] if series else data