def announcements_processor(request):
	from reserver.models import Announcement, render_announcements
	from django.utils.safestring import mark_safe

	if request.user.is_authenticated():
		return {'announcements': mark_safe(render_announcements(user=request.user))}
	else:
		return {'announcements': mark_safe(render_announcements())}
	