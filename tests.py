from datetime import datetime, timedelta
import os
import json
import requests


def main():
    config = load_config()

    data = get_ticker(config['ticker'], config)
    output_to_csv(data[config['ticker']])


def output_to_csv(data):
    out = "Timestamp,Open,Close,Volume\n"
    i = 0
    for item in data:
        out += f"{i},{item['o']},{item['c']},{item['v']}\n"
        i += 1
    with open('out.csv', 'x') as f:
        f.write(out)


def get_ticker(ticker, config):
    after_date = datetime.now() - timedelta(days=config['historic_days'])
    params = {
        'symbols': ticker,
        'after': f"{after_date.isoformat().split('T')[0]}T00:00:00-00:00"
    }
    response = requests.get(
        f"{config['market_api_root']}/v1/bars/{config['bars_timeframe']}", headers=alpaca_headers(), params=params)
    return response.json()


def alpaca_headers():
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    return {
        'APCA-API-KEY-ID': api_key,
        'APCA-API-SECRET-KEY': secret_key
    }


def load_config():
    with open('config.json') as f:
        config_str = f.read()
    return json.loads(config_str)


main()
