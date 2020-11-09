import datetime

from django.shortcuts import render
from django.urls import reverse
from django.contrib import messages
from django.utils.safestring import mark_safe
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.exceptions import PermissionDenied

from django.contrib.auth.models import User

from django.utils import timezone

from reserver.utils import get_cruises_need_attention, get_upcoming_cruises
from reserver.utils import get_unapproved_cruises, get_users_not_approved, get_users_requested_account_deletion
from reserver.models import Action, CruiseDay, Cruise, Season, Statistics

def admin_view(request):
	last_actions = list(Action.objects.filter(timestamp__lte=timezone.now(), timestamp__gt=timezone.now()-datetime.timedelta(days=30)))[:-4:-1]
	cruises_need_attention = get_cruises_need_attention()
	upcoming_cruises = get_upcoming_cruises()
	unapproved_cruises = get_unapproved_cruises()
	users_not_approved = get_users_not_approved()
	users_requested_account_deletion = get_users_requested_account_deletion()
	current_year = timezone.now().year
	next_year = timezone.now().year+1
	internal_days_remaining = 150-CruiseDay.objects.filter(event__start_time__year = current_year, cruise__is_approved = True, cruise__leader__userdata__organization__is_NTNU = True).count()
	external_days_remaining = 66-CruiseDay.objects.filter(event__start_time__year = current_year, cruise__is_approved = True, cruise__leader__userdata__organization__is_NTNU = False).count()
	internal_days_remaining_next_year = 150-CruiseDay.objects.filter(event__start_time__year = next_year, cruise__is_approved = True, cruise__leader__userdata__organization__is_NTNU = True).count()
	external_days_remaining_next_year = 30-CruiseDay.objects.filter(event__start_time__year = next_year, cruise__is_approved = True, cruise__leader__userdata__organization__is_NTNU = False).count()
	if len(cruises_need_attention) > 1:
		messages.add_message(request, messages.WARNING, mark_safe(('<i class="fa fa-exclamation-triangle" aria-hidden="true"></i> %s approved cruises have not had their information approved yet.' % str(len(cruises_need_attention)))+"<br><br><a class='btn btn-primary' href='#approved-cruises-needing-attention'><i class='fa fa-arrow-down' aria-hidden='true'></i> Jump to cruises</a>"))
	elif len(cruises_need_attention) == 1:
		messages.add_message(request, messages.WARNING, mark_safe('<i class="fa fa-exclamation-triangle" aria-hidden="true"></i> An approved cruise has not had its information approved yet.'+"<br><br><a class='btn btn-primary' href='#approved-cruises-needing-attention'><i class='fa fa-arrow-down' aria-hidden='true'></i> Jump to cruise</a>"))
	if (len(users_not_approved) + len(users_requested_account_deletion)) > 1:
		messages.add_message(request, messages.INFO, mark_safe(('<i class="fa fa-info-circle" aria-hidden="true"></i> %s users need attention.' % str(len(users_not_approved) + len(users_requested_account_deletion)))+"<br><br><a class='btn btn-primary' href='#users-needing-attention'><i class='fa fa-arrow-down' aria-hidden='true'></i> Jump to users</a>"))
	elif (len(users_not_approved) + len(users_requested_account_deletion)) == 1:
		messages.add_message(request, messages.INFO, mark_safe('<i class="fa fa-info-circle" aria-hidden="true"></i> A user needs attention.'+"<br><br><a class='btn btn-primary' href='#users-needing-attention'><i class='fa fa-arrow-down' aria-hidden='true'></i> Jump to user</a>"))
	if len(unapproved_cruises) > 1:
		messages.add_message(request, messages.INFO, mark_safe(('<i class="fa fa-info-circle" aria-hidden="true"></i> %s cruises are awaiting approval.' % str(len(unapproved_cruises)))+"<br><br><a class='btn btn-primary' href='#unapproved-cruises-needing-attention'><i class='fa fa-arrow-down' aria-hidden='true'></i> Jump to cruises</a>"))
	elif len(unapproved_cruises) == 1:
		messages.add_message(request, messages.INFO, mark_safe('<i class="fa fa-info-circle" aria-hidden="true"></i> A cruise is awaiting approval.'+"<br><br><a class='btn btn-primary' href='#unapproved-cruises-needing-attention'><i class='fa fa-arrow-down' aria-hidden='true'></i> Jump to cruise</a>"))
	return render(request, 'reserver/admin/admin_overview.html', {'unapproved_cruises':unapproved_cruises, 'upcoming_cruises':upcoming_cruises, 'cruises_need_attention':cruises_need_attention, 'users_not_verified':users_not_approved, 'users_requested_account_deletion':users_requested_account_deletion, 'internal_days_remaining':internal_days_remaining, 'external_days_remaining':external_days_remaining, 'internal_days_remaining_next_year':internal_days_remaining_next_year, 'external_days_remaining_next_year':external_days_remaining_next_year, 'current_year':current_year, 'next_year':next_year, 'last_actions':last_actions})

