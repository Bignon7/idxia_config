python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 feature_aggregator.py --log ../demo-webapp/login_attempts.log