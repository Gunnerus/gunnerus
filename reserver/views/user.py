from django.shortcuts import render, redirect
from django.views.generic.edit import UpdateView
from django.urls import reverse_lazy, reverse
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.utils.safestring import mark_safe
from django.utils import timezone

from django.contrib.auth.models import User

from reserver.models import User, Cruise
from reserver.forms import UserForm

def login_redirect(request):
	redirect_target = reverse_lazy('home')
	if request.user.is_authenticated():
		if request.user.userdata.role == "invoicer":
			redirect_target = reverse_lazy('invoicer-overview')
		elif request.user.userdata.role == "admin":
			redirect_target = reverse_lazy('admin')
	else:
		raise PermissionDenied
	return redirect(redirect_target)

def upcoming_cruises_view(request):
	upcoming_cruises = list(set(list(Cruise.objects.filter(leader=request.user, is_submitted=True, is_approved=True, cruise_end__gte=timezone.now()) | Cruise.objects.filter(owner=request.user, is_submitted=True, is_approved=True, cruise_end__gte=timezone.now()))))
	context = {
		'cruises': sorted(list(upcoming_cruises), key=lambda x: str(x.cruise_start), reverse=True)
	}
	return render(request, 'reserver/user/user_upcoming_cruises.html', context=context)

def submitted_cruises_view(request):
	submitted_cruises = list(set(list(Cruise.objects.filter(leader=request.user, is_submitted=True, is_approved=False) | Cruise.objects.filter(owner=request.user, is_submitted=True, is_approved=False))))
	context = {
		'cruises': sorted(list(submitted_cruises), key=lambda x: str(x.cruise_start), reverse=True)
	}
	return render(request, 'reserver/user/user_submitted_cruises.html', context=context)

def unsubmitted_cruises_view(request):
	unsubmitted_cruises = list(set(list(Cruise.objects.filter(leader=request.user, is_submitted=False) | Cruise.objects.filter(owner=request.user, is_submitted=False))))
	context = {
		'cruises': sorted(list(unsubmitted_cruises), key=lambda x: str(x.cruise_start), reverse=True)
	}
	return render(request, 'reserver/user/user_unsubmitted_cruises.html', context=context)

def finished_cruises_view(request):
	finished_cruises = list(set(list(Cruise.objects.filter(leader=request.user, is_submitted=True, is_approved=True, cruise_end__lte=timezone.now()) | Cruise.objects.filter(owner=request.user, is_submitted=True, cruise_end__lte=timezone.now()))))
	context = {
		'cruises': sorted(list(finished_cruises), key=lambda x: str(x.cruise_start), reverse=True)
	}
	return render(request, 'reserver/user/user_finished_cruises.html', context=context)

class UserView(UpdateView):
	template_name = 'reserver/user/user.html'
	model = User
	form_class = UserForm
	slug_field = "username"
	success_url = reverse_lazy('user-page')

	def post(self, request, *args, **kwargs):
		messages.add_message(request, messages.SUCCESS, "Profile updated.")
		return super(UserView, self).post(request, *args, **kwargs)

	def get_form_kwargs(self):
		kwargs = super(UserView, self).get_form_kwargs()
		kwargs.update({'request': self.request})
		return kwargs

	def get_context_data(self, **kwargs):
		context = super(UserView, self).get_context_data(**kwargs)

		if not self.request.user.userdata.email_confirmed and self.request.user.userdata.role == "":
			messages.add_message(self.request, messages.WARNING, mark_safe("You have not yet confirmed your email address. Your account will not be eligible for approval or submitting cruises before this is done. If you typed the wrong email address while signing up, correct it in the form below and we'll send you a new one. You may have to add no-reply@rvgunnerus.no to your contact list if our messages go to spam."+"<br><br><a class='btn btn-primary' href='"+reverse('resend-activation-mail')+"'>Resend activation email</a>"))
		elif self.request.user.userdata.email_confirmed and self.request.user.userdata.role == "":
			messages.add_message(self.request, messages.WARNING, "Your user account has not been approved by an administrator yet. You may save cruise drafts and edit them, but you may not submit cruises for approval before your account is approved.")

		# add submitted cruises to context
		submitted_cruises = list(set(list(Cruise.objects.filter(leader=self.request.user, is_submitted=True) | Cruise.objects.filter(owner=self.request.user, is_submitted=True))))
		context['my_submitted_cruises'] = sorted(list(submitted_cruises), key=lambda x: str(x.cruise_start), reverse=True)

		# add unsubmitted cruises to context
		unsubmitted_cruises = list(set(list(Cruise.objects.filter(leader=self.request.user, is_submitted=False) | Cruise.objects.filter(owner=self.request.user, is_submitted=False))))
		context['my_unsubmitted_cruises'] = sorted(list(unsubmitted_cruises), key=lambda x: str(x.cruise_start), reverse=True)
		return context

class CurrentUserView(UserView):
	def get_object(self):
		return self.request.user