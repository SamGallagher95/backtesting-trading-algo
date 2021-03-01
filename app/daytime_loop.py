import time
from datetime import datetime, timedelta
import requests
import math
from . import util


def execute(ticker, ticker_config, config):
    print(ticker)
    print(ticker_config)

    # Prep time loop
    t = datetime.today()
    market_close = datetime(t.year, t.month, t.day, 16, 0)

    # Prep vars
    last_timestamp = 0
    price_map = []
    velocity_map = []
    velocity_epoch_map = []
    volume_map = []
    volume_velocity_map = []
    epoch = 0
    sold_today = False
    is_order_open = False
    trades = []
    cash = get_starting_cash(config) / 2
    flag = True

    def buy(price):
        nonlocal cash, is_order_open
        quantity = math.floor(cash / price)
        value = quantity * price

        print(f'Buying {quantity} of {ticker} for {value}.')

        data = {
            'symbol': ticker,
            'qty': quantity,
            'side': 'buy',
            'type': 'market',
            'time_in_force': 'ioc'
        }
        response = requests.post(
            f"{config['api_root']}/v1/orders", json=data, headers=util.alpaca_headers())
        print(response)
        print(response.json())
        print(response.status_code)

        # Update variables
        is_order_open = True

    def sell(price):
        nonlocal is_order_open, sold_today

        print('Closing positions.')

        response = requests.delete(
            f"{config['api_root']}/v2/positions", headers=util.alpaca_headers())
        print(response)
        print(response.json())
        print(response.status_code)

        # Update variables
        is_order_open = False
        sold_today = True
        flag = False

    while flag:
        print(f'Tick at {time.ctime()}')

        # Check time
        now = datetime.now()
        if now >= market_close:
            print("Market is closed")
            tl.stop()

        # Check stop conditions
        if sold_today == True:
            print("Already sold today, stopping.")
            flag = False

        # Get the latest item
        ticker_item = get_latest_item(ticker, config)
        if len(ticker_item[ticker]) == 0:
            print('Skipping, no market items')
            print(ticker_item)
            return

        item = ticker_item[ticker][-1]

        # Check timestamp unique
        if item['t'] == last_timestamp:
            print('Skipping, non unique timestamp.')
            return
        else:
            last_timestamp = item['t']

        # Collect new data
        price = item['o']
        volume = item['v']
        if epoch == 0:
            velocity = 0
            volume_velocity = 0
        else:
            velocity = price/price_map[-1]
            volume_velocity = volume/volume_map[-1]
        price_map.append(price)
        volume_map.append(volume)
        velocity_map.append(velocity)
        volume_velocity_map.append(volume_velocity)

        # Check sell conditions
        if is_order_open:
            if velocity <= ticker_config['price_velocity_sell_threshold']:
                sell(price)
            elif volume_velocity <= ticker_config['volume_velocity_sell_threshold']:
                sell(price)

        # Check buy conditions
        if is_order_open == False:
            if velocity >= ticker_config['price_velocity_buy_threshold']:
                buy(price)
            elif volume_velocity >= ticker_config['volume_velocity_buy_threshold']:
                buy(price)

        # Iterate the epoch
        epoch += 1
        if epoch % ticker_config['epoch_interval'] == 0:
            epoch_velocity = price / \
                price_map[ticker_config['epoch_interval']*-1]
            velocity_epoch_map.append(epoch_velocity)

            # Check sell conditions
            if is_order_open:
                if epoch_velocity <= ticker_config['epoch_velocity_sell_threshold']:
                    sell(price)

            # Check buy conditions
            if is_order_open == False:
                if epoch_velocity >= ticker_config['epoch_velocity_buy_threshold']:
                    buy(price)

        # Sleep for 60 seconds
        time.sleep(60)


def get_latest_item(ticker, config):
    now = datetime.now() - timedelta(minutes=15)
    t = now.timetuple()
    y, m, d, h, mi, sec, wd, yd, i = t
    h = (h + 6) % 25
    params = {
        'symbols': [ticker],
        'start': f"{now.isoformat().split('T')[0]}T{h}:{mi}:00-00:00",
        'limit': 100
    }
    print(params)
    response = requests.get("https://data.alpaca.markets/v1/bars/minute",
                            params=params, headers=util.alpaca_headers())
    return response.json()


def get_starting_cash(config):
    response = requests.get(
        f"{config['api_root']}/v2/account", headers=util.alpaca_headers())
    data = response.json()
    return float(data['buying_power'])
