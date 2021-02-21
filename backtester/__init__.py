from datetime import datetime, timedelta
import requests
import os
import json
import math


def backtest(config):
    # Setup vars for the entire test
    price_map = {}
    velocity_map = {}
    velocity_epoch_map = {}
    volume_map = {}
    volume_velocity_map = {}
    epoch = {}
    sold_today = False
    is_order_open = False
    order_ticker = ""
    trades = []
    buy_price = 0
    sell_price = 0
    cash = config['cash']

    for ticker in config['tickers']:
        epoch[ticker] = 0
        price_map[ticker] = []
        velocity_map[ticker] = []
        velocity_epoch_map[ticker] = []
        volume_map[ticker] = []
        volume_velocity_map[ticker] = []

    # Define local buy function
    def buy(ticker, price):
        nonlocal cash, is_order_open, order_ticker
        quantity = math.floor(cash / price)
        value = quantity * price

        # Create the trade
        trades.append({
            'type': 'Buy',
            'ticker': ticker,
            'price': price,
            'quantity': quantity,
            'value': value
        })

        # Update variables
        cash -= value
        is_order_open = True
        order_ticker = ticker

    # Define local sell function
    def sell(ticker, price):
        nonlocal cash, is_order_open, order_ticker, sold_today
        buy_trade = trades[-1]
        quantity = buy_trade['quantity']
        value = quantity * price

        # Create the trade
        trades.append({
            'type': 'Sell',
            'ticker': ticker,
            'price': price,
            'quantity': quantity,
            'value': value
        })

        # Update variables
        cash = value
        is_order_open = False
        order_ticker = ""
        sold_today = True

    # Iterate through each day
    for days_ago in range(1, config['days_to_test'] + 1):
        data = get_ticker(config['tickers'], days_ago)
        sold_today = False

        # Iterate through each data point
        for i in range(0, len(data[config['tickers'][0]])):

            # Iterate through each ticker
            for ticker in config['tickers']:
                # Check skip condition
                if is_order_open and order_ticker != ticker:
                    continue
                elif sold_today:
                    continue
                elif i >= len(data[ticker]):
                    continue

                item = data[ticker][i]

                # Collect new data
                price = item['o']
                volume = item['v']
                if epoch[ticker] == 0:
                    velocity = 0
                    volume_velocity = 0
                else:
                    velocity = price/price_map[ticker][-1]
                    volume_velocity = volume/volume_map[ticker][-1]
                price_map[ticker].append(price)
                volume_map[ticker].append(volume)
                velocity_map[ticker].append(velocity)
                volume_velocity_map[ticker].append(volume_velocity)

                # Check sell conditions
                if is_order_open:
                    if velocity <= config['price_velocity_sell_threshold']:
                        sell(ticker, price)
                    elif volume_velocity <= config['volume_velocity_sell_threshold']:
                        sell(ticker, price)

                # Check buy conditions
                if is_order_open == False:
                    if velocity >= config['price_velocity_buy_threshold']:
                        buy(ticker, price)
                    elif volume_velocity >= config['volume_velocity_buy_threshold']:
                        buy(ticker, price)

                # Iterate the epoch
                epoch[ticker] += 1
                if epoch[ticker] % config['epoch_interval'] == 0:
                    epoch_velocity = price / \
                        price_map[ticker][config['epoch_interval']*-1]
                    velocity_epoch_map[ticker].append(epoch_velocity)

                    # Check sell conditions
                    if is_order_open:
                        if epoch_velocity <= config['epoch_velocity_sell_threshold']:
                            sell(ticker, price)

                    # Check buy conditions
                    if is_order_open == False:
                        if epoch_velocity >= config['epoch_velocity_buy_threshold']:
                            buy(ticker, price)

    return cash, trades


cache = {}


def get_ticker(tickers, days_ago):
    after_date = datetime.now() - timedelta(days=days_ago)
    until_date = datetime.now() - timedelta(days=days_ago - 1)
    params = {
        'symbols': ','.join(tickers),
        'after': f"{after_date.isoformat().split('T')[0]}T00:00:00-00:00",
        'until': f"{until_date.isoformat().split('T')[0]}T00:00:00-00:00",
        'limit': 1000
    }
    url = "https://data.alpaca.markets/v1/bars/1Min"

    # Check cache
    cache_key = json.dumps(params).__hash__()
    if cache_key in cache:
        return cache[cache_key]
    else:
        # Fetch the data
        response = requests.get(
            url, headers=alpaca_headers(), params=params)
        cache[cache_key] = response.json()
        return response.json()


def alpaca_headers():
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    return {
        'APCA-API-KEY-ID': api_key,
        'APCA-API-SECRET-KEY': secret_key
    }
