from django.shortcuts import render
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.utils import timezone

from reserver.models import Organization, Action
from reserver.forms import OrganizationForm

def admin_organization_view(request):
	organizations = list(Organization.objects.all())

	return render(request, 'reserver/organizations/admin_organizations.html', {'organizations':organizations})

class CreateOrganization(CreateView):
	model = Organization
	template_name = 'reserver/organizations/organization_create_form.html'
	form_class = OrganizationForm

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "created organization"
		action.save()
		return reverse_lazy('organizations')

class OrganizationEditView(UpdateView):
	model = Organization
	template_name = 'reserver/organizations/organization_edit_form.html'
	form_class = OrganizationForm

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "edited organization"
		action.save()
		return reverse_lazy('organizations')

class OrganizationDeleteView(DeleteView):
	model = Organization
	template_name = 'reserver/organizations/organization_delete_form.html'

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "deleted organization"
		action.save()
		return reverse_lazy('organizations')
