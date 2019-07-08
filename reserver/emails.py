from smtplib import SMTPException

from django.core.mail import send_mail, get_connection
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes
from django.utils import six
from django.contrib import messages

from reserver.models import UserData, Participant, EmailTemplate

def email(notif):
	template = notif.template
	event = notif.event
	# Use category to determine which email methods to run
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
	elif notif.template.group == 'Admin deadline notice':
		admin_deadline_notice_email(notif)
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
		send_email(recipients, notif.template.message, notif, share_recipient_emails=False)
	elif notif.event.is_external_order():
		recipients = []
		for user in UserData.objects.filter(role='external'):
			recipients.append(user.user.email)
		# remove duplicates
		recipients = list(set(recipients))
		send_email(recipients, notif.template.message, notif, share_recipient_emails=False)

def admin_deadline_notice_email(notif):
	recipients = []
	for user in UserData.objects.filter(role='admin'):
		recipients.append(user.user.email)
	# remove duplicates
	recipients = list(set(recipients))
	send_email(recipients, notif.template.message, notif, share_recipient_emails=True)

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
	send_email(recipients, notif.template.message, notif, share_recipient_emails=True)

def cruise_departure_email(notif):
	recipients = []
	if notif.event.is_cruise_day():
		cruise = notif.event.cruiseday.cruise
	else:
		return False
	recipients.append(cruise.leader.email)
	for owner in cruise.owner.all():
		recipients.append(owner.email)
	for participant in Participant.objects.select_related().filter(cruise=cruise.pk):
		recipients.append(participant.email)
	# remove duplicates
	recipients = list(set(recipients))
	send_email(recipients, notif.template.message, notif, share_recipient_emails=True)

def other_email(notif):
	recipients = notif.recipient_set.all()
	# remove duplicates
	recipients = list(set(recipients))
	send_email(recipients, notif.template.message, notif, share_recipient_emails=False)

def send_email(recipients, message, notif, **kwargs):
	# file path is set in settings.py as EMAIL_FILE_PATH
	file_backend = get_connection('django.core.mail.backends.filebased.EmailBackend')
	smtp_backend = get_connection(settings.EMAIL_BACKEND)
	template = EmailTemplate()
	subject = "Cruise reservation system notification"

	try:
		if notif.is_sent:
			return
	except:
		pass

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
				subject = 'Cruise administration notification'
			elif notif.template.group == 'Cruise departure':
				subject = 'Cruise departure notification'
			elif notif.template.group == 'Cruise deadline':
				subject = notif.template.title
				# check if deadline mail should be sent
				if len(event.cruiseday.cruise.get_missing_information_list()) == 0:
					return
			elif notif.template.group == 'Admin deadline notice':
				subject = 'Admin deadline notice'
				# check if deadline mail should be sent
				if len(event.cruiseday.cruise.get_missing_information_list()) == 0:
					return
			elif notif.template.group == 'Admin notices':
				subject = 'Admin notification'
			elif notif.template.group == 'User administration':
				subject = 'User administration notification'
			elif notif.template.group == 'Season':
				subject = 'Season opening notification'
			elif category == 'Other':
				subject = 'Notification'
	except:
		pass

	try:
		if notif.extra_message:
			extra_message = notif.extra_message
		else:
			extra_message = ""
	except:
		extra_message = ""

	cruise_name = ""

	try:
		if notif.event.is_cruise_day():
			subject_event = str(notif.event.cruiseday.cruise)
			cruise_name = str(notif.event.cruiseday.cruise)
		else:
			subject_event = str(notif.event.name)
	except AttributeError:
		try:
			subject_event = notif.template.title
		except AttributeError:
			subject_event = 'unknown event'

	season_name = ""

	try:
		try:
			if notif.event.season != None:
				season_name = notif.event.season.name
		except ObjectDoesNotExist:
			pass
		try:
			if notif.event.external_order != None:
				season_name = notif.event.external_order.name
		except ObjectDoesNotExist:
			pass
		try:
			if notif.event.internal_order != None:
				season_name = notif.event.internal_order.name
		except ObjectDoesNotExist:
			pass
	except (AttributeError, ObjectDoesNotExist):
		season_name = 'unknown season'

	user = ''
	cruise = ''
	if kwargs.get("user"):
		user = kwargs["user"]
	if kwargs.get("cruise"):
		cruise = kwargs["cruise"]

	context = {
		"subject_event": subject_event,
		"cruise_name": cruise_name,
		"season_name": season_name,
		"extra_message": extra_message,
		"user": user,
		"cruise": cruise
	}

	if kwargs.get("subject"):
		subject = kwargs["subject"]

	share_recipient_emails = False
	if kwargs.get("share_recipient_emails"):
		share_recipient_emails = kwargs["share_recipient_emails"]

	if isinstance(recipients, str):
		# recipients needs to be a list even if we just have one recipient
		recipients = [recipients]

	if share_recipient_emails:
		send_mail(
			subject,
			strip_tags(template.render_message_body(context)),
			settings.DEFAULT_FROM_EMAIL,
			recipients,
			fail_silently=True,
			connection=file_backend,
			html_message=template.render(context)
		)

		try:
			send_mail(
				subject,
				strip_tags(template.render_message_body(context)),
				settings.DEFAULT_FROM_EMAIL,
				recipients,
				fail_silently=False,
				connection=smtp_backend,
				html_message=template.render(context)
			)
			if not notif.is_sent:
				notif.is_sent = True
				notif.save()
		except SMTPException as e:
			print('There was an error sending an email: ', e)
	else:
		for recipient in recipients:
			send_mail(
				subject,
				strip_tags(template.render_message_body(context)),
				settings.DEFAULT_FROM_EMAIL,
				[recipient],
				fail_silently=True,
				connection=file_backend,
				html_message=template.render(context)
			)

			try:
				send_mail(
					subject,
					strip_tags(template.render_message_body(context)),
					settings.DEFAULT_FROM_EMAIL,
					[recipient],
					fail_silently=False,
					connection=smtp_backend,
					html_message=template.render(context)
				)
				if not notif.is_sent:
					notif.is_sent = True
					notif.save()
			except SMTPException as e:
				print('There was an error sending an email: ', e)

