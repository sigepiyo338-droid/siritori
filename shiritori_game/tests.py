from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

class AuthViewsTestCase(TestCase):
    def setUp(self):
        # Create a test user
        self.username = 'testuser'
        self.password = 'testpass123'
        self.user = User.objects.create_user(username=self.username, password=self.password)

    def test_login_page_renders(self):
        response = self.client.get(reverse('shiritori_game:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shiritori_game/login.html')

    def test_login_success(self):
        response = self.client.post(reverse('shiritori_game:login'), {
            'username': self.username,
            'password': self.password
        })
        self.assertRedirects(response, reverse('shiritori_game:game_index'))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_failure(self):
        response = self.client.post(reverse('shiritori_game:login'), {
            'username': self.username,
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        # Verify the form has errors
        form = response.context['form']
        self.assertTrue(form.errors)

    def test_logout(self):
        # Log in first
        self.client.login(username=self.username, password=self.password)
        # Log out
        response = self.client.get(reverse('shiritori_game:logout'))
        self.assertRedirects(response, reverse('shiritori_game:game_index'))
        # Check that user is logged out
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_upload_page_requires_login(self):
        response = self.client.get(reverse('shiritori_game:image_upload'))
        self.assertRedirects(response, reverse('shiritori_game:login') + '?next=' + reverse('shiritori_game:image_upload'))

    def test_upload_page_renders_when_logged_in(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('shiritori_game:image_upload'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shiritori_game/upload.html')


