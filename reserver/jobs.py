from reserver.models import *
from datetime import datetime
from django.utils import timezone
from apscheduler.schedulers.background import BackgroundScheduler


def email(title, recipient, message, notif):
	print(title + '\nTo ' + recipient + ',\n' + message + '\n')
	#notif.is_sent = True
	#notif.save()
	pass

def create_email_jobs(scheduler):
	email_notifications = EmailNotification.objects.all()
	for notif in email_notifications:
		if notif.recipients.all() is not None:
			recipients = list(notif.recipients.all())
		if notif.template is not None:
			template = notif.template
			if not notif.is_sent and template.is_active:
				event = notif.event
				if event is not None:
					if template.date is None and template.time_before is not None:
						event_start = event.start_time
						send_time = event_start + template.time_before
					elif template.date is not None:
						send_time = template.date
					else:
						send_time = event.start_time
					try:
						event.cruiseday
						recipients = []
						cruise = event.cruiseday.cruise
						for owner in list(cruise.owner.all()):
							recipients.append(owner.email)
						for participant in list(cruise.participant_set.all()):
							recipients.append(participant.email)
						recipients.append(cruise.leader.email)
					except ObjectDoesNotExist:
						try:
							event.internal_order
							recipients = []
							for internal_user in list(UserData.objects.filter(role='internal')):
								recipients.append(internal_user.user.email)
						except ObjectDoesNotExist:
							try:
								event.external_order
								recipients = []
								for external_user in list(UserData.objects.filter(role='external')):
									recipients.append(external_user.user.email)
							except ObjectDoesNotExist:
								if recipients is not None:
									if template.date is not None:
										send_time = template.date
									else:
										send_time = timezone.now()
									for recipient in recipients:
										if send_time > timezone.now():
											scheduler.add_job(email, 'date', run_date=send_time, kwargs={'title':template.title, 'recipient':recipient.user.email, 'message':template.message, 'notif':notif})
										elif send_time <= timezone.now():
											scheduler.add_job(email, kwargs={'title':template.title, 'recipient':recipient.user.email, 'message':template.message, 'notif':notif})
								else:
									print('Notification for non-cruise or -season event needs a pre-defined list of recipients')
								continue
					for recipient in recipients:
						if send_time > timezone.now():
							scheduler.add_job(email, 'date', run_date=send_time, kwargs={'title':template.title, 'recipient':recipient, 'message':template.message, 'notif':notif})
						elif send_time <= timezone.now():
							scheduler.add_job(email, kwargs={'title':template.title, 'recipient':recipient, 'message':template.message, 'notif':notif})
				else:
					if template.date is not None:
						send_time = template.date
					else:
						send_time = timezone.now()
					if len(recipients) > 0:
						for recipient in recipients:
							if send_time > timezone.now():
								scheduler.add_job(email, 'date', run_date=send_time, kwargs={'title':template.title, 'recipient':recipient.user.email, 'message':template.message, 'notif':notif})
							elif send_time <= timezone.now():
								scheduler.add_job(email, kwargs={'title':template.title, 'recipient':recipient.user.email, 'message':template.message, 'notif':notif})
					else:
						print('Eventless notification needs a pre-defined list of recipients')
		else:
			print('Notification has no template')
			
def main():
	# Scheduler which executes methods at set times in the future, such as sending emails about upcoming cruises to the leader, owners and participants on certain deadlines
	scheduler = BackgroundScheduler()
	scheduler.start()
	create_email_jobs(scheduler)
	scheduler.print_jobs()