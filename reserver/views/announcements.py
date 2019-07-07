from django.shortcuts import render
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.utils import timezone

from reserver.models import Announcement, Action
from reserver.forms import AnnouncementForm

def admin_announcements_view(request):
	stored_announcements = list(Announcement.objects.all())
	return render(request, 'reserver/announcements/admin_announcements.html', {'stored_announcements':stored_announcements})

class CreateAnnouncement(CreateView):
	model = Announcement
	template_name = 'reserver/announcements/announcement_create_form.html'
	form_class = AnnouncementForm

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "created announcement"
		action.save()
		return reverse_lazy('announcements')

class AnnouncementEditView(UpdateView):
	model = Announcement
	template_name = 'reserver/announcements/announcement_edit_form.html'
	form_class = AnnouncementForm

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "edited announcement"
		action.save()
		return reverse_lazy('announcements')

class AnnouncementDeleteView(DeleteView):
	model = Announcement
	template_name = 'reserver/announcements/announcement_delete_form.html'

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "deleted announcement"
		action.save()
		return reverse_lazy('announcements')
