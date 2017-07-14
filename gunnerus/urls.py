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
from reserver.views import CruiseList, CruiseCreateView, CruiseEditView, CruiseDeleteView, UserView, CurrentUserView, submit_cruise, unsubmit_cruise
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test

app_name = 'reserver'

urlpatterns = [
    url(r'^admin/django/', admin.site.urls),
	url(r'cruises/add/$', login_required(CruiseCreateView.as_view()), name='cruise-add'),
    url(r'cruises/(?P<pk>[0-9]+)/$', login_required(CruiseEditView.as_view()), name='cruise-update'),
    url(r'cruises/(?P<pk>[0-9]+)/delete/$', login_required(CruiseDeleteView.as_view()), name='cruise-delete'),
    url(r'cruises/(?P<pk>[0-9]+)/submit/$', login_required(views.submit_cruise), name='cruise-submit'),
    url(r'cruises/(?P<pk>[0-9]+)/unsubmit/$', login_required(views.unsubmit_cruise), name='cruise-unsubmit'),
	url(r'^cruises/', login_required(CruiseList.as_view()), name='cruise-list'),
	url(r'^user/$', login_required(CurrentUserView.as_view()), name='user-page'),
	url(r'^user/(?P<slug>[\w.@+-]+)/$', login_required(UserView.as_view()), name='user-page'),
	url(r'^$', views.index_view, name='home'), 
	url(r'^admin/cruises/', login_required(user_passes_test(lambda u: u.is_superuser)(views.admin_cruise_view))),
	url(r'^admin/users/', login_required(user_passes_test(lambda u: u.is_superuser)(views.admin_user_view))),
	url(r'^admin/food/(?P<pk>\d+)/$', login_required(user_passes_test(lambda u: u.is_superuser)(views.food_view)), name='cruise_food'),
	url(r'^admin/', login_required(user_passes_test(lambda u: u.is_superuser)(views.admin_view))),
	url(r'^login/$', auth_views.login, {'template_name': 'reserver/authform.html'}, name='login'),
	url(r'^register/$', views.signup_view, name='register'),
	url(r'^calendar/', views.calendar_event_source, name='calendar_event_source'),
	url(r'^logout/$', auth_views.logout, {'next_page': 'home'}, name='logout'),
]
