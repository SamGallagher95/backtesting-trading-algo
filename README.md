# Backtesting Trading Algorithm

Entrypoint to the app is `main.py`. The interesting code is in `app/backtest.py`.

## App Architecture

This is designed to start ~ an hour before the market opens, runs it's backtesting, and then waits for the market to open. Once the market opens, it grabs the price of the chosen ticker every minute and runs it through the buy/sell algorithm. Once it has sold for the day it will quit.

## Deployment Architecture

- This app is built as a Docker container and lives in my personal ECR registry.
- A Lambda function is setup on a CRON schedule with the schedule `0 7 * * 1-3`.
  - This function launches an EC2 instance based on a predefined launch template
- User Data on the EC2 instance installs `Docker`, pulls the above ECR image, and starts the app.
- The app runs and does it's stuff.
- When the app finishes, it invokes another Lambda function.
  - This function terminates the EC2 instance.
