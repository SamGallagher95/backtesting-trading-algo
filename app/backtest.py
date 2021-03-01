import concurrent.futures
from datetime import datetime, timedelta
from tqdm import tqdm
import random
import json
import time
import uuid
import os
import requests
import math


def execute(tickers, config):
    out = {}
    for ticker in tickers:
        print(ticker)
        i = 0
        seed = uuid.uuid4()
        out[ticker] = []

        with tqdm(total=config['tests_to_run']) as pbar:
            with concurrent.futures.ThreadPoolExecutor(max_workers=config['threadpool_max_workers']) as executor:
                futures = []
                for x in range(0, config['tests_to_run']):
                    futures.append(executor.submit(
                        initialize_test, ticker, config, x))
                for future in concurrent.futures.as_completed(futures):
                    pbar.update(1)
                    (test_config, cash, trades) = future.result()
                    if cash > config['cash_per_test']:
                        out[ticker].append({
                            'config': test_config,
                            'ending_cash': cash,
                            'trades': trades
                        })

        print(f"Sleeping {config['backtest_sleep_seconds']} seconds...")
        time.sleep(config['backtest_sleep_seconds'])

    # Find the best config and ticker
    best_config = {
        'ending_cash': 0
    }
    best_ticker = ''
    for ticker in tickers:
        sorted_configs = sorted(out[ticker], key=lambda k: k['ending_cash'])
        sorted_configs.reverse()
        best_ticker_config = sorted_configs[0]
        if best_ticker_config['ending_cash'] > best_config['ending_cash']:
            best_config = best_ticker_config
            best_ticker = ticker

    # Run Iter Learn algorithm
    (best_config) = iter_learn(config, best_config)

    return (best_ticker, best_config)


def initialize_test(ticker, config, x):
    random.seed(time.time())

    # Create a new configuration
    ticker_config = {
        'tickers': [ticker],
        'days_to_test': config['days_to_test'],
        'cash': config['cash_per_test'],
        'epoch_interval': random.randint(config['epoch_interval_floor'], config['epoch_interval_ceiling']),
        'price_velocity_sell_threshold': random.uniform(config['price_velocity_sell_floor'], config['price_velocity_sell_ceiling']),
        'volume_velocity_sell_threshold': random.uniform(config['volume_velocity_sell_floor'], config['volume_velocity_sell_ceiling']),
        'epoch_velocity_sell_threshold': random.uniform(config['epoch_velocity_sell_floor'], config['epoch_velocity_sell_ceiling']),
        'price_velocity_buy_threshold': random.uniform(config['price_velocity_buy_floor'], config['price_velocity_buy_ceiling']),
        'volume_velocity_buy_threshold': random.uniform(config['volume_velocity_buy_floor'], config['volume_velocity_buy_ceiling']),
        'epoch_velocity_buy_threshold': random.uniform(config['epoch_velocity_buy_floor'], config['epoch_velocity_buy_ceiling'])
    }

    # Spawn the test
    (cash, trades) = backtest(ticker_config)
    return (ticker_config, cash, trades)


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
    for days_ago in range(0, config['days_to_test']):
        data = get_ticker(config['tickers'], config['days_to_test'] - days_ago)
        sold_today = False

        # Reverse the list
        data[config['tickers'][0]].reverse()

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
        if response.status_code != 200:
            print(response.status_code)
            print(params)
        return response.json()


def alpaca_headers():
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    return {
        'APCA-API-KEY-ID': api_key,
        'APCA-API-SECRET-KEY': secret_key
    }


def iter_learn(config, ticker_config_full):
    base_cash = ticker_config_full['ending_cash']
    ticker_config = dict(ticker_config_full['config'])
    print(f'Starting Iterative Learning with base cash: {base_cash}...')

    better_cash = 0
    num_changes = 0

    with tqdm(total=config["iter_learn_iterations"]) as pbar:
        for i in range(0, config["iter_learn_iterations"]):
            # Reseed random
            random.seed(uuid.uuid4())

            # Get a step value
            step = random.uniform(
                config["iter_learn_floor"], config["iter_learn_ceiling"])
            isNegative = random.randint(1, 100)
            if isNegative > 50:
                step = step * -1

            # Run the backtests
            (new_ticker_config, cash) = back_iteration(
                config, ticker_config, step, base_cash)

            if cash > base_cash and cash > better_cash:
                better_cash = cash
                ticker_config = new_ticker_config
                num_changes += 1

            pbar.update(1)

    if better_cash != 0 and better_cash != base_cash:
        print(f'Found better values, made: {better_cash}')
        print(f'Made {num_changes} changes.')

    ticker_config_full['config'] = dict(ticker_config)
    return ticker_config_full


# Backtest every possible combination of step and find best outcome
keys = [
    'price_velocity_sell_threshold',
    'volume_velocity_sell_threshold',
    'epoch_velocity_sell_threshold',
    'price_velocity_buy_threshold',
    'volume_velocity_buy_threshold',
    'epoch_velocity_buy_threshold'
]


def back_iteration(config, ticker_config, step, base_cash):
    rand_map = [
        random.randint(0, 100),
        random.randint(0, 100),
        random.randint(0, 100),
        random.randint(0, 100),
        random.randint(0, 100),
        random.randint(0, 100)
    ]

    new_ticker_config = dict(ticker_config)
    for i in range(0, len(rand_map)):
        if rand_map[i] > 50:
            new_ticker_config[keys[i]] += step

    (cash, trades) = backtest(new_ticker_config)

    return (new_ticker_config, cash)
