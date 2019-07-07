from django.urls import reverse
from django.test.utils import setup_test_environment
from django.test import Client
from django.test import TestCase
from django.contrib.auth.models import User
from datetime import datetime
from reserver.models import Cruise, CruiseDay, UserData, Organization, Season
from reserver.forms import CruiseDayForm, OrganizationForm, SeasonForm
from reserver.utils import init
from reserver.tests.setup import create_initial_test_models
from django.core.exceptions import ValidationError
import sys
import io
from contextlib import redirect_stdout

USER_CREDENTIALS = {
		'username': 'testuser',
		'password': 'secret'
}

class CruiseDayTests(TestCase):
	def setUp(self):
		trap = io.StringIO()
		with redirect_stdout(trap):
			init()
		user = User.objects.create_user(**USER_CREDENTIALS)
		user_data = UserData()
		user_data.user = user
		user_data.save()
		cruise = Cruise(leader=user)
		cruise.save()
		self.cruise = cruise

	def test_cruiseday_form(self):
		form = CruiseDayForm(data={'description': 'hello', 'date': '2019-01-01', 'cruise': self.cruise.pk})
		self.assertTrue(form.is_valid())
		cruiseday = form.save()
		self.assertEqual(CruiseDay.objects.get(pk=cruiseday.pk).description, form.cleaned_data['description'])

class OrganizationTests(TestCase):
	def test_organization_form(self):
		form = OrganizationForm(data={'name':"form test org", 'is_NTNU':False})
		self.assertTrue(form.is_valid())
		organization = form.save()
		self.assertEqual(Organization.objects.get(pk=organization.pk).name, form.cleaned_data['name'])

class SeasonTests(TestCase):
	def test_no_season_order_events(self):
		form = SeasonForm(data={
			'name':"test season",
			'season_event_start_date':datetime(2019, 10, 1, 8),
			'season_event_end_date':datetime(2020, 3, 31, 20)})
		self.assertFalse(form.is_valid())

	def test_no_season_end(self):
		form = SeasonForm(data={
			'name':"test season",
			'season_event_start_date':datetime(2019, 10, 1, 8),
			'internal_order_event_date':datetime(2019, 7, 1, 8),
			'external_order_event_date':datetime(2019, 8, 1, 8)})

	def test_season_end_before_season_start(self):
		form = SeasonForm(data={
			'name':"test season",
			'season_event_start_date':datetime(2019, 10, 1, 8),
			'season_event_end_date':datetime(2020, 3, 31, 20),
			'internal_order_event_date':datetime(2019, 7, 1, 8),
			'external_order_event_date':datetime(2019, 8, 1, 8)})
		self.assertFalse(form.is_valid())
