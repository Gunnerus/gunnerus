from .aps_test import scheduler
from datetime import datetime

def send_email(message):
	print(message)

scheduler.start()

scheduler.add_job(send_email, 'date', run_date=datetime(2017, 7, 26, 19, 40), kwargs={'message':'Hello, I\'m Mr. Meeseeks'})