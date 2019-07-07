from django.shortcuts import get_object_or_404, render
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.utils import timezone

from reserver.models import EmailNotification, EmailTemplate, Action
from reserver.forms import NotificationForm

def admin_notification_view(request):
	from reserver.utils import check_default_models
	check_default_models()
	notifications = EmailNotification.objects.filter(is_special=True)
	email_templates = EmailTemplate.objects.all()
	return render(request, 'reserver/notifications/admin_notifications.html', {'notifications':notifications, 'email_templates':email_templates})

class CreateNotification(CreateView):
	model = EmailNotification
	template_name = 'reserver/notifications/notification_create_form.html'
	form_class = NotificationForm

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "created notification"
		action.save()
		return reverse_lazy('notifications')

	def get_form_kwargs(self):
		kwargs = super(CreateNotification, self).get_form_kwargs()
		kwargs.update({'request': self.request})
		return kwargs

	def get(self, request, *args, **kwargs):
		"""Handles creation of new blank form/formset objects."""
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
		notification = form.save(commit=False)
		notification.is_special = True
		notification.save()
		self.object = form.save()
		return HttpResponseRedirect(self.get_success_url())

	def form_invalid(self, form):
		"""Throw form back at user."""
		return self.render_to_response(
			self.get_context_data(
				form=form
			)
		)

class NotificationEditView(UpdateView):
	model = EmailNotification
	template_name = 'reserver/notifications/notification_edit_form.html'
	form_class = NotificationForm

	def get_form_kwargs(self):
		kwargs = super(NotificationEditView, self).get_form_kwargs()
		kwargs.update({'request': self.request})
		return kwargs

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "edited notification"
		action.save()
		return reverse_lazy('notifications')

	def get(self, request, *args, **kwargs):
		self.object = get_object_or_404(EmailNotification, pk=self.kwargs.get('pk'))
		form_class = self.get_form_class()
		form = self.get_form(form_class)

		form.initial={

			'recips':self.object.recipients.all(),
			'event':self.object.event,
			'template':self.object.template,

		}

		return self.render_to_response(
			self.get_context_data(
				form=form
			)
		)

	def post(self, request, *args, **kwargs):
		self.object = get_object_or_404(EmailNotification, pk=self.kwargs.get('pk'))
		form_class = self.get_form_class()
		form = self.get_form(form_class)
		# check if form is valid, handle outcome
		if form.is_valid():
			return self.form_valid(form)
		else:
			return self.form_invalid(form)

	def form_valid(self, form):
		notification = form.save(commit=False)
		notification.is_special = True
		notification.save()
		self.object = form.save()
		return HttpResponseRedirect(self.get_success_url())

	def form_invalid(self, form):
		"""Throw form back at user."""
		return self.render_to_response(
			self.get_context_data(
				form=form
			)
		)

class NotificationDeleteView(DeleteView):
	model = EmailNotification
	template_name = 'reserver/notifications/notification_delete_form.html'
	success_url = reverse_lazy('notifications')

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "deleted notification"
		action.save()
		return reverse_lazy('notifications')
