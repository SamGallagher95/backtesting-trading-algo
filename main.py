import datetime
from finviz.screener import Screener
import json
import time
import requests
from app import util, daytime_loop, backtest


def main():
    # Load config
    config = load_config()

    # Close open positions
    close_positions(config)

    # Get stocks from fin viz
    tickers = get_tickers_from_screener(config)

    # Run backtests on top 10, find top ticker and config
    (ticker, ticker_config) = run_backtests(tickers, config)

    # Wait for market to open
    wait_for_market(config)

    # Set an interval loop, check the ticker price every 60 seconds.
    daytime_loop(ticker, ticker_config, config)

    # Stop executing on sell or market close
    market_close(config)


def market_close(config):
    print("Market is closed")
    pass


def daytime_loop(ticker, ticker_config, config):
    daytime_loop.execute(ticker, ticker_config, config)


def wait_for_market(config):
    t = datetime.datetime.today()
    future = datetime.datetime(t.year, t.month, t.day, 8, 30)
    time.sleep((future-t).total_seconds())


def run_backtests(tickers, config):
    (ticker, ticker_config) = backtest.execute(tickers, config)
    print(ticker)
    print(ticker_config)
    return (ticker, ticker_config)


def get_tickers_from_screener(config):
    stock_list = Screener(
        filters=config["finviz_filters"], table=config["finviz_table"], order=config["finviz_order"])
    tickers = list(map(lambda x: x['Ticker'], stock_list))
    tickers.reverse()
    return tickers[0:config['num_of_tickers']]


def close_positions(config):
    positions_response = requests.get(
        f"{config['api_root']}/v2/positions", headers=util.alpaca_headers())
    positions = positions_response.json()
    for position in positions:
        params = {
            'qty': position['qty']
        }
        response = requests.delete(
            f"{config['api_root']}/v2/positions/{position['symbol']}", headers=util.alpaca_headers(), params=params)


def load_config():
    with open('config.json', 'r') as f:
        config_str = f.read()
    return json.loads(config_str)


main()
