from django.urls import reverse
from django.test.utils import setup_test_environment
from django.test import Client
from django.test import TestCase
from django.contrib.auth.models import User
from reserver.models import UserData
import io
from contextlib import redirect_stdout
from reserver.utils import check_default_models
from django.core.urlresolvers import get_resolver
from django.urls import NoReverseMatch

ADMIN_CREDENTIALS = {
		'username': 'testadmin',
		'password': 'secret',
		'email': 'test@example.net'
}

USER_CREDENTIALS = {
		'username': 'testuser',
		'password': 'secret'
}

class ViewTests(TestCase):
	def test_index_view_works(self):
		"""
		Index view returns a 200 status code with the expected content
		"""
		response = self.client.get(reverse('home'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "R/V Gunnerus")

	def test_admin_view_not_accessible_nologin(self):
		"""
		Index view returns a 302 status code with the expected content
		"""
		response = self.client.get(reverse('admin'))
		self.assertEqual(response.status_code, 302)
		response = self.client.get(reverse('admin'), follow=True)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Login")
		#self.assertQuerysetEqual(response.context['latest_question_list'], [])

class AdminViewTests(TestCase):
	def setUp(self):
		trap = io.StringIO()
		with redirect_stdout(trap):
			check_default_models()
		admin_user = User.objects.create_superuser(**ADMIN_CREDENTIALS)
		user_data = UserData()
		user_data.user = admin_user
		user_data.save()
		self.client.post(reverse('login'), ADMIN_CREDENTIALS, follow=True)

	def test_views_work(self):
		"""
		Views return a 200 status code with the expected content
		"""
		ok_count = 0
		total_count = 0
		urls = get_resolver(None).reverse_dict.keys()
		print("\n\nTesting views")
		for url in urls:
			if isinstance(url, str):
				try:
					response = self.client.get(reverse(url))
					self.assertEqual(response.status_code, 200)
					print("Tested ok: " + url)
					ok_count += 1
					total_count += 1
				except Exception as ex:
					if not isinstance(ex, NoReverseMatch):
						print("\n!!! Could not load " + url + " due to " + str(ex) + "\n")
						total_count += 1
					else:
						print("(Needs own test view with URL parameters: " + url + ")")
		print(str(ok_count) + "/" + str(total_count) + " views ok")

	def test_index_view_works(self):
		"""
		Index view returns a 200 status code with the expected content
		"""
		response = self.client.get(reverse('home'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "R/V Gunnerus")

	def test_admin_view_works(self):
		"""
		Admin overview returns a 200 status code with the expected content
		"""
		response = self.client.get(reverse('admin'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Internal days remaining")

	def test_admin_events_view_works(self):
		"""
		Admin overview returns a 200 status code with the expected content
		"""
		response = self.client.get(reverse('events'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Events")

	def test_admin_work_hours_view_works(self):
		"""
		Admin work hour view returns a 200 status code with the expected content
		"""
		response = self.client.get(reverse('hours'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Work hours")

	def test_admin_statistics_view_works(self):
		"""
		Admin statistics view returns a 200 status code with the expected content
		"""
		response = self.client.get(reverse('admin-statistics'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Statistics")

	def test_admin_settings_view_works(self):
		"""
		Admin settings view returns a 200 status code with the expected content
		"""
		response = self.client.get(reverse('settings'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "System settings")

	def test_admin_announcements_view_works(self):
		"""
		Admin overview returns a 200 status code with the expected content
		"""
		response = self.client.get(reverse('announcements'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Announcements")

class AuthenticationTests(TestCase):
	def setUp(self):
		user = User.objects.create_user(**USER_CREDENTIALS)
		user_data = UserData()
		user_data.user = user
		user_data.save()

		admin_user = User.objects.create_superuser(**ADMIN_CREDENTIALS)
		user_data = UserData()
		user_data.user = admin_user
		user_data.save()

	def test_login(self):
		response = self.client.post(reverse('login'), USER_CREDENTIALS, follow=True)
		self.assertTrue(response.context['user'].is_authenticated)

	def test_admin_login(self):
		response = self.client.post(reverse('login'), ADMIN_CREDENTIALS, follow=True)
		self.assertTrue(response.context['user'].is_authenticated)

	def test_logout(self):
		response = self.client.post(reverse('logout'), follow=True)
		self.assertFalse(response.context['user'].is_authenticated)

	def test_get_admin_as_user(self):
		self.test_logout()
		self.test_login()
		response = self.client.get(reverse('admin'))
		self.assertEqual(response.status_code, 302)

	def test_get_admin_as_admin(self):
		self.test_logout()
		self.test_admin_login()
		response = self.client.get(reverse('admin'))
		self.assertEqual(response.status_code, 200)