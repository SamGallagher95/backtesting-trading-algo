aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 150297168177.dkr.ecr.us-east-1.amazonaws.com
docker build -t daytrader .
docker tag daytrader:latest 150297168177.dkr.ecr.us-east-1.amazonaws.com/daytrader:latest
docker push 150297168177.dkr.ecr.us-east-1.amazonaws.com/daytrader:latest