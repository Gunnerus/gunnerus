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

def admin_debug_view(request):
	if (request.user.is_superuser):
		debug_data = DebugData.objects.all()
		debug_data = debug_data[::-1]
		paginator = Paginator(debug_data, 5)
		page = request.GET.get('page')
		try:
			page_debug_data = paginator.page(page)
		except PageNotAnInteger:
			# If page is not an integer, deliver first page.
			page_debug_data = paginator.page(1)
		except EmptyPage:
			# If page is out of range (e.g. 9999), deliver last page of results.
			page_debug_data = paginator.page(paginator.num_pages)
	else:
		raise PermissionDenied

	return render(request, 'reserver/admin_debug.html', {'debug_data': page_debug_data})

class StringReprJSONEncoder(json.JSONEncoder):
	def default(self, o):
		try:
			return repr(o)
		except:
			return '[unserializable]'

@csrf_exempt
def log_debug_data(request):
	if request.user.is_authenticated():
		log_data = ""
		label = ""
		try:
			json_data = json.loads(request.body.decode("utf-8"))
			log_data = json_data["log_data"]
			label = json_data["label"]
		except:
			pass
		log = DebugData()
		log.data = log_data
		log.label = label + " from user " + str(request.user)
		log.timestamp = timezone.now()
		log.request_metadata = json.dumps(request.META, cls=StringReprJSONEncoder, ensure_ascii=True)
		log.save()
	else:
		raise PermissionDenied
	return JsonResponse(json.dumps([], ensure_ascii=True), safe=False)