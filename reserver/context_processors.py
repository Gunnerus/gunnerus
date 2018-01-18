def announcements_processor(request):
	from reserver.models import Announcement, render_announcements, InvoiceInformation
	from django.utils.safestring import mark_safe
	from reserver.views import get_cruises_need_attention, get_users_not_approved, get_unapproved_cruises
	from django.utils import timezone

	if request.user.is_authenticated():
		if request.user.is_superuser:
			cruises_badge = len(get_cruises_need_attention())
			users_badge = len(get_users_not_approved())
			overview_badge = cruises_badge + users_badge + len(get_unapproved_cruises())
			unfinalized_invoices_badge = InvoiceInformation.objects.filter(is_finalized=False, cruise__is_approved=True, cruise__cruise_end__lte=timezone.now()).count()
			return {'announcements': mark_safe(render_announcements(user=request.user)), 'cruises_badge': cruises_badge, 'users_badge': users_badge, 'overview_badge': overview_badge, 'unfinalized_invoices_badge': unfinalized_invoices_badge}
		else:
			return {'announcements': mark_safe(render_announcements(user=request.user))}
	else:
		return {'announcements': mark_safe(render_announcements())}