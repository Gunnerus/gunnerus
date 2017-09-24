from reserver.models import *
from datetime import datetime, timedelta, date
from django.utils import timezone
from apscheduler.schedulers.background import BackgroundScheduler
from django.core.mail import send_mail, get_connection
from django.conf import settings

job_defaults = {
    'coalesce': False,
    'max_instances': 1
}

scheduler = BackgroundScheduler(timezone='Europe/Oslo', job_defaults=job_defaults) #Chooses the basic scheduler which runs in the background

def create_jobs(scheduler, notifs=None): #Creates jobs for given email notifications, or for all existing notifications if none given
	#offset to avoid scheduling jobs at the same time as executing them
	offset = 0
	print("Creating jobs")
	if notifs is None:
		print("notifs empty")
		email_notifications = EmailNotification.objects.all()
		for job in scheduler.get_jobs():
			job.remove()
		scheduler.add_job(create_jobs, args={scheduler}, trigger='cron', day='*', hour=8)
	else:
		print("notifs "+str(notifs))
		email_notifications = notifs
	for notif in email_notifications:
		print(notif)
		send_time = notif.get_send_time()
		print(send_time)
		if not notif.is_sent:
			if send_time <= timezone.now():
				print('New job')
				scheduler.add_job(email, kwargs={'notif':notif})
				scheduler.print_jobs()
			elif timezone.now() + timedelta(hours=offset) < send_time <= timezone.now() + timedelta(days=1, hours=offset):
				print('New job')
				scheduler.add_job(email, trigger='date', run_date=send_time, kwargs={'notif':notif})
				scheduler.print_jobs()
				
def restart_scheduler():
	pass
	#create_jobs(scheduler)
	#print("removing now-dead jobs")
	#scheduled_jobs = scheduler.get_jobs()
	#for job in scheduler.get_jobs():
	#	job.remove()
	#create_jobs(scheduler)
	#scheduler.add_job(create_jobs, args={scheduler}, trigger='cron', day='*', hour=8)

def email(notif):
	template = notif.template
	event = notif.event
	#Use category to determine which email methods to run
	if event is not None:
		print(event)
		try:
			category = event.category.name
		except:
			pass
	print(notif.template.group)
	if notif.template.group == 'Cruise administration' or notif.template.group == 'Cruise deadlines':
		cruise_administration_email(notif)
	elif notif.template.group == 'Cruise departure':
		cruise_departure_email(notif)
	elif notif.template.group == 'Season':
		season_email(notif)
	elif notif.template.group == 'Other':
		other_email(notif)
	else:
		print("Unable to determine email category")

def season_email(notif):
	if notif.event.is_internal_order():
		recipients = []
		for user in UserData.objects.filter(role='internal'):
			recipients.append(user.user.email)
		# remove duplicates
		recipients = list(set(recipients))
		for recipient in recipients:
			send_email(recipient, notif.template.message, notif)
	elif notif.event.is_external_order():
		recipients = []
		for user in UserData.objects.filter(role='external'):
			recipients.append(user.user.email)
		# remove duplicates
		recipients = list(set(recipients))
		for recipient in recipients:
			send_email(recipient, notif.template.message, notif)
		
def cruise_administration_email(notif):
	recipients = []
	if notif.event.is_cruise_day():
		cruise = notif.event.cruiseday.cruise
	else:
		return False
	recipients.append(cruise.leader.email)
	for owner in cruise.owner.all():
		recipients.append(owner.email)
	# remove duplicates
	recipients = list(set(recipients))
	for recipient in recipients:
		send_email(recipient, notif.template.message, notif)
	
def cruise_departure_email(notif):
	recipients = []
	print("Cruise departure email")
	if notif.event.is_cruise_day():
		cruise = notif.event.cruiseday.cruise
	else:
		return False
	recipients.append(cruise.leader.email)
	for owner in cruise.owner.all():
		recipients.append(owner.email)
	for participant in Participant.objects.select_related().filter(cruise=cruise.pk):
		recipient.append(participant.email)
	# remove duplicates
	recipients = list(set(recipients))
	for recipient in recipients:
		send_email(recipient, notif.template.message, notif)
	
def other_email(notif):
	recipients = notif.recipient_set.all()
	# remove duplicates
	recipients = list(set(recipients))
	for recipient in recipients:
		send_email(recipient.email, notif.template.message, notif)

def send_email(recipient, message, notif, **kwargs):
	print('To ' + recipient + ',\n' + message + '\n')
	# file path is set in settings.py as EMAIL_FILE_PATH
	file_backend = get_connection('django.core.mail.backends.filebased.EmailBackend')
	smtp_backend = get_connection(settings.EMAIL_BACKEND)
	template = EmailTemplate()
	subject = "Cruise reservation system notification"
	
	try:
		if notif.template:
			template = notif.template
			event = notif.event
			if event is not None:
				try:
					category = event.category.name
				except:
					pass
			if notif.template.group == 'Cruise administration':
				subject = 'Cruise adminstration notification'
			elif notif.template.group == 'Cruise departure':
				subject = 'Cruise departure notification'
			elif category == 'Season':
				subject = 'Season opening notification'
			elif category == 'Other':
				subject = 'Notification'
	except:
		pass
		
	try:
		if notif.event.is_cruise_day():
			subject_event = str(notif.event.cruiseday.cruise)
		else:
			subject_event = str(notif.event.name)
	except AttributeError:
		try:
			subject_event = notif.template.title
		except AttributeError:
			subject_event = 'unknown event'
			
	context = {
		"subject_event": subject_event,
	}
		
	if kwargs.get("subject"):
		subject = kwargs["subject"]
		
	send_mail(
		subject,
		message,
		'no-reply@reserver.471.no',
		[recipient],
		fail_silently=False,
		connection=file_backend,
		html_message=template.render(context)
	)
	print("actually sent a mail")
	send_mail(
		subject,
		message,
		'no-reply@reserver.471.no',
		[recipient],
		fail_silently=False,
		connection=smtp_backend,
		html_message=template.render(context)
	)
	notif.is_sent = True
	notif.save()
		
def main():
	#Scheduler which executes methods at set times in the future, such as sending emails about upcoming cruises to the leader, owners and participants on certain deadlines
	global scheduler
	#Set all notifications.is_active to False to avoid duplicates in the scheduler
	scheduler.start() #Starts the scheduler, which then can run scheduled jobs
	create_jobs(scheduler)
	scheduler.add_job(create_jobs, args={scheduler}, trigger='cron', day='*', hour=8)
	scheduler.print_jobs()