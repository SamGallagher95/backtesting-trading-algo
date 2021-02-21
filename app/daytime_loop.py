import time
from datetime import timedelta
from timeloop import Timeloop


def execute(ticker, ticker_config, config):
    tl = Timeloop()
    i = 0

    @tl.job(interval=timedelta(seconds=5))
    def tick():
        nonlocal i

        print(f'Tick at {time.ctime()}')

        i += 1
        if i > 10:
            tl.stop()

    tl.start()
