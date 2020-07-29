import tempfile, zipfile

from wsgiref.util import FileWrapper

from django.http import HttpResponse
from django.utils import timezone
from django.shortcuts import render, redirect
from django.views.generic.edit import UpdateView
from django.urls import reverse_lazy, reverse
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.utils.safestring import mark_safe
from django.core import serializers

from django.contrib.auth.models import User

from reserver.models import UserData, Cruise, CruiseDay, Organization, Document, Equipment
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
	upcoming_cruises = list(set(list(Cruise.objects.filter(leader=request.user, is_submitted=True, is_archived=False, is_hidden=False, is_approved=True, cruise_end__gte=timezone.now()) | Cruise.objects.filter(owner=request.user, is_submitted=True, is_archived=False, is_hidden=False, is_approved=True, cruise_end__gte=timezone.now()))))
	context = {
		'cruises': sorted(list(upcoming_cruises), key=lambda x: str(x.cruise_start), reverse=True)
	}
	return render(request, 'reserver/user/user_upcoming_cruises.html', context=context)

def submitted_cruises_view(request):
	submitted_cruises = list(set(list(Cruise.objects.filter(leader=request.user, is_submitted=True, is_archived=False, is_hidden=False, is_approved=False) | Cruise.objects.filter(owner=request.user, is_submitted=True, is_archived=False, is_hidden=False, is_approved=False))))
	context = {
		'cruises': sorted(list(submitted_cruises), key=lambda x: str(x.cruise_start), reverse=True)
	}
	return render(request, 'reserver/user/user_submitted_cruises.html', context=context)

def unsubmitted_cruises_view(request):
	unsubmitted_cruises = list(set(list(Cruise.objects.filter(leader=request.user, is_submitted=False, is_archived=False, is_hidden=False) | Cruise.objects.filter(owner=request.user, is_submitted=False, is_archived=False, is_hidden=False))))
	context = {
		'cruises': sorted(list(unsubmitted_cruises), key=lambda x: str(x.cruise_start), reverse=True)
	}
	return render(request, 'reserver/user/user_unsubmitted_cruises.html', context=context)

def finished_cruises_view(request):
	finished_cruises = list(set(list(Cruise.objects.filter(leader=request.user, is_submitted=True, is_cancelled=False, is_approved=True, cruise_end__lte=timezone.now(), is_archived=False, is_hidden=False) | Cruise.objects.filter(owner=request.user, is_submitted=True, is_cancelled=False, cruise_end__lte=timezone.now(), is_archived=False, is_hidden=False))))
	context = {
		'finished_cruises': sorted(list(finished_cruises), key=lambda x: str(x.cruise_start), reverse=True)
	}
	return render(request, 'reserver/user/user_finished_cruises.html', context=context)

def archived_finished_cruises_view(request):
	finished_cruises = list(set(list(Cruise.objects.filter(leader=request.user, is_archived=True, is_hidden=False, is_submitted=True, is_cancelled=False, is_approved=True, cruise_end__lte=timezone.now()) | Cruise.objects.filter(owner=request.user, is_archived=True, is_hidden=False, is_submitted=True, is_cancelled=False, cruise_end__lte=timezone.now()))))
	context = {
		'cruises': sorted(list(finished_cruises), key=lambda x: str(x.cruise_start), reverse=True)
	}
	return render(request, 'reserver/user/user_archived_finished_cruises.html', context=context)

def archived_unsubmitted_cruises_view(request):
	unsubmitted_cruises = list(set(list(Cruise.objects.filter(leader=request.user, is_archived=True, is_hidden=False, is_submitted=False) | Cruise.objects.filter(owner=request.user, is_archived=True, is_hidden=False, is_submitted=False))))
	context = {
		'cruises': sorted(list(unsubmitted_cruises), key=lambda x: str(x.cruise_start), reverse=True)
	}
	return render(request, 'reserver/user/user_archived_unsubmitted_cruises.html', context=context)

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

		return context

class CurrentUserView(UserView):
	def get_object(self):
		return self.request.user

def export_data_view(request):
	"""
	Create a ZIP file on disk and transmit it in chunks of 8KB,
	without loading the whole file into memory. A similar approach can
	be used for large dynamic PDF files.
	"""
	temp = tempfile.TemporaryFile()

	archive = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED)

	JSONSerializer = serializers.get_serializer("json")
	json_serializer = JSONSerializer()

	# store cruise data

	cruises = list(set(list(Cruise.objects.filter(leader=request.user) | Cruise.objects.filter(owner=request.user))))

	cruise_data = tempfile.TemporaryFile(mode='r+')
	json_serializer.serialize(cruises, stream=cruise_data)
	cruise_data.seek(0)

	archive.writestr("cruises.json", cruise_data.read())

	# store cruise days

	cruise_days = list(set(list(CruiseDay.objects.filter(cruise__leader=request.user) | CruiseDay.objects.filter(cruise__owner=request.user))))

	cruise_days_data = tempfile.TemporaryFile(mode='r+')
	json_serializer.serialize(cruise_days, stream=cruise_days_data)
	cruise_days_data.seek(0)

	archive.writestr("cruise_days.json", cruise_days_data.read())

	# store equipment

	cruise_equipment = list(set(list(Equipment.objects.filter(cruise__leader=request.user) | Equipment.objects.filter(cruise__leader=request.user))))

	cruise_equipment_data = tempfile.TemporaryFile(mode='r+')
	json_serializer.serialize(cruise_equipment, stream=cruise_equipment_data)
	cruise_equipment_data.seek(0)

	archive.writestr("cruise_equipment.json", cruise_equipment_data.read())

	# store documents

	cruise_documents = list(set(list(Document.objects.filter(cruise__leader=request.user) | Document.objects.filter(cruise__owner=request.user))))

	cruise_documents_data = tempfile.TemporaryFile(mode='r+')
	json_serializer.serialize(cruise_documents, stream=cruise_documents_data)
	cruise_documents_data.seek(0)

	archive.writestr("cruise_documents.json", cruise_documents_data.read())

	for document in cruise_documents:
		if document.file:
			archive.writestr("uploads\\" + document.file.name, document.file.read())

	# store user data

	user = list(User.objects.filter(pk=request.user.pk))

	user_file = tempfile.TemporaryFile(mode='r+')
	json_serializer.serialize(user, stream=user_file)
	user_file.seek(0)

	archive.writestr("user.json", user_file.read())

	user_data = list(UserData.objects.filter(user=request.user))

	user_data_file = tempfile.TemporaryFile(mode='r+')
	json_serializer.serialize(user_data, stream=user_data_file)
	user_data_file.seek(0)

	archive.writestr("user_data.json", user_data_file.read())

	# store user organization data

	user_org_data = list(Organization.objects.filter(pk=request.user.userdata.organization.pk))

	user_org_data_file = tempfile.TemporaryFile(mode='r+')
	json_serializer.serialize(user_org_data, stream=user_org_data_file)
	user_org_data_file.seek(0)

	archive.writestr("organization.json", user_org_data_file.read())

	#close and serve archive

	archive.close()
	length = temp.tell()
	wrapper = FileWrapper(temp)
	temp.seek(0)
	response = HttpResponse(wrapper, content_type='application/zip')
	response['Content-Disposition'] = 'attachment; filename=user-export-' + str(request.user) + '-'+timezone.now().strftime('%Y-%m-%d-%H%M%S')+'.zip'
	response['Content-Length'] = length
	return response
