from __init__ import scheduler
from models import *
from datetime import datetime


def email(title, recipient, message):
	print(title + '\n To ' + recipient + ', \n' + message)

def create_email_jobs():
	email_notifications = EmailNotification.object.all()
	for notif in email_notifications:
		template = notif.template
		if not notif.is_sent and template.is_active:
			event = notif.event
			if template.date is None and template.time_before is not None:
				event_start = event.start_time
				send_time = event_start + notif.time_before
			elif template.date is not None:
				send_time = notif.date
			else:
				send_time = event.start_time
			recipients = []
			if event.cruiseday is not None:
				cruise = event.cruiseday.cruise
				for owner in list(cruise.owner.all()):
					recipients.append(owner.email)
				for participant in list(cruise.participant.all()):
					recipients.append(participant.email)
				recipients.append(cruise.leader.email)
			if event.season is not None:
				
			for recipient in recipients:
				if send_time > datetime.now():
					scheduler.add_job(email, 'date', run_date=send_time, kwargs={'title':template.title, 'recipient':te)
				elif send_time <= datetime.now():
					pass