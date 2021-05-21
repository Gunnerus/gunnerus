def announcements_processor(request):
	from reserver.models import render_announcements, InvoiceInformation, get_events_in_period
	from django.utils.safestring import mark_safe
	from reserver.utils import get_cruises_need_attention, get_users_not_approved, get_users_requested_account_deletion, get_unapproved_cruises, event_filter
	from django.utils import timezone
	import datetime

	if request.user.is_authenticated:
		if request.user.is_superuser:
			current_day = timezone.now()

			start_date = current_day - datetime.timedelta(days=current_day.weekday())
			end_date = start_date + datetime.timedelta(days=6)

			events = get_events_in_period(start_date, end_date)
			events = list(filter(event_filter, events))

			events_badge = len(events)
			cruises_badge = len(get_cruises_need_attention())
			users_badge = len(get_users_not_approved() + get_users_requested_account_deletion())
			overview_badge = cruises_badge + users_badge + len(get_unapproved_cruises())
			unfinalized_invoices_badge = InvoiceInformation.objects.filter(is_finalized=False, is_paid=False, cruise__is_approved=True, cruise__cruise_end__lte=timezone.now()).count()
			return {'announcements': mark_safe(render_announcements(user=request.user)), 'cruises_badge': cruises_badge, 'users_badge': users_badge, 'overview_badge': overview_badge, 'unfinalized_invoices_badge': unfinalized_invoices_badge, 'events_badge': events_badge}
		else:
			return {'announcements': mark_safe(render_announcements(user=request.user))}
	else:
		return {'announcements': mark_safe(render_announcements())}
