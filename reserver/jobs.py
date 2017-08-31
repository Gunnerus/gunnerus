from reserver.models import *
from datetime import datetime, timedelta
from django.utils import timezone
from apscheduler.schedulers.background import BackgroundScheduler


scheduler = BackgroundScheduler() #Chooses the basic scheduler which runs in the background

def create_jobs(scheduler, notifs=None): #Creates jobs for given email notifications, or for all existing notifications if none given
	#offset to avoid scheduling jobs at the same time as executing them
	offset = 0
	if notifs is None:
		email_notifications = EmailNotification.objects.all()
	else:
		email_notifications = notifs
	for notif in email_notifications:
		send_time = notif.get_send_time()
		if not notif.is_sent and not notif.is_active:
			if send_time <= timezone.now():
				print('New job')
				scheduler.add_job(email, kwargs={'notif':notif})
				notif.is_active = False
				notif.save()
				scheduler.print_jobs()
			elif timezone.now() + timedelta(hours=offset) < send_time <= timezone.now() + timedelta(days=1, hours=offset):
				print('New job')
				scheduler.add_job(email, 'date', run_date=send_time, kwargs={'notif':notif})
				notif.is_active = False
				notif.save()
				scheduler.print_jobs()

def email(notif):
	template = notif.template
	event = notif.event
	#Use category to determine which email methods to run
	if event is not None:
		category = event.category.name
	if category == 'Cruise day':
		if notif.template.group == 'Cruise administration':
			cruise_administration_email(notif)
		elif notif.template.group == 'Cruise departure':
			cruise_departure_email(notif)
	elif category == 'Season':
		season_email(notif)
	elif category == 'Other':
		pass

def season_email(notif):
	if notif.event.is_internal_order():
		recipients = UserData.objects.filter(role='internal')
		for recipient in recipients:
			email(recipient, message, notif)
	elif notif.event.is_external_order():
		recipients = UserData.objects.filter(role='external')
		for recipient in recipients:
			send_email(recipient, message, notif)
		
def cruise_administration_email(notif):
	recipients = []
	if notif.event.is_cruise_day():
		cruise = notif.event.cruiseday.cruise
	else:
		return False
	recipients.append(cruise.leader.email)
	for owner in cruise.owner.all():
		recipients.append(owner.email)
	for recipient in recipients:
		send_email(recipient, notif.template.message, notif)
	
def cruise_departure_email(notif):
	recipients = []
	if notif.event.is_cruise_day():
		cruise = notif.event.cruiseday.cruise
	else:
		return False
	recipients.append(cruise.leader)
	for owner in cruise.owner_set.all():
		recipients.append(owner.email)
	for participant in cruise.participant_set.all():
		recipient.append(participant.email)
	for recipient in recipients:
		send_email(recipient, message, notif)
	
def other_email(notif):
	recipients = notif.recipient_set.all()
	for recipient in recipients:
		send_email(recipient.email, message, notif)

def send_email(recipient, message, notif):
	print('To ' + recipient + ',\n' + message + '\n')
	#notif.is_sent = True
	notif.save()
	pass
		
def main():
	#Scheduler which executes methods at set times in the future, such as sending emails about upcoming cruises to the leader, owners and participants on certain deadlines
	global scheduler
	#Set all notifications.is_active to False to avoid duplicates in the scheduler
	for notif in EmailNotification.objects.filter(is_active=True):
		notif.is_active=False
		notif.save()
	scheduler.start() #Starts the scheduler, which then can run scheduled jobs
	create_jobs(scheduler)
	scheduler.print_jobs()