def announcements_processor(request):
	from reserver.models import Announcement, render_announcements
	from django.utils.safestring import mark_safe
	from reserver.views import get_cruises_need_attention, get_users_not_approved, get_unapproved_cruises

	if request.user.is_authenticated():
		if request.user.is_superuser:
			cruises_badge = len(get_cruises_need_attention())
			users_badge = len(get_users_not_approved())
			overview_badge = cruises_badge + users_badge + len(get_unapproved_cruises())
			return {'announcements': mark_safe(render_announcements(user=request.user)), 'cruises_badge': cruises_badge, 'users_badge': users_badge, 'overview_badge': overview_badge}
		else:
			return {'announcements': mark_safe(render_announcements(user=request.user))}
	else:
		return {'announcements': mark_safe(render_announcements())}
	