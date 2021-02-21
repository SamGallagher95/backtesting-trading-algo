from finviz.screener import Screener
import json
import app


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
    pass


def daytime_loop(ticker, ticker_config, config):
    pass


def wait_for_market(config):
    pass


def run_backtests(tickers, config):
    pass


def get_tickers_from_screener(config):
    stock_list = Screener(
        filters=config["finviz_filters"], table=config["finviz_table"], order=config["finviz_order"])
    tickers = list(map(lambda x: x['Ticker'], stock_list))
    tickers.reverse()
    return tickers[0:9]


def close_postitions(config):
    positions_response =


def load_config():
    with open('config.json', 'r') as f:
        config_str = f.read()
    return json.loads(config_str)