def send_template_only_email(recipients, template, **kwargs):
	# file path is set in settings.py as EMAIL_FILE_PATH
	file_backend = get_connection('django.core.mail.backends.filebased.EmailBackend')
	smtp_backend = get_connection(settings.EMAIL_BACKEND)
	subject = "Cruise reservation system notification"

	try:
		if template.group == 'Cruise administration':
			subject = 'Cruise administration notification'
		elif template.group == 'Cruise departure':
			subject = 'Cruise departure notification'
		elif template.group == 'Admin notices':
			subject = 'Admin notification'
		elif template.group == 'User administration':
			subject = 'User administration notification'
	except:
		pass

	user = ''
	cruise = ''
	invoice = ''

	if kwargs.get("user"):
		user = kwargs["user"]
	if kwargs.get("cruise"):
		cruise = kwargs["cruise"]
	if kwargs.get("invoice"):
		invoice = kwargs["invoice"]

	context = {
		"user": user,
		"cruise": cruise,
		"invoice": invoice
	}

	if kwargs.get("subject"):
		subject = kwargs["subject"]

	if isinstance(recipients, str):
		# recipients needs to be a list even if we just have one recipient
		recipients = [recipients]

	send_mail(
		subject,
		strip_tags(template.render_message_body(context)),
		settings.DEFAULT_FROM_EMAIL,
		recipients,
		fail_silently=True,
		connection=file_backend,
		html_message=template.render(context)
	)

	try:
		send_mail(
			subject,
			strip_tags(template.render_message_body(context)),
			settings.DEFAULT_FROM_EMAIL,
			recipients,
			fail_silently=False,
			connection=smtp_backend,
			html_message=template.render(context)
		)
	except SMTPException as e:
		print('There was an error sending an email: ', e)

# Special email functions used for user activation

class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
	def _make_hash_value(self, user, timestamp):
		return (
			six.text_type(user.pk) + six.text_type(timestamp)
		)

account_activation_token = AccountActivationTokenGenerator()

def send_activation_email(request, user):
	from django.conf import settings
	from django.contrib.auth.models import User
	from reserver.models import UserData, EmailTemplate
	file_backend = get_connection('django.core.mail.backends.filebased.EmailBackend')
	smtp_backend = get_connection(settings.EMAIL_BACKEND)

	user.userdata.email_confirmed = False
	user.userdata.save()
	current_site = get_current_site(request)
	template = EmailTemplate.objects.get(title="Confirm email address")
	subject = template.title
	context = {
		'user': user,
		'domain': current_site.domain,
		'uid': urlsafe_base64_encode(force_bytes(user.pk)),
		'token': account_activation_token.make_token(user),
	}
	message = template.render_message_body(context)

	send_mail(
		subject,
		message,
		settings.DEFAULT_FROM_EMAIL,
		[user.email],
		fail_silently=False,
		connection=file_backend,
		html_message=template.render(context)
	)

	try:
		send_mail(
			subject,
			message,
			settings.DEFAULT_FROM_EMAIL,
			[user.email],
			fail_silently=False,
			connection=smtp_backend,
			html_message=template.render(context)
		)
	except SMTPException as e:
		print('There was an error sending an email: ', e)

	messages.add_message(request, messages.INFO, 'Email confirmation link sent to %s.' % str(user.email))

def send_user_approval_email(request, user):
	from django.conf import settings
	from django.contrib.auth.models import User
	from reserver.models import EmailTemplate
	current_site = get_current_site(request)
	template = EmailTemplate.objects.get(title="Account approved")
	subject = template.title
	context = {
		'user': user,
	}
	message = template.render_message_body(context)
	send_mail(
		subject,
		message,
		settings.DEFAULT_FROM_EMAIL,
		[user.email],
		fail_silently = False,
		html_message = template.render(context)
	)