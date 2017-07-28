from __init__ import scheduler
from models import *
from datetime import datetime


def email(title, recipient, message):
	print(title + '\n To ' + recipient + ', \n' + message)

def create_email_jobs():
	email_notifications = EmailNotification.object.all()
	for notif in email_notifications:
		if notif.recipient.all() is not None:
			recipients = list(notif.recipient.all())
		if notif.template is not None:
			template = notif.template
			if not notif.is_sent and template.is_active:
				event = notif.event
				if event is not None:
					if template.date is None and template.time_before is not None:
						event_start = event.start_time
						send_time = event_start + notif.time_before
					elif template.date is not None:
						send_time = template.date
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
					elif event.internal_order is not None:
						for internal_user in list(UserData.object.filter(role='internal')):
							recipients.append(internal_user.user.email)
					elif event.external_order is not None:
						for external_user in list(UserData.object.filter(role='external')):
							recipients.append(external_user.user.email)
					else:
						if recipients is not None:
							if template.date is not None:
								send_time = template.date
							else:
								send_time = datetime.now()
							for recipient in recipients:
								if send_time > datetime.now():
									scheduler.add_job(email, 'date', run_date=send_time, kwargs={'title':template.title, 'recipient':recipient, 'message':template.message}, id=event.pk)
								elif send_time <= datetime.now():
									scheduler.add_job(email, kwargs={'title':template.title, 'recipient':recipient, 'message':template.message}, id=event.pk)
						else:
							print('Notification for non-cruise or -season event needs a pre-defined list of recipients')
					for recipient in recipients:
						if send_time > datetime.now():
							scheduler.add_job(email, 'date', run_date=send_time, kwargs={'title':template.title, 'recipient':recipient, 'message':template.message}, id=event.pk)
						elif send_time <= datetime.now():
							scheduler.add_job(email, kwargs={'title':template.title, 'recipient':recipient, 'message':template.message}, id=event.pk)
				else:
					if template.date is not None:
						send_time = template.date
					else:
						send_time = datetime.now()
					for recipient in list(:
						if send_time > datetime.now():
							scheduler.add_job(email, 'date', run_date=send_time, kwargs={'title':template.title, 'recipient':recipient, 'message':template.message})
						elif send_time <= datetime.now():
							scheduler.add_job(email, kwargs={'title':template.title, 'recipient':recipient, 'message':template.message})
					else:
						print('Eventless notification needs a pre-defined list of recipients')
		else:
			print('Notification has no template')

def create_single_email_job(template, recipients):
	
				
if __name__ == '__main__':
	