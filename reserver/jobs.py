from reserver.models import *
from datetime import datetime
from django.utils import timezone
from apscheduler.schedulers.background import BackgroundScheduler


scheduler = BackgroundScheduler() #Chooses the basic scheduler which runs in the background

def create_jobs(scheduler, notifs=None): #Creates jobs for given email notifications, or for all existing notifications if none given
	if notifs is None:
		email_notifications = EmailNotification.objects.all()
	else:
		email_notifications = notifs
	for notif in email_notifications:
		send_time = notif.get_send_time()
		if send_time <= timezone.now():
			print('New job')
			scheduler.add_job(email, kwargs={'notif':notif})
			scheduler.print_jobs()
		else:
			print('New job')
			scheduler.add_job(email, 'date', run_date=send_time, kwargs={'notif':notif})
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
	for owner in cruise.owner_set.all():
		recipients.append(owner.email)
	for recipient in recipients:
		send_email(recipient, message, notif)
	
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
	notif.is_sent = True
	notif.save()
	pass

#This method creates jobs to put into the scheduler from all existing EmailNotification objects
def create_email_jobs(scheduler):
	email_notifications = EmailNotification.objects.all()
	#Goes through every notification object
	for notif in email_notifications:
		#Sets recipients list if the notification object has a pre-defined list of recipients
		if notif.recipients.all() is not None:
			recipients = list(notif.recipients.all())
		#Checks if the notification has a template, ignores notifications without templates
		if notif.template is not None:
			template = notif.template
			#Only makes jobs of active notifications that have not been sent
			if not notif.is_sent and template.is_active:
				event = notif.event
				#Checks if the notification has an event
				if event is not None:
					#Sets the send time of the job, only chooses time_before if there is no  date. 
					if template.date is None and template.time_before is not None:
						event_start = event.start_time
						send_time = event_start + template.time_before
					elif template.date is not None:
						send_time = template.date
					#Chooses the event's start_time if there is neither a date or time_before
					else:
						send_time = event.start_time
					#Determines if the event is related to a cruiseday or season
					try:
						event.cruiseday
						recipients = []
						cruise = event.cruiseday.cruise
						#Fills recipient list with all emails related to the cruise (leader, owners and participants)
						for owner in list(cruise.owner.all()):
							recipients.append(owner.email)
						for participant in list(cruise.participant_set.all()):
							recipients.append(participant.email)
						recipients.append(cruise.leader.email)
					except ObjectDoesNotExist:
						try:
							event.internal_order
							recipients = []
							#Recipients are all internal users (possibly add all admins too?)
							for internal_user in list(UserData.objects.filter(role='internal')):
								recipients.append(internal_user.user.email)
						except ObjectDoesNotExist:
							try:
								event.external_order
								recipients = []
								#Recipients are all external users (possibly add all admins too?)
								for external_user in list(UserData.objects.filter(role='external')):
									recipients.append(external_user.user.email)
							except ObjectDoesNotExist:
								#If the event is related to neither cruises or seasons, pre-defined recipient list is used
								if recipients is not None:
									#Makes a job for every recipient and adds it to the scheduler
									for recipient in recipients:
										#If the send_time has passed already, the job receives no date. The scheduler then immediately runs the email method
										if send_time > timezone.now():
											scheduler.add_job(email, 'date', run_date=send_time, kwargs={'title':template.title, 'recipient':recipient.user.email, 'message':template.message, 'notif':notif})
										elif send_time <= timezone.now():
											scheduler.add_job(email, kwargs={'title':template.title, 'recipient':recipient.user.email, 'message':template.message, 'notif':notif})
								else:
									print('Notification for non-cruise or -season event needs a pre-defined list of recipients')
								continue
					#Recipients added from cruise or season are put into jobs
					for recipient in recipients:
						if send_time > timezone.now():
							scheduler.add_job(email, 'date', run_date=send_time, kwargs={'title':template.title, 'recipient':recipient, 'message':template.message, 'notif':notif})
						elif send_time <= timezone.now():
							scheduler.add_job(email, kwargs={'title':template.title, 'recipient':recipient, 'message':template.message, 'notif':notif})
				#The pre-defined recipient list is also used if the notification has no event
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
	#Scheduler which executes methods at set times in the future, such as sending emails about upcoming cruises to the leader, owners and participants on certain deadlines
	global scheduler
	scheduler.start() #Starts the scheduler, which then can run scheduled jobs
	create_jobs(scheduler)
	scheduler.print_jobs()