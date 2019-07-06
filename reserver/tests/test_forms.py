from django.urls import reverse
from django.test.utils import setup_test_environment
from django.test import Client
from django.test import TestCase
from django.contrib.auth.models import User
from reserver.models import Cruise, CruiseDay, UserData
from reserver.forms import CruiseDayForm
from reserver.utils import init
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
		print(self.cruise, file=sys.stderr)
		self.assertTrue(form.is_valid())
		print(form.errors, file=sys.stderr)
		cruiseday = form.save()
		self.assertEqual(CruiseDay.objects.get(pk=cruiseday.pk).description, form.cleaned_data['description'])