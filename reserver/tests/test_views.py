from django.urls import reverse
from django.test.utils import setup_test_environment
from django.test import Client
from django.test import TestCase
from django.contrib.auth.models import User
from reserver.models import UserData

ADMIN_CREDENTIALS = {
        'username': 'testadmin',
        'password': 'secret',
        'email': 'test@test.test'
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
		#self.assertQuerysetEqual(response.context['latest_question_list'], [])

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


		