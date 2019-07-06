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

class CreateStandaloneInvoice(CreateView):
	model = InvoiceInformation
	template_name = 'reserver/invoice_standalone_create_form.html'
	form_class = StandaloneInvoiceInformationForm

	def get_success_url(self):
		return reverse_lazy('invoices-search')

	def form_valid(self, form):
		invoice = form.save(commit=False)
		invoice.is_cruise_invoice = False
		invoice.save()
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "created standalone invoice"
		action.save()
		return HttpResponseRedirect(self.get_success_url())

def create_additional_cruise_invoice(request, pk):
	if request.user.is_superuser:
		cruise = get_object_or_404(Cruise, pk=pk)
		invoice = cruise.get_invoice_info()
		if not invoice:
			invoice = InvoiceInformation()
		invoice.pk = None
		invoice.is_cruise_invoice = False
		invoice.title = 'Invoice for ' + str(cruise)
		invoice.is_finalized = False
		invoice.is_sent = False
		invoice.is_paid = False
		invoice.paid_date = None
		invoice.save()
		action = Action(user=request.user, timestamp=timezone.now(), target=str(cruise))
		action.action = "added an additional invoice to the cruise"
		action.save()
		Cruise.objects.filter(leader=request.user).update(missing_information_cache_outdated=True)
		messages.add_message(request, messages.SUCCESS, mark_safe('Additional invoice created.'))
	else:
		raise PermissionDenied
	try:
		return redirect(request.META['HTTP_REFERER'])
	except KeyError:
		return reverse_lazy('admin_invoices')


class EditStandaloneInvoice(UpdateView):
	model = InvoiceInformation
	template_name = 'reserver/invoice_standalone_edit_form.html'
	form_class = StandaloneInvoiceInformationForm

	def get_success_url(self):
		return reverse_lazy('admin-invoices')

	def form_valid(self, form):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=form.instance)
		action.action = "updated invoice " + str(form.instance)
		action.save()
		return super(EditStandaloneInvoice, self).form_valid(form)

class CreateListPrice(CreateView):
	model = ListPrice
	template_name = 'reserver/listprice_create_form.html'
	form_class = ListPriceForm

	def get_success_url(self):
		if self.object.invoice.cruise:
			return reverse_lazy('cruise-invoices', kwargs={'pk': self.object.invoice.cruise.pk})
		return reverse_lazy('admin-invoices')

	def form_valid(self, form):
		form.instance.invoice = InvoiceInformation.objects.get(pk=self.kwargs['pk'])
		action = Action(user=self.request.user, timestamp=timezone.now(), target=form.instance.invoice)
		action.action = "added list price " + str(form.instance) + " (" + str(form.instance.price) + " NOK)"
		action.save()
		return super(CreateListPrice, self).form_valid(form)

class UpdateListPrice(UpdateView):
	model = ListPrice
	template_name = 'reserver/listprice_edit_form.html'
	form_class = ListPriceForm

	def get_success_url(self):
		if self.object.invoice.cruise:
			return reverse_lazy('cruise-invoices', kwargs={'pk': self.object.invoice.cruise.pk})
		return reverse_lazy('admin-invoices')

	def form_valid(self, form):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=form.instance.invoice)
		action.action = "updated list price " + str(form.instance) + " (" + str(form.instance.price) + " NOK)"
		action.save()
		return super(UpdateListPrice, self).form_valid(form)

class DeleteListPrice(DeleteView):
	model = ListPrice
	template_name = 'reserver/listprice_delete_form.html'

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=self.object.invoice)
		action.action = "deleted list price " + str(self.object) + " (" + str(self.object.price) + " NOK)"
		action.save()
		if self.object.invoice.cruise:
			return reverse_lazy('cruise-invoices', kwargs={'pk': self.object.invoice.cruise.pk})
		return reverse_lazy('admin-invoices')

def view_cruise_invoices(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if (request.user.pk == cruise.leader.pk or request.user in cruise.owner.all() or request.user.is_superuser):
		invoices = InvoiceInformation.objects.filter(cruise=pk)
	else:
		raise PermissionDenied
	return render(request, 'reserver/cruise_invoices.html', {'cruise': cruise, 'invoices': invoices})

def admin_invoice_view(request):
	if (request.user.is_superuser):
		unfinalized_invoices = InvoiceInformation.objects.filter(is_finalized=False, cruise__is_approved=True, cruise__cruise_end__lte=timezone.now())
		unpaid_invoices = InvoiceInformation.objects.filter(is_finalized=True, is_paid=False, cruise__is_approved=True, cruise__cruise_end__lte=timezone.now())
		unfinalized_invoices |= InvoiceInformation.objects.filter(cruise__isnull=True, is_finalized=False, is_paid=False)
		unpaid_invoices |= InvoiceInformation.objects.filter(cruise__isnull=True, is_finalized=True, is_paid=False)
	else:
		raise PermissionDenied

	return render(request, 'reserver/admin_invoices.html', {'unfinalized_invoices': unfinalized_invoices, 'unpaid_invoices': unpaid_invoices})

def invoicer_overview(request):
	if (request.user.userdata.role == "invoicer"):
		unsent_invoices = InvoiceInformation.objects.filter(is_finalized=True, is_sent=False, is_paid=False)
		unpaid_invoices = InvoiceInformation.objects.filter(is_finalized=True, is_sent=True, is_paid=False)
	else:
		raise PermissionDenied

	return render(request, 'reserver/invoicer_overview.html', {'unsent_invoices': unsent_invoices, 'unpaid_invoices': unpaid_invoices})

class InvoiceDeleteView(DeleteView):
	model = InvoiceInformation
	template_name = 'reserver/invoice_delete_form.html'

	def get_success_url(self):
		try:
			return reverse('cruise-invoices', args=(self.object.cruise.pk, ))
		except:
			return reverse_lazy('admin-invoices')

def invoice_history(request, **kwargs):
	template = "reserver/invoicer_invoice_history.html"
	if (request.user.is_superuser or request.user.userdata.role == "invoicer"):
		if request.user.is_superuser:
			template = "reserver/admin_invoice_history.html"
		has_dates_selected = False
		start_date_string = ""
		end_date_string = ""
		cruise_leaders = []
		expected_cruise_leaders = []
		invoice_sum = 0
		unsent_invoice_sum = 0
		expected_invoice_sum = 0
		expected_unsent_invoice_sum = 0
		invoices = []
		expected_invoices = []
		cruises = []
		expected_cruises = []
		cruise_names = []
		expected_cruise_names = []
		seasons = Season.objects.all()
		years = []
		expected_unpaid_invoices = []

		research_count = 0
		education_count = 0
		boa_count = 0
		external_count = 0
		short_day_count = 0
		long_day_count = 0

		expected_research_count = 0
		expected_education_count = 0
		expected_boa_count = 0
		expected_external_count = 0
		expected_short_day_count = 0
		expected_long_day_count = 0

		for season in seasons:
			years.append(season.season_event.start_time.strftime("%Y"))
			years.append(season.season_event.end_time.strftime("%Y"))

		years = reversed(sorted(list(set(years))))

		if kwargs.get("start_date") and kwargs.get("end_date"):
			has_dates_selected = True
			start_date_string = kwargs.get("start_date")
			end_date_string = kwargs.get("end_date")

			start_date = timezone.make_aware(datetime.datetime.strptime(start_date_string, '%Y-%m-%d'))
			end_date = timezone.make_aware(datetime.datetime.strptime(end_date_string, '%Y-%m-%d'))
			if start_date > end_date:
				# swap dates
				temp_date = start_date
				start_date = end_date
				end_date = temp_date

				temp_date_string = start_date_string
				start_date_string = end_date_string
				end_date_string = temp_date_string

			invoices = InvoiceInformation.objects.filter(is_paid=True, cruise__cruise_end__lte=end_date+datetime.timedelta(days=1), cruise__cruise_start__gte=start_date-datetime.timedelta(days=1)).order_by('cruise__cruise_start') # is_finalized=True
			expected_invoices = InvoiceInformation.objects.filter(cruise__is_approved=True, cruise__cruise_end__lte=end_date+datetime.timedelta(days=1), cruise__cruise_start__gte=start_date-datetime.timedelta(days=1)).order_by('cruise__cruise_start') # is_finalized=True
			expected_unpaid_invoices = InvoiceInformation.objects.filter(is_paid=False, cruise__is_approved=True, cruise__cruise_end__lte=end_date+datetime.timedelta(days=1), cruise__cruise_start__gte=start_date-datetime.timedelta(days=1)).order_by('cruise__cruise_start')
			invoices |= InvoiceInformation.objects.filter(is_paid=True, cruise__isnull=True, paid_date__lte=end_date+datetime.timedelta(days=1), paid_date__gte=start_date-datetime.timedelta(days=1)).order_by('paid_date')

			for invoice in invoices:
				invoice_sum += invoice.get_sum()
				if not invoice.is_sent:
					unsent_invoice_sum += invoice.get_sum()

				if invoice.cruise is not None:
					cruise_leaders.append(invoice.cruise.leader)
					cruise_names.append(str(invoice.cruise))
					cruises.append(invoice.cruise)

					billing_type = invoice.cruise.get_billing_type()

					if billing_type == "education":
						education_count += 1
					elif billing_type == "boa":
						boa_count += 1
					elif billing_type == "research":
						research_count += 1
					elif billing_type == "external":
						external_count += 1

			for invoice in expected_invoices:
				expected_cruise_leaders.append(invoice.cruise.leader)
				expected_cruise_names.append(str(invoice.cruise))
				expected_cruises.append(invoice.cruise)
				expected_invoice_sum += invoice.get_sum()
				billing_type = invoice.cruise.get_billing_type()

				if billing_type == "education":
					expected_education_count += 1
				elif billing_type == "boa":
					expected_boa_count += 1
				elif billing_type == "research":
					expected_research_count += 1
				elif billing_type == "external":
					expected_external_count += 1

				if not invoice.is_sent:
					expected_unsent_invoice_sum += invoice.get_sum()

			# remove duplicates
			cruise_leaders = list(set(cruise_leaders))
			cruises = list(set(cruises))

			for cruise in cruises:
				for cruise_day in cruise.get_cruise_days():
					if cruise_day.is_long_day:
						long_day_count += 1
					else:
						short_day_count += 1

			expected_cruise_leaders = list(set(expected_cruise_leaders))
			expected_cruises = list(set(expected_cruises))

			for cruise in expected_cruises:
				for cruise_day in cruise.get_cruise_days():
					if cruise_day.is_long_day:
						expected_long_day_count += 1
					else:
						expected_short_day_count += 1

		else:
			messages.add_message(request, messages.INFO, mark_safe('<i class="fa fa-info-circle" aria-hidden="true"></i> Please enter a start date and end date to get an invoice summary for.'))
	else:
		raise PermissionDenied

	return render(request,
		template,
		{
			'invoices': invoices,
			'has_dates_selected': has_dates_selected,
			'start_date': start_date_string,
			'end_date': end_date_string,
			'cruise_names': cruise_names,
			'cruise_leaders': cruise_leaders,
			'unsent_invoice_sum': unsent_invoice_sum,
			'invoice_sum': invoice_sum,
			'expected_invoices': expected_invoices,
			'expected_cruise_names': expected_cruise_names,
			'expected_cruise_leaders': expected_cruise_leaders,
			'expected_unsent_invoice_sum': expected_unsent_invoice_sum,
			'expected_invoice_sum': expected_invoice_sum,
			'seasons': seasons,
			'years': years,
			'expected_unpaid_invoices': expected_unpaid_invoices,
			'research_count': research_count,
			'education_count': education_count,
			'boa_count': boa_count,
			'external_count': external_count,
			'short_day_count': short_day_count,
			'long_day_count': long_day_count,
			'expected_research_count': expected_research_count,
			'expected_education_count': expected_education_count,
			'expected_boa_count': expected_boa_count,
			'expected_external_count': expected_external_count,
			'expected_short_day_count': expected_short_day_count,
			'expected_long_day_count': expected_long_day_count
		}
	)

@csrf_exempt
def reject_invoice(request, pk):
	invoice = get_object_or_404(InvoiceInformation, pk=pk)
	if request.user.userdata.role == "invoicer":
		#message
		message = ""
		try:
			json_data = json.loads(request.body.decode("utf-8"))
			message = json_data["message"]
		except:
			message = ""
		#end message
		invoice.is_finalized = False
		invoice.rejection_message = message
		invoice.save()
		action = Action(user=request.user, target=str(invoice))
		action.action = "rejected invoice"
		action.timestamp = timezone.now()
		action.save()
		messages.add_message(request, messages.SUCCESS, mark_safe('Invoice "' + str(invoice) + '" rejected.'))
		admin_user_emails = [admin_user.email for admin_user in list(User.objects.filter(userdata__role='admin'))]
		send_template_only_email(admin_user_emails, EmailTemplate.objects.get(title='Invoice rejected'), invoice=invoice)
	else:
		raise PermissionDenied
	return JsonResponse(json.dumps([], ensure_ascii=True), safe=False)

def mark_invoice_as_finalized(request, pk):
	invoice = get_object_or_404(InvoiceInformation, pk=pk)
	if (request.user.is_superuser):
		invoice.is_finalized = True
		invoice.save()
		action = Action(user=request.user, target=str(invoice))
		action.action = "marked invoice as finalized"
		action.timestamp = timezone.now()
		action.save()
		messages.add_message(request, messages.SUCCESS, mark_safe('Invoice "' + str(invoice) + '" marked as finalized. It is now viewable by invoicers.'))
		invoicer_user_emails = [invoice_user.email for invoice_user in list(User.objects.filter(userdata__role='invoicer'))]
		send_template_only_email(invoicer_user_emails, EmailTemplate.objects.get(title='New invoice ready'), invoice=invoice)
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])

def mark_invoice_as_unfinalized(request, pk):
	invoice = get_object_or_404(InvoiceInformation, pk=pk)
	if (request.user.is_superuser and not invoice.is_sent):
		invoice.is_finalized = False
		invoice.save()
		action = Action(user=request.user, target=str(invoice))
		action.action = "marked invoice as unfinalized"
		action.timestamp = timezone.now()
		action.save()
		messages.add_message(request, messages.SUCCESS, mark_safe('Invoice "' + str(invoice) + '" marked as finalized. It is no longer viewable by invoicers.'))
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])

def mark_invoice_as_paid(request, pk):
	invoice = get_object_or_404(InvoiceInformation, pk=pk)
	if (request.user.userdata.role == "invoicer"):
		invoice.is_paid = True
		invoice.paid_date = timezone.now()
		invoice.save()
		action = Action(user=request.user, target=str(invoice))
		action.action = "marked invoice as paid"
		action.timestamp = timezone.now()
		action.save()
		messages.add_message(request, messages.SUCCESS, mark_safe('Invoice "' + str(invoice) + '" marked as paid.'))
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])

def mark_invoice_as_unpaid(request, pk):
	invoice = get_object_or_404(InvoiceInformation, pk=pk)
	if (request.user.userdata.role == "invoicer"):
		invoice.is_paid = False
		invoice.save()
		action = Action(user=request.user, target=str(invoice))
		action.action = "marked invoice as unpaid"
		action.timestamp = timezone.now()
		action.save()
		messages.add_message(request, messages.SUCCESS, mark_safe('Invoice "' + str(invoice) + '" marked as unpaid.'))
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])

def mark_invoice_as_sent(request, pk):
	invoice = get_object_or_404(InvoiceInformation, pk=pk)
	if (request.user.userdata.role == "invoicer"):
		invoice.is_sent = True
		invoice.send_date = timezone.now()
		invoice.save()
		action = Action(user=request.user, target=str(invoice))
		action.action = "marked as sent"
		action.timestamp = timezone.now()
		action.save()
		messages.add_message(request, messages.SUCCESS, mark_safe('Invoice "' + str(invoice) + '" marked as sent.'))
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])

def mark_invoice_as_unsent(request, pk):
	invoice = get_object_or_404(InvoiceInformation, pk=pk)
	if (request.user.userdata.role == "invoicer"):
		invoice.is_sent = False
		invoice.save()
		action = Action(user=request.user, target=str(invoice))
		action.action = "marked as unsent"
		action.timestamp = timezone.now()
		action.save()
		messages.add_message(request, messages.SUCCESS, mark_safe('Invoice "' + str(invoice) + '" marked as unsent.'))
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])