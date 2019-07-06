from django.shortcuts import get_list_or_404, get_object_or_404, render, redirect
from django.db.models import Q
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.views.generic import ListView
from django.contrib.auth.decorators import login_required
from django.views.generic.detail import SingleObjectMixin
from django.contrib import messages
from django.utils.safestring import mark_safe
from reserver.utils import render_add_cal_button, account_activation_token
from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes
from django.utils import six
import os, tempfile, zipfile
from django.http import HttpResponse
from wsgiref.util import FileWrapper
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from easy_pdf.views import PDFTemplateView
from easy_pdf.rendering import html_to_pdf, make_response, render_to_pdf_response
from django.utils.decorators import method_decorator
from django import template
import pyqrcode
import io
import base64

from reserver.utils import check_for_and_fix_users_without_userdata, send_user_approval_email
from reserver.models import *
from reserver.forms import *
from reserver.test_models import create_test_models
from reserver import jobs
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail, get_connection

from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.template import loader
from django.utils import timezone
from reserver.utils import init, send_activation_email
import datetime
import json
from reserver.jobs import send_email, send_template_only_email
from django.conf import settings

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

	return render(request, 'reserver/admin_sent_emails.html', {'email_logs':email_logs})

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