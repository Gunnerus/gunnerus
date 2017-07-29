"""gunnerus URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from django.contrib.auth import views as auth_views
from reserver import views
from reserver.views import CruiseList, CruiseCreateView, CruiseEditView, CruiseDeleteView, CreateEvent, SeasonEditView, EventEditView, NotificationDeleteView
from reserver.views import UserView, CurrentUserView, submit_cruise, unsubmit_cruise, CruiseView, SeasonDeleteView, EventDeleteView, NotificationEditView
from reserver.views import approve_cruise, unapprove_cruise, approve_cruise_information, unapprove_cruise_information, CreateSeason, CreateNotification
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test

app_name = 'reserver'

urlpatterns = [
    url(r'^admin/django/', admin.site.urls, name='django-admin'),
	url(r'cruises/add/$', login_required(CruiseCreateView.as_view()), name='cruise-add'),
    url(r'cruises/(?P<pk>[0-9]+)/edit/$', login_required(CruiseEditView.as_view()), name='cruise-update'),
    url(r'cruises/(?P<pk>[0-9]+)/delete/$', login_required(CruiseDeleteView.as_view()), name='cruise-delete'),
    url(r'cruises/(?P<pk>[0-9]+)/view/$', login_required(CruiseView.as_view()), name='cruise-view'),
    url(r'cruises/(?P<pk>[0-9]+)/submit/$', login_required(views.submit_cruise), name='cruise-submit'),
    url(r'cruises/(?P<pk>[0-9]+)/unsubmit/$', login_required(views.unsubmit_cruise), name='cruise-unsubmit'),
    url(r'cruises/(?P<pk>[0-9]+)/approve/$', login_required(views.approve_cruise), name='cruise-approve'),
    url(r'cruises/(?P<pk>[0-9]+)/unapprove/$', login_required(views.unapprove_cruise), name='cruise-unapprove'),
    url(r'cruises/(?P<pk>[0-9]+)/approve-information/$', login_required(views.approve_cruise_information), name='cruise-approve-information'),
    url(r'cruises/(?P<pk>[0-9]+)/unapprove-information/$', login_required(views.unapprove_cruise_information), name='cruise-unapprove-information'),
	url(r'^user/$', login_required(CurrentUserView.as_view()), name='user-page'),
	url(r'^user/(?P<slug>[\w.@+-]+)/$', login_required(UserView.as_view()), name='user-page'),
	url(r'^$', views.index_view, name='home'), 
	url(r'^admin/cruises/$', login_required(user_passes_test(lambda u: u.is_superuser)(views.admin_cruise_view)), name='admin-cruises'),
	url(r'^admin/users/$', login_required(user_passes_test(lambda u: u.is_superuser)(views.admin_user_view)), name='admin-users'),
	url(r'^admin/users/(?P<pk>[0-9]+)/set_as_admin/$', login_required(user_passes_test(lambda u: u.is_superuser)(views.set_as_admin)), name='user-set-admin'),
	url(r'^admin/users/(?P<pk>[0-9]+)/set_as_external/$', login_required(user_passes_test(lambda u: u.is_superuser)(views.set_as_external)), name='user-set-external'),
	url(r'^admin/users/(?P<pk>[0-9]+)/set_as_internal/$', login_required(user_passes_test(lambda u: u.is_superuser)(views.set_as_internal)), name='user-set-internal'),
	url(r'^admin/users/(?P<pk>[0-9]+)/delete/$', login_required(user_passes_test(lambda u: u.is_superuser)(views.delete_user)), name='user-delete'),
	url(r'^admin/seasons/$', login_required(user_passes_test(lambda u: u.is_superuser)(views.admin_season_view)), name='seasons'),
	url(r'^admin/seasons/(?P<pk>[0-9]+)/edit/$', login_required(user_passes_test(lambda u: u.is_superuser)(SeasonEditView.as_view())), name='season-update'),
	url(r'^admin/seasons/(?P<pk>[0-9]+)/delete/$', login_required(user_passes_test(lambda u: u.is_superuser)(SeasonDeleteView.as_view())), name='season-delete'),
	url(r'^admin/seasons/add/$', login_required(user_passes_test(lambda u: u.is_superuser)(CreateSeason.as_view())), name='add-season'),
	url(r'^admin/events/$', login_required(user_passes_test(lambda u: u.is_superuser)(views.admin_event_view)), name='events'),
	url(r'^admin/events/(?P<pk>[0-9]+)/edit/$', login_required(user_passes_test(lambda u: u.is_superuser)(EventEditView.as_view())), name='event-update'),
	url(r'^admin/events/(?P<pk>[0-9]+)/delete/$', login_required(user_passes_test(lambda u: u.is_superuser)(EventDeleteView.as_view())), name='event-delete'),
	url(r'^admin/events/add/$', login_required(user_passes_test(lambda u: u.is_superuser)(CreateEvent.as_view())), name='add-event'),
	url(r'^admin/notifications/$', login_required(user_passes_test(lambda u: u.is_superuser)(views.admin_notification_view)), name='notifications'),
	url(r'^admin/notifications/(?P<pk>[0-9]+)/edit/$', login_required(user_passes_test(lambda u: u.is_superuser)(NotificationEditView.as_view())), name='notification-update'),
	url(r'^admin/notifications/(?P<pk>[0-9]+)/delete/$', login_required(user_passes_test(lambda u: u.is_superuser)(NotificationDeleteView.as_view())), name='notification-delete'),
	url(r'^admin/notifications/add/$', login_required(user_passes_test(lambda u: u.is_superuser)(CreateNotification.as_view())), name='add-notification'),
	url(r'^admin/food/(?P<pk>\d+)/$', login_required(user_passes_test(lambda u: u.is_superuser)(views.food_view)), name='cruise-food'),
	url(r'^admin/$', login_required(user_passes_test(lambda u: u.is_superuser)(views.admin_view)), name='admin'),
	url(r'^login/$', auth_views.login, {'template_name': 'reserver/authform.html'}, name='login'),
	url(r'^register/$', views.register_view, name='register'),
	url(r'^calendar/', views.calendar_event_source, name='calendar_event_source'),
	url(r'^logout/$', auth_views.logout, {'next_page': 'home'}, name='logout'),
]
