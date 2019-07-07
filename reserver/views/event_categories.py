from django.shortcuts import get_object_or_404, render
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.safestring import mark_safe

from django.http import HttpResponseRedirect
from django.utils import timezone

from reserver.models import EventCategory, Action
from reserver.forms import EventCategoryNonDefaultForm, EventCategoryForm

def admin_eventcategory_view(request):
	from reserver.utils import check_default_models
	check_default_models()
	eventcategories = list(EventCategory.objects.all())

	return render(request, 'reserver/event_categories/admin_eventcategories.html', {'eventcategories':eventcategories})

class CreateEventCategory(CreateView):
	model = EventCategory
	template_name = 'reserver/event_categories/eventcategory_create_form.html'
	form_class = EventCategoryNonDefaultForm

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "created event category"
		action.save()
		return reverse_lazy('eventcategories')

class EventCategoryEditView(UpdateView):
	model = EventCategory
	template_name = 'reserver/event_categories/eventcategory_edit_form.html'

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		self.object = get_object_or_404(EventCategory, pk=self.kwargs.get('pk'))
		if self.object.is_default:
			action.action = "edited built-in event category"
		else:
			action.action = "edited event category"
		action.save()
		return reverse_lazy('eventcategories')

	def get_form_class(self):
		self.object = get_object_or_404(EventCategory, pk=self.kwargs.get('pk'))
		if self.object.is_default:
			return EventCategoryForm
		else:
			return EventCategoryNonDefaultForm

class EventCategoryDeleteView(DeleteView):
	model = EventCategory
	template_name = 'reserver/event_categories/eventcategory_delete_form.html'

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "deleted event category"
		action.save()
		return reverse_lazy('eventcategories')

# Simple version with no feedback, only resets the object and refreshes the page.
def event_category_reset_view(request, pk):
	from reserver.utils import default_event_categories
	event_category = get_object_or_404(EventCategory, pk=pk)
	default = next(df for df in default_event_categories if df[0] == event_category.name)
	event_category.name = default[0]
	event_category.icon = default[1]
	event_category.colour = default[2]
	event_category.description = default[3]
	event_category.is_default = True
	event_category.save()
	action = Action(user=request.user, timestamp=timezone.now(), target=str(event_category))
	action.action = "reset event category to default"
	action.save()
	messages.add_message(request, messages.SUCCESS, mark_safe('The contents of the event category "' + str(event_category) + '" was reset to its default values.'))
	return HttpResponseRedirect(reverse_lazy('eventcategories'))