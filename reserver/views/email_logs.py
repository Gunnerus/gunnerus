from django.shortcuts import render
from django.urls import reverse_lazy
from django.conf import settings
from django.http import HttpResponseRedirect
import re

from reserver.jobs import send_email
from reserver.models import EmailNotification

def view_email_logs(request):
	import os.path
	email_logs = []
	email_log_files = os.listdir(settings.EMAIL_FILE_PATH)
	email_log_files.sort()
	for filename in email_log_files:
		data = ""
		subject = ""
		recipients = ""
		with open(os.path.join(settings.EMAIL_FILE_PATH, filename), 'r') as email_log:
			data=email_log.read()
			try:
				subject = re.findall('Subject: ((?:.|\n )*)', data)
			except AttributeError:
				pass
			try:
				recipients = re.findall('To: ((?:.|\n )*)', data)
			except AttributeError:
				pass
		email_logs.append({
			"title": filename,
			"subject": subject,
			"recipients": recipients,
			"url": "/uploads/debug-emails/"+filename
		})
	email_logs.reverse()

	return render(request, 'reserver/admin/admin_sent_emails.html', {'email_logs':email_logs})

def test_email_view(request):
	send_email('test@test.no', 'a message', EmailNotification())
	return HttpResponseRedirect(reverse_lazy('email_list_view'))

def purge_email_logs(request):
	import os
	import glob

	files = glob.glob(settings.EMAIL_FILE_PATH+'*')
	for file in files:
		if ".log" in file and "debug-emails" in file:
			os.remove(file)

	return HttpResponseRedirect(reverse_lazy('email_list_view'))
