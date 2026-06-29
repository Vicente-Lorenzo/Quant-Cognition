import yfinance as yf

from Library.Formulas import formula

@formula
def spot_price(ticker):
    data = yf.Ticker(ticker=ticker)
    price = data.info.get("regularMarketPrice")
    return price