import datetime

from django.shortcuts import get_object_or_404
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect
from django.utils import timezone

from reserver.models import Action, EmailTemplate
from reserver.forms import EmailTemplateNonDefaultForm, EmailTemplateForm

class CreateEmailTemplate(CreateView):
	model = EmailTemplate
	template_name = 'reserver/email_templates/email_template_create_form.html'
	form_class = EmailTemplateNonDefaultForm

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "created email template"
		action.save()
		return reverse_lazy('notifications')

	def get_form_kwargs(self):
		kwargs = super(CreateEmailTemplate, self).get_form_kwargs()
		kwargs.update({'request': self.request})
		return kwargs

	def get(self, request, *args, **kwargs):
		self.object = None
		form_class = self.get_form_class()
		form = self.get_form(form_class)

		return self.render_to_response(
			self.get_context_data(
				form=form
			)
		)

	def post(self, request, *args, **kwargs):
		self.object = None
		form_class = self.get_form_class()
		form = self.get_form(form_class)
		# check if form is valid, handle outcome
		if form.is_valid():
			return self.form_valid(form)
		else:
			return self.form_invalid(form)

	def form_valid(self, form):
		template = form.save(commit=False)
		if form.cleaned_data.get("time_before_hours") is not None:
			hours = form.cleaned_data.get("time_before_hours")
		else:
			hours = 0
		if form.cleaned_data.get("time_before_days") is not None:
			days = form.cleaned_data.get("time_before_days")
		else:
			days = 0
		if form.cleaned_data.get("time_before_weeks") is not None:
			weeks = form.cleaned_data.get("time_before_weeks")
		else:
			weeks = 0
		if hours == days == weeks == 0:
			template.time_before = None
		else:
			template.time_before = datetime.timedelta(hours=hours, days=days, weeks=weeks)
		template.save()
		self.object = form.save()
		return HttpResponseRedirect(self.get_success_url())

	def form_invalid(self, form):
		"""Throw form back at user."""
		return self.render_to_response(
			self.get_context_data(
				form=form
			)
		)

class EmailTemplateEditView(UpdateView):
	model = EmailTemplate
	template_name = 'reserver/email_templates/email_template_edit_form.html'

	def get_form_kwargs(self):
		kwargs = super(EmailTemplateEditView, self).get_form_kwargs()
		kwargs.update({'request': self.request})
		return kwargs

	def get_form_class(self):
		self.object = get_object_or_404(EmailTemplate, pk=self.kwargs.get('pk'))
		if self.object.is_default:
			return EmailTemplateForm
		else:
			return EmailTemplateNonDefaultForm

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		if self.object.is_default:
			action.action = "edited built-in email template"
		else:
			action.action = "edited email template"
		action.save()
		return reverse_lazy('notifications')

	def get(self, request, *args, **kwargs):
		"""Handles creation of new blank form/formset objects."""
		self.object = get_object_or_404(EmailTemplate, pk=self.kwargs.get('pk'))
		form_class = self.get_form_class()
		form = self.get_form(form_class)

		hours = days = weeks = None
		if self.object.time_before is not None and self.object.time_before.total_seconds() > 0:
			time = self.object.time_before
			weeks = int(time.days / 7)
			time -= datetime.timedelta(days=weeks * 7)
			days = time.days
			time -= datetime.timedelta(days=days)
			hours = int(time.seconds / 3600)

		form.initial={

			'title':self.object.title,
			'group':self.object.group,
			'message':self.object.message,
			'is_active':self.object.is_active,
			'is_muteable':self.object.is_muteable,
			'date':self.object.date,
			'time_before_hours':hours,
			'time_before_days':days,
			'time_before_weeks':weeks,

		}

		return self.render_to_response(
			self.get_context_data(
				form=form
			)
		)

	def post(self, request, *args, **kwargs):
		self.object = get_object_or_404(EmailTemplate, pk=self.kwargs.get('pk'))
		form_class = self.get_form_class()
		form = self.get_form(form_class)
		# check if form is valid, handle outcome
		if form.is_valid():
			return self.form_valid(form)
		else:
			return self.form_invalid(form)

	def form_valid(self, form):
		template = form.save(commit=False)
		if not template.is_default:
			if form.cleaned_data.get("time_before_hours") is not None:
				hours = form.cleaned_data.get("time_before_hours")
			else:
				hours = 0
			if form.cleaned_data.get("time_before_days") is not None:
				days = form.cleaned_data.get("time_before_days")
			else:
				days = 0
			if form.cleaned_data.get("time_before_weeks") is not None:
				weeks = form.cleaned_data.get("time_before_weeks")
			else:
				weeks = 0
			if hours == days == weeks == 0:
				template.time_before = None
			else:
				template.time_before = datetime.timedelta(hours=hours, days=days, weeks=weeks)
		template.save()
		self.object = form.save()
		return HttpResponseRedirect(self.get_success_url())

	def form_invalid(self, form):
		"""Throw form back at user."""
		return self.render_to_response(
			self.get_context_data(
				form=form
			)
		)

class EmailTemplateDeleteView(DeleteView):
	model = EmailTemplate
	template_name = 'reserver/email_templates/email_template_delete_form.html'

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "deleted email template"
		action.save()
		return reverse_lazy('notifications')

# Not finished implementing. NOT IN USE RIGHT NOW
class EmailTemplateResetView(UpdateView):
	model = EmailTemplate
	template_name = 'reserver/email_templates/email_template_reset_form.html'

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "reset email template to default"
		action.save()
		return reverse_lazy('notifications')

# Simple version with no feedback, only resets the object and refreshes the page.
def email_template_reset_view(request, pk):
	from reserver.utils import default_email_templates
	template = get_object_or_404(EmailTemplate, pk=pk)
	default = next(df for df in default_email_templates if df[0] == template.title)
	template.title = default[0]
	template.message = default[2]
	template.time_before = default[3]
	template.is_active = default[5]
	template.is_muteable = default[6]
	template.date = default[4]
	template.is_default = True
	template.group = default[1]
	template.save()
	action = Action(user=request.user, timestamp=timezone.now(), target=str(template))
	action.action = "reset email template to default"
	action.save()
	messages.add_message(request, messages.SUCCESS, mark_safe('The contents of the email template "' + str(template) + '" was reset to its default values.'))
	return HttpResponseRedirect(reverse_lazy('notifications'))
