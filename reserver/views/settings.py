from django.views.generic.edit import UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.safestring import mark_safe
from django.utils import timezone

from reserver.models import Settings, Action, get_settings_object
from reserver.forms import SettingsForm

class SettingsEditView(UpdateView):
	model = Settings
	template_name = 'reserver/settings/settings_edit_form.html'
	form_class = SettingsForm

	def get_object(self):
		return get_settings_object()

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "edited system settings"
		action.save()
		messages.add_message(self.request, messages.SUCCESS, mark_safe('System settings successfully updated.'))
		return reverse_lazy('settings')

	def get(self, request, *args, **kwargs):
		self.object = get_settings_object()
		form_class = self.get_form_class()
		form = self.get_form(form_class)

		return self.render_to_response(
			self.get_context_data(
				form=form
			)
		)
