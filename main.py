import boto3
import datetime
from finviz.screener import Screener
import json
import os
import time
import requests
from app import util, daytime_loop, backtest


def main():
    try:
        # Load config
        config = load_config()

        # Push start notification
        push_start_notification(config)

        # Close open positions
        close_positions(config)

        # Get stocks from fin viz
        tickers = get_tickers_from_screener(config)

        # Run backtests on top 10, find top ticker and config
        (ticker, ticker_config) = run_backtests(tickers, config)

        # Wait for market to open
        wait_for_market(config)

        # Set an interval loop, check the ticker price every 60 seconds.
        loop(ticker, ticker_config['config'], config)

        # Stop executing on sell or market close
        market_close(config)

        # Push finished notification
        push_stop_notification(config)

        kill_self(config)
    except Exception as e:
        push_error_notification(config, e)

        kill_self(config)


def market_close(config):
    print("Market is closed")
    pass


def loop(ticker, ticker_config, config):
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


def push_error_notification(config, e):
    response = requests.post('https://api.pushover.net/1/messages.json', data={
        "token": config["pushover_token"],
        "user": config["pushover_user"],
        "message": f"Daytrader encountered an error and quit. {e}"
    })


def push_stop_notification(config):
    response = requests.post('https://api.pushover.net/1/messages.json', data={
        "token": config["pushover_token"],
        "user": config["pushover_user"],
        "message": "Daytrader has finished!"
    })


def push_start_notification(config):
    response = requests.post('https://api.pushover.net/1/messages.json', data={
        "token": config["pushover_token"],
        "user": config["pushover_user"],
        "message": "Daytrader has started!"
    })


def load_config():
    # Get Alpaca creds
    client = boto3.client('ssm')
    api_key_response = client.get_parameter(
        Name='ALPACA_API_KEY',
        WithDecryption=True
    )
    secret_key_response = client.get_parameter(
        Name='ALPACA_SECRET_KEY',
        WithDecryption=True
    )
    api_key = api_key_response['Parameter']['Value']
    secret_key = secret_key_response['Parameter']['Value']
    os.environ['ALPACA_API_KEY'] = api_key
    os.environ['ALPACA_SECRET_KEY'] = secret_key

    # Get local config
    with open('config.json', 'r') as f:
        config_str = f.read()
    return json.loads(config_str)


def kill_self(config):
    client = boto3.client('lambda')
    response = client.invoke(
        FunctionName=config['kill_self_lambda_name'],
    )


main()
