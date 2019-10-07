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
from django.conf.urls import include
import sys
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.views.static import serve

import reserver.views.cruise as cruise
import reserver.views.misc_views as misc_views
import reserver.views.calendar as calendar
import reserver.views.email_template as email_template
import reserver.views.cruise_receipt as receipts
import reserver.views.settings as system_settings
import reserver.views.email_logs as emails
import reserver.views.notifications as notifications
import reserver.views.announcements as announcements
import reserver.views.events as events
import reserver.views.event_categories as event_categories
import reserver.views.organizations as organizations
import reserver.views.invoices as invoices
import reserver.views.admin_debug as debug
import reserver.views.seasons as seasons
import reserver.views.user_registration as registration
import reserver.views.admin as admin_views
import reserver.views.user_management as user_management
import reserver.views.backup as backup
import reserver.views.user as user

from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from reserver.utils import init, server_starting

#import debug_toolbar

admin.site.site_header = 'R/V Gunnerus'

urlpatterns = [
	url(r'^uploads/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT,}),

	#Misc urls
	url(r'^$', misc_views.index_view, name='home'),
	url(r'^qr/(?P<b64_path>[\=0-9A-Za-z_\-]+)/qr.png$', misc_views.path_to_qr_view, name='path-to-qr'),
	url(r'^login/redirect/$', login_required(user.login_redirect), name='login-redirect'),
	url(r'^login/$', auth_views.login, {'template_name': 'reserver/user/authform.html'}, name='login'),
	url(r'^logout/$', auth_views.logout, {'next_page': 'home'}, name='logout'),
	url(r'^register/$', registration.register_view, name='register'),
	url(r'^calendar/', calendar.calendar_event_source, name='calendar_event_source'),
	url(r'^log/', debug.log_debug_data, name='log-debug-data'),

	#User urls
	url(r'^user/$', login_required(user.CurrentUserView.as_view()), name='user-page'),
	url(r'^user/export/$', login_required(user.export_data_view), name='user-export'),
	url(r'^user/(?P<slug>[\w.@+-]+)/$', login_required(user.UserView.as_view()), name='user-page'),
	url(r'^user/password/reset/$', auth_views.PasswordResetView.as_view(template_name='reserver/user/reset-form.html'), name='reset-form'),
	url(r'^user/activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', registration.activate_view, name='activate'),
	url(r'^user/resend_activation_mail/$', login_required(registration.send_activation_email_view), name='resend-activation-mail'),
	url(r'^user/password/reset/done/$', auth_views.PasswordResetDoneView.as_view(template_name='reserver/user/reset-email-sent.html'), name='password_reset_done'),
	url(r'^user/password/reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', auth_views.PasswordResetConfirmView.as_view(template_name='reserver/user/reset-confirm.html'), name='password_reset_confirm'),
	url(r'^user/password/reset/complete/$', auth_views.PasswordResetCompleteView.as_view(template_name='reserver/user/reset-complete.html'), name='password_reset_complete'),

	#User cruise pages
	url(r'^user/cruises/upcoming/$', login_required(user.upcoming_cruises_view), name='user-upcoming-cruises'),
	url(r'^user/cruises/submitted/$', login_required(user.submitted_cruises_view), name='user-submitted-cruises'),
	url(r'^user/cruises/unsubmitted/$', login_required(user.unsubmitted_cruises_view), name='user-unsubmitted-cruises'),
	url(r'^user/cruises/finished/$', login_required(user.finished_cruises_view), name='user-finished-cruises'),

	#Cruise urls
	url(r'^cruises/add/$', login_required(cruise.CruiseCreateView.as_view()), name='cruise-add'),
	url(r'^cruises/add/from-(?P<start_date>\d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01]))-to-(?P<end_date>\d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01]))$', login_required(cruise.CruiseCreateView.as_view()), name='cruise-add'),
	url(r'^cruises/(?P<pk>[0-9]+)/edit/$', login_required(cruise.CruiseEditView.as_view()), name='cruise-update'),
	url(r'^cruises/(?P<pk>[0-9]+)/edit-billing-type/$', login_required(invoices.UpdateCruiseBillingType.as_view()), name='cruise-update-billing-type'),
	url(r'^cruises/(?P<pk>[0-9]+)/archive/$', login_required(cruise.archive_cruise), name='cruise-archive'),
	url(r'^cruises/(?P<pk>[0-9]+)/cancel/$', login_required(cruise.cancel_cruise), name='cruise-cancel'),
	url(r'^cruises/(?P<pk>[0-9]+)/view/$', login_required(cruise.CruiseView.as_view()), name='cruise-view'),
	url(r'^cruises/(?P<pk>[0-9]+)/pdf/$', login_required(cruise.cruise_pdf_view), name='cruise-pdf-view'),
	url(r'^cruises/(?P<pk>[0-9]+)/submit/$', login_required(cruise.submit_cruise), name='cruise-submit'),
	url(r'^cruises/(?P<pk>[0-9]+)/unsubmit/$', login_required(cruise.unsubmit_cruise), name='cruise-unsubmit'),
	url(r'^cruises/(?P<pk>[0-9]+)/reject/$', login_required(cruise.reject_cruise), name='cruise-reject'),
	url(r'^cruises/(?P<pk>[0-9]+)/approve/$', login_required(cruise.approve_cruise), name='cruise-approve'),
	url(r'^cruises/(?P<pk>[0-9]+)/unapprove/$', login_required(cruise.unapprove_cruise), name='cruise-unapprove'),
	url(r'^cruises/(?P<pk>[0-9]+)/message/$', login_required(cruise.send_cruise_message), name='cruise-message'),
	url(r'^cruises/(?P<pk>[0-9]+)/invoices/$', login_required(invoices.view_cruise_invoices), name='cruise-invoices'),
	url(r'^cruises/(?P<pk>[0-9]+)/add-invoice/$', login_required(invoices.create_additional_cruise_invoice), name='cruise-invoice-add'),
	url(r'^cruises/(?P<pk>[0-9]+)/approve-information/$', login_required(cruise.approve_cruise_information), name='cruise-approve-information'),
	url(r'^cruises/(?P<pk>[0-9]+)/unapprove-information/$', login_required(cruise.unapprove_cruise_information), name='cruise-unapprove-information'),
	url(r'^cruises/(?P<pk>[0-9]+)/add-invoice-item/$', login_required(invoices.CreateListPrice.as_view()), name='add-invoice-item'),
	url(r'^cruises/cost/', receipts.cruise_receipt_source, name='cruise_receipt_source'),

	#Invoice urls
	url(r'^invoices/items/(?P<pk>[0-9]+)/edit/$', login_required(invoices.UpdateListPrice.as_view()), name='edit-invoice-item'),
	url(r'^invoices/items/(?P<pk>[0-9]+)/delete/$', login_required(invoices.DeleteListPrice.as_view()), name='remove-invoice-item'),

	#Admin invoice urls
	url(r'^admin/invoices/$', login_required(user_passes_test(lambda u: u.is_superuser)(invoices.admin_invoice_view)), name='admin-invoices'),
	url(r'^admin/invoices/(?P<pk>[0-9]+)/delete/$', login_required(invoices.InvoiceDeleteView.as_view()), name='invoice-delete'),
	url(r'^admin/invoices/(?P<pk>[0-9]+)/mark-as-sent/$', login_required(invoices.mark_invoice_as_sent), name='invoice-mark-as-sent'),
	url(r'^admin/invoices/(?P<pk>[0-9]+)/mark-as-unsent/$', login_required(invoices.mark_invoice_as_unsent), name='invoice-mark-as-unsent'),
	url(r'^admin/invoices/(?P<pk>[0-9]+)/mark-as-paid/$', login_required(invoices.mark_invoice_as_paid), name='invoice-mark-as-paid'),
	url(r'^admin/invoices/(?P<pk>[0-9]+)/mark-as-unpaid/$', login_required(invoices.mark_invoice_as_unpaid), name='invoice-mark-as-unpaid'),
	url(r'^admin/invoices/(?P<pk>[0-9]+)/reject/$', login_required(invoices.reject_invoice), name='invoice-reject'),
	url(r'^admin/invoices/(?P<pk>[0-9]+)/mark-as-finalized/$', login_required(invoices.mark_invoice_as_finalized), name='invoice-mark-as-finalized'),
	url(r'^admin/invoices/(?P<pk>[0-9]+)/mark-as-unfinalized/$', login_required(invoices.mark_invoice_as_unfinalized), name='invoice-mark-as-unfinalized'),

	#Admin user urls
	url(r'^admin/users/$', login_required(user_passes_test(lambda u: u.is_superuser)(user_management.admin_user_view)), name='admin-users'),
	url(r'^admin/users/(?P<pk>[0-9]+)/edit/$', login_required(user_passes_test(lambda u: u.is_superuser)(user_management.UserDataEditView.as_view())), name='edit-userdata'),
	url(r'^admin/users/(?P<pk>[0-9]+)/set_as_admin/$', login_required(user_passes_test(lambda u: u.is_superuser)(user_management.set_as_admin)), name='user-set-admin'),
	url(r'^admin/users/(?P<pk>[0-9]+)/set_as_external/$', login_required(user_passes_test(lambda u: u.is_superuser)(user_management.set_as_external)), name='user-set-external'),
	url(r'^admin/users/(?P<pk>[0-9]+)/set_as_internal/$', login_required(user_passes_test(lambda u: u.is_superuser)(user_management.set_as_internal)), name='user-set-internal'),
	url(r'^admin/users/(?P<pk>[0-9]+)/set_as_invoicer/$', login_required(user_passes_test(lambda u: u.is_superuser)(user_management.set_as_invoicer)), name='user-set-invoicer'),
	url(r'^admin/users/(?P<pk>[0-9]+)/toggle_crew_status/$', login_required(user_passes_test(lambda u: u.is_superuser)(user_management.toggle_user_crew_status)), name='user-toggle-crew'),
	url(r'^admin/users/(?P<pk>[0-9]+)/delete/$', login_required(user_passes_test(lambda u: u.is_superuser)(user_management.delete_user)), name='user-delete'),

	#Admin season urls
	url(r'^admin/seasons/$', login_required(user_passes_test(lambda u: u.is_superuser)(seasons.admin_season_view)), name='seasons'),
	url(r'^admin/seasons/(?P<pk>[0-9]+)/edit/$', login_required(user_passes_test(lambda u: u.is_superuser)(seasons.SeasonEditView.as_view())), name='season-update'),
	url(r'^admin/seasons/(?P<pk>[0-9]+)/delete/$', login_required(user_passes_test(lambda u: u.is_superuser)(seasons.SeasonDeleteView.as_view())), name='season-delete'),
	url(r'^admin/seasons/add/$', login_required(user_passes_test(lambda u: u.is_superuser)(seasons.CreateSeason.as_view())), name='add-season'),

	#Admin organization urls
	url(r'^admin/organizations/$', login_required(user_passes_test(lambda u: u.is_superuser)(organizations.admin_organization_view)), name='organizations'),
	url(r'^admin/organizations/(?P<pk>[0-9]+)/edit/$', login_required(user_passes_test(lambda u: u.is_superuser)(organizations.OrganizationEditView.as_view())), name='organization-update'),
	url(r'^admin/organizations/(?P<pk>[0-9]+)/delete/$', login_required(user_passes_test(lambda u: u.is_superuser)(organizations.OrganizationDeleteView.as_view())), name='organization-delete'),
	url(r'^admin/organizations/add/$', login_required(user_passes_test(lambda u: u.is_superuser)(organizations.CreateOrganization.as_view())), name='add-organization'),

	#Admin event urls
	url(r'^admin/eventcategories/$', login_required(user_passes_test(lambda u: u.is_superuser)(event_categories.admin_eventcategory_view)), name='eventcategories'),
	url(r'^admin/eventcategories/(?P<pk>[0-9]+)/edit/$', login_required(user_passes_test(lambda u: u.is_superuser)(event_categories.EventCategoryEditView.as_view())), name='eventcategory-update'),
	url(r'^admin/eventcategories/(?P<pk>[0-9]+)/reset_event_category/$', login_required(user_passes_test(lambda u: u.is_superuser)(event_categories.event_category_reset_view)), name='eventcategory-reset'),
	url(r'^admin/eventcategories/(?P<pk>[0-9]+)/delete/$', login_required(user_passes_test(lambda u: u.is_superuser)(event_categories.EventCategoryDeleteView.as_view())), name='eventcategory-delete'),
	url(r'^admin/eventcategories/add/$', login_required(user_passes_test(lambda u: u.is_superuser)(event_categories.CreateEventCategory.as_view())), name='add-eventcategory'),
	url(r'^admin/events/$', login_required(user_passes_test(lambda u: u.is_superuser)(events.admin_event_view)), name='events'),
	url(r'^admin/events/(?P<pk>[0-9]+)/edit/$', login_required(user_passes_test(lambda u: u.is_superuser)(events.EventEditView.as_view())), name='event-update'),
	url(r'^admin/events/(?P<pk>[0-9]+)/delete/$', login_required(user_passes_test(lambda u: u.is_superuser)(events.EventDeleteView.as_view())), name='event-delete'),
	url(r'^admin/events/add/$', login_required(user_passes_test(lambda u: u.is_superuser)(events.CreateEvent.as_view())), name='add-event'),
	url(r'^admin/events/add/from-(?P<start_date>\d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01]))-to-(?P<end_date>\d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01]))$', login_required(user_passes_test(lambda u: u.is_superuser)(events.CreateEvent.as_view())), name='add-event'),
	url(r'^admin/events/overview/$', login_required(events.event_overview), name='period-overview'),
	url(r'^admin/events/overview/from-(?P<start_date>\d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01]))-to-(?P<end_date>\d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01]))$', login_required(events.event_overview), name='overview-for-period'),
	url(r'^admin/events/overview/pdf/$', login_required(events.event_overview_pdf), name='pdf-overview'),
	url(r'^admin/events/overview/from-(?P<start_date>\d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01]))-to-(?P<end_date>\d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01]))/pdf/$', login_required(events.event_overview_pdf), name='pdf-overview-for-period'),

	#Admin announcement urls
	url(r'^admin/announcements/$', login_required(user_passes_test(lambda u: u.is_superuser)(announcements.admin_announcements_view)), name='announcements'),
	url(r'^admin/announcements/(?P<pk>[0-9]+)/edit/$', login_required(user_passes_test(lambda u: u.is_superuser)(announcements.AnnouncementEditView.as_view())), name='announcement-update'),
	url(r'^admin/announcements/(?P<pk>[0-9]+)/delete/$', login_required(user_passes_test(lambda u: u.is_superuser)(announcements.AnnouncementDeleteView.as_view())), name='announcement-delete'),
	url(r'^admin/announcements/add/$', login_required(user_passes_test(lambda u: u.is_superuser)(announcements.CreateAnnouncement.as_view())), name='add-announcement'),

	#Admin notification urls
	url(r'^admin/notifications/$', login_required(user_passes_test(lambda u: u.is_superuser)(notifications.admin_notification_view)), name='notifications'),
	url(r'^admin/notifications/(?P<pk>[0-9]+)/edit_notification/$', login_required(user_passes_test(lambda u: u.is_superuser)(notifications.NotificationEditView.as_view())), name='notification-update'),
	url(r'^admin/notifications/(?P<pk>[0-9]+)/delete_notification/$', login_required(user_passes_test(lambda u: u.is_superuser)(notifications.NotificationDeleteView.as_view())), name='notification-delete'),
	url(r'^admin/notifications/add_notification/$', login_required(user_passes_test(lambda u: u.is_superuser)(notifications.CreateNotification.as_view())), name='add-notification'),
	url(r'^admin/notifications/(?P<pk>[0-9]+)/edit_email_template/$', login_required(user_passes_test(lambda u: u.is_superuser)(email_template.EmailTemplateEditView.as_view())), name='email-template-update'),
	url(r'^admin/notifications/(?P<pk>[0-9]+)/reset_email_template/$', login_required(user_passes_test(lambda u: u.is_superuser)(email_template.email_template_reset_view)), name='email-template-reset'),
	url(r'^admin/notifications/(?P<pk>[0-9]+)/delete_email_template/$', login_required(user_passes_test(lambda u: u.is_superuser)(email_template.EmailTemplateDeleteView.as_view())), name='email-template-delete'),
	url(r'^admin/notifications/add_email_template/$', login_required(user_passes_test(lambda u: u.is_superuser)(email_template.CreateEmailTemplate.as_view())), name='add-email-template'),

	#Admin email urls
	url(r'^admin/emails/$', login_required(user_passes_test(lambda u: u.is_superuser)(emails.view_email_logs)), name='email_list_view'),
	url(r'^admin/emails/test/$', login_required(user_passes_test(lambda u: u.is_superuser)(emails.test_email_view)), name='send_test_email_view'),
	url(r'^admin/emails/purge/$', login_required(user_passes_test(lambda u: u.is_superuser)(emails.purge_email_logs)), name='email_purge_view'),

	#Misc admin urls
	url(r'^admin/$', login_required(user_passes_test(lambda u: u.is_superuser)(admin_views.admin_view)), name='admin'),
	url(r'^admin/hours/$', login_required(user_passes_test(lambda u: u.is_superuser)(admin_views.admin_work_hour_view)), name='hours'),
	url(r'^admin/hours/for-(?P<year>\d{4})$', login_required(user_passes_test(lambda u: u.is_superuser)(admin_views.admin_work_hour_view)), name='hours-for-period'),
	url(r'^admin/cruises/$', login_required(user_passes_test(lambda u: u.is_superuser)(admin_views.admin_cruise_view)), name='admin-cruises'),
	url(r'^admin/actions/$', login_required(user_passes_test(lambda u: u.is_superuser)(admin_views.admin_actions_view)), name='admin-actions'),
	url(r'^admin/statistics/$', login_required(user_passes_test(lambda u: u.is_superuser)(admin_views.admin_statistics_view)), name='admin-statistics'),
	url(r'^admin/django/', admin.site.urls, name='django-admin'),
	url(r'^admin/settings/$', login_required(user_passes_test(lambda u: u.is_superuser)(system_settings.SettingsEditView.as_view())), name='settings'),
	url(r'^admin/food/(?P<pk>\d+)/$', login_required(user_passes_test(lambda u: u.is_superuser)(admin_views.food_view)), name='cruise-food'),
	url(r'^admin/debug/view/', debug.admin_debug_view, name='view-debug-data'),
	url(r'^admin/backup/$', login_required(user_passes_test(lambda u: u.is_superuser)(backup.backup_view)), name='backup-view'),
	url(r'^hijack/', include('hijack.urls')),

	#Invoice urls
	url(r'^invoices/overview/$', login_required(invoices.invoicer_overview), name='invoicer-overview'),
	url(r'^invoices/history/$', login_required(invoices.invoice_history), name='invoices-search'),
	url(r'^invoices/new_standalone/$', login_required(user_passes_test(lambda u: u.is_superuser)(invoices.CreateStandaloneInvoice.as_view())), name='add-standalone-invoice'),
	url(r'^invoices/(?P<pk>[0-9]+)/edit_standalone_invoice/$', login_required(user_passes_test(lambda u: u.is_superuser)(invoices.EditStandaloneInvoice.as_view())), name='standalone-invoice-edit'),
	url(r'^invoices/history/from-(?P<start_date>\d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01]))-to-(?P<end_date>\d{4}\-(0?[1-9]|1[012])\-(0?[1-9]|[12][0-9]|3[01]))$', login_required(invoices.invoice_history), name='invoices-for-period'),
#	url(r'^__debug__/', include(debug_toolbar.urls)),
]

if server_starting():
	# we don't want to run this during a migration.
	print("Initializing server...")
	init()
	print("Server initialized")
