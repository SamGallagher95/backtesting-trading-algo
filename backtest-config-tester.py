import concurrent.futures
from tqdm import tqdm
import random
import json
import time
import uuid
import os
from backtester import backtest

# Each config will test against these tickers
# tickers = ['RKDA', 'REPH', 'GNCA', 'CERC',
#            'VIVE', 'QTT', 'TTI', 'SESN', 'PHX', 'MREO']

tickers = ['RKDA']

# How much cash does each test have?
cash_per_test = 1000

# How many days do we test?
days_to_test = 14

# How many tests do we run?
tests_to_run = 400000


def main():
    i = 0
    seed = uuid.uuid4()
    out = []

    with tqdm(total=tests_to_run) as pbar:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for x in range(0, tests_to_run):
                futures.append(executor.submit(initialize_test, x))
            for future in concurrent.futures.as_completed(futures):
                pbar.update(1)
                (config, cash, trades) = future.result()
                if cash > cash_per_test:
                    out.append({
                        'config': config,
                        'ending_cash': cash,
                        'trades': trades
                    })

    if len(out) > 0:
        print(f'Writing {seed}.')
        sorted_out = sorted(out, key=lambda k: k['ending_cash'])
        sorted_out.reverse()
        with open(f'backtests/temp/{seed}-out.json', 'x') as f:
            f.write(json.dumps(sorted_out))
        print('Best')
        best = sorted_out[0]
        print(
            f"{best['ending_cash']},{best['config']['price_velocity_sell_threshold']},{best['config']['price_velocity_buy_threshold']},{best['config']['volume_velocity_sell_threshold']},{best['config']['volume_velocity_buy_threshold']},{best['config']['epoch_velocity_sell_threshold']},{best['config']['epoch_velocity_buy_threshold']},{best['config']['epoch_interval']}")
    else:
        print(f'Not writing output')


def initialize_test(x):
    random.seed(time.time())

    # Create new configuration
    config = {
        'tickers': tickers,
        'days_to_test': days_to_test,
        'cash': cash_per_test,
        'epoch_interval': random.randint(1, 200),
        'price_velocity_sell_threshold': random.uniform(0.5, 1.5),
        'volume_velocity_sell_threshold': random.uniform(0.5, 1.5),
        'price_velocity_buy_threshold': random.uniform(0.5, 1.5),
        'volume_velocity_buy_threshold': random.uniform(0.5, 20),
        'epoch_velocity_sell_threshold': random.uniform(0.5, 1.5),
        'epoch_velocity_buy_threshold': random.uniform(0.5, 1.5)
    }

    # Spawn the test
    (cash, trades) = backtest(config)
    return (config, cash, trades)


main()