def admin_cruise_view(request):
	cruises = list(Cruise.objects.filter(is_approved=True).order_by('-cruise_start'))
	cruises_need_attention = get_cruises_need_attention()
	if len(cruises_need_attention) > 1:
		messages.add_message(request, messages.WARNING, mark_safe(('<i class="fa fa-exclamation-triangle" aria-hidden="true"></i> %s upcoming cruises have not had their information approved yet.' % str(len(cruises_need_attention)))+"<br><br><a class='btn btn-primary' href='"+reverse('admin')+"#approved-cruises-needing-attention'><i class='fa fa-arrow-right' aria-hidden='true'></i> Jump to cruises</a>"))
	elif len(cruises_need_attention) == 1:
		messages.add_message(request, messages.WARNING, mark_safe('<i class="fa fa-exclamation-triangle" aria-hidden="true"></i> An upcoming cruise has not had its information approved yet.'+"<br><br><a class='btn btn-primary' href='"+reverse('admin')+"#approved-cruises-needing-attention'><i class='fa fa-arrow-right' aria-hidden='true'></i> Jump to cruise</a>"))
	return render(request, 'reserver/cruises/admin_cruises.html', {'cruises':cruises})

def admin_actions_view(request):
	actions = Action.objects.all()
	actions = actions[::-1]
	paginator = Paginator(actions, 20)
	page = request.GET.get('page')
	try:
		page_actions = paginator.page(page)
	except PageNotAnInteger:
		# If page is not an integer, deliver first page.
		page_actions = paginator.page(1)
	except EmptyPage:
		# If page is out of range (e.g. 9999), deliver last page of results.
		page_actions = paginator.page(paginator.num_pages)

	return render(request, 'reserver/admin/admin_actions.html', {'actions':page_actions})

def admin_statistics_view(request):
	#last_statistics = list(Statistics.objects.filter(timestamp__lte=timezone.now(), timestamp__gt=timezone.now()-datetime.timedelta(days=30)))
	last_statistics = list(Statistics.objects.filter(timestamp__lte=timezone.now()))
	seen_timestamps = set()
	unique_statistics = []
	for statistic in last_statistics:
		if statistic.timestamp.strftime('%Y-%m-%d') not in seen_timestamps:
			unique_statistics.append(statistic)
			seen_timestamps.add(statistic.timestamp.strftime('%Y-%m-%d'))
	operation_years = []
	for season in Season.objects.all():
		season_start_year = season.season_event.start_time.year
		season_end_year = season.season_event.end_time.year
		if season_start_year not in operation_years:
			operation_years.append(season_start_year)
		if season_end_year not in operation_years:
			operation_years.append(season_end_year)

	unique_statistics.reverse()

	paginator = Paginator(unique_statistics, 20)
	page = request.GET.get('page')
	try:
		page_statistics = paginator.page(page)
	except PageNotAnInteger:
		# If page is not an integer, deliver first page.
		page_statistics = paginator.page(1)
	except EmptyPage:
		# If page is out of range (e.g. 9999), deliver last page of results.
		page_statistics = paginator.page(paginator.num_pages)

	return render(request, 'reserver/admin/admin_statistics.html', {'statistics':page_statistics})

def admin_work_hour_view(request, **kwargs):
	if request.user.is_superuser:
		template = "reserver/work_hours/admin_work_hours.html"

		seasons = Season.objects.all()
		years = []

		# default: use the current year
		year = datetime.datetime.strftime(timezone.now(), '%Y')
		years.append(year)

		for season in seasons:
			years.append(season.season_event.start_time.strftime("%Y"))
			years.append(season.season_event.end_time.strftime("%Y"))

		years = reversed(sorted(list(set(years))))

		if kwargs.get("year"):
			year = kwargs.get("year")

		#start_date = timezone.make_aware(datetime.datetime.strptime(year+"-01-01", '%Y-%m-%d'))
		#end_date = timezone.make_aware(datetime.datetime.strptime(year+"-12-31", '%Y-%m-%d'))

		#invoices = InvoiceInformation.objects.filter(is_paid=True, cruise__cruise_end__lte=end_date+datetime.timedelta(days=1), cruise__cruise_start__gte=start_date-datetime.timedelta(days=1)).order_by('cruise__cruise_start') # is_finalized=True
		crew_users = User.objects.filter(is_staff=True)

	else:
		raise PermissionDenied

	return render(request,
		template,
		{
			'selected_year': year,
			'years': years,
			'crew_users': crew_users
		}
	)

def food_view(request, pk):
	cruise = Cruise.objects.get(pk=pk)
	days = list(CruiseDay.objects.filter(cruise=cruise.pk))
	return render(request, 'reserver/cruises/food.html', {'cruise':cruise, 'days':days})
