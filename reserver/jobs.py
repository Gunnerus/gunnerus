from reserver.models import *
from datetime import datetime, timedelta, date
from django.utils import timezone
from apscheduler.schedulers.background import BackgroundScheduler
from django.core.mail import send_mail, get_connection
from django.core.exceptions import ObjectDoesNotExist
from smtplib import SMTPException
from django.conf import settings
from django.db import transaction
from django.utils.html import strip_tags
from reserver.emails import email

job_defaults = {
	'coalesce': False,
	'max_instances': 1
}

scheduler = BackgroundScheduler(timezone='Europe/Oslo', job_defaults=job_defaults) #Chooses the basic scheduler which runs in the background

def main():
	# Scheduler which executes methods at set times in the future, such as 
	# sending emails about upcoming cruises to the leader, owners and participants on certain deadlines
	global scheduler
	scheduler.start() #Starts the scheduler, which then can run scheduled jobs
	create_jobs(scheduler)
	scheduler.print_jobs()

def daily_0800():
	""" runs once daily at 0800 - daily status mails, etc. """
	create_jobs(scheduler)

def daily_0000():
	""" runs once daily at 0000 - daily statistic logging, etc. """
	collect_statistics()

def collect_statistics():
	statistics = Statistics()
	statistics.timestamp = timezone.now()
	statistics.event_count = Event.objects.all().count()
	statistics.cruise_count = Cruise.objects.all().count()
	statistics.approved_cruise_count = Cruise.objects.filter(is_approved=True).count()
	statistics.cruise_day_count = CruiseDay.objects.all().count()
	statistics.approved_cruise_day_count = CruiseDay.objects.filter(cruise__is_approved=True).count()
	statistics.user_count = User.objects.all().count()
	statistics.emailconfirmed_user_count = UserData.objects.filter(email_confirmed=True).count()
	statistics.organization_count = Organization.objects.all().count()
	statistics.email_notification_count = EmailNotification.objects.all().count()
	statistics.save()
	return statistics

@transaction.atomic
def create_jobs(scheduler, notifs=None): 
	""" Creates jobs for given email notifications, or for all existing notifications if none given. """
	# offset to avoid scheduling jobs at the same time as executing them
	offset = 0
	print("Creating jobs")
	if notifs is None:
		email_notifications = EmailNotification.objects.all()
		for job in scheduler.get_jobs():
			job.remove()
		scheduler.add_job(daily_0800, trigger='cron', day='*', hour=8)
		scheduler.add_job(daily_0000, trigger='cron', day='*', hour=0)
	else:
		email_notifications = notifs
	for notif in email_notifications:
		send_time = notif.get_send_time()
		if not notif.is_sent:
			try:
				if send_time <= timezone.now():
					print('New job')
					scheduler.add_job(email, kwargs={'notif':notif})
					scheduler.print_jobs()
				elif timezone.now() + timedelta(hours=offset) < send_time <= timezone.now() + timedelta(days=1, hours=offset):
					print('New job')
					scheduler.add_job(email, trigger='date', run_date=send_time, kwargs={'notif':notif})
					scheduler.print_jobs()
			except:
				print("Unable to send: "+str(notif))