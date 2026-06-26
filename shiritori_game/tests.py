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

    def test_image_upload_processing(self):
        # Log in first
        self.client.login(username=self.username, password=self.password)
        
        # 1. 600pxより大きい画像をテスト (1200 x 800 -> 800 x 800にクロップ -> 600 x 600に縮小)
        from PIL import Image
        import io
        img_file1 = io.BytesIO()
        img1 = Image.new('RGB', (1200, 800), color='blue')
        img1.save(img_file1, format='PNG')
        img_file1.name = 'test_image_large.png'
        img_file1.seek(0)
        
        response1 = self.client.post(reverse('shiritori_game:image_upload'), {
            'image': img_file1,
            'reading': 'てすと'
        })
        self.assertRedirects(response1, reverse('shiritori_game:game_index'))
        
        from .models import GameImage
        game_image1 = GameImage.objects.filter(readings__reading='てすと').last()
        self.assertIsNotNone(game_image1)
        saved_img1 = Image.open(game_image1.image.path)
        self.assertEqual(saved_img1.size, (600, 600))

        # 2. 600pxより小さい画像をテスト (400 x 300 -> 300 x 300にクロップ -> 縮小せずそのまま保存)
        img_file2 = io.BytesIO()
        img2 = Image.new('RGB', (400, 300), color='red')
        img2.save(img_file2, format='PNG')
        img_file2.name = 'test_image_small.png'
        img_file2.seek(0)
        
        response2 = self.client.post(reverse('shiritori_game:image_upload'), {
            'image': img_file2,
            'reading': 'ちいさい'
        })
        self.assertRedirects(response2, reverse('shiritori_game:game_index'))
        
        game_image2 = GameImage.objects.filter(readings__reading='ちいさい').last()
        self.assertIsNotNone(game_image2)
        saved_img2 = Image.open(game_image2.image.path)
        self.assertEqual(saved_img2.size, (300, 300))

    def test_upload_readings_limit_ok(self):
        self.client.login(username=self.username, password=self.password)
        from PIL import Image
        import io
        img_file = io.BytesIO()
        img = Image.new('RGB', (100, 100))
        img.save(img_file, format='PNG')
        img_file.name = 'test.png'
        img_file.seek(0)
        
        response = self.client.post(reverse('shiritori_game:image_upload'), {
            'image': img_file,
            'reading': 'いち, に, さん, よん, ご'
        })
        self.assertRedirects(response, reverse('shiritori_game:game_index'))
        
        from .models import GameImage
        game_image = GameImage.objects.last()
        self.assertEqual(game_image.readings.count(), 5)

    def test_upload_readings_limit_fail(self):
        self.client.login(username=self.username, password=self.password)
        from PIL import Image
        import io
        img_file = io.BytesIO()
        img = Image.new('RGB', (100, 100))
        img.save(img_file, format='PNG')
        img_file.name = 'test.png'
        img_file.seek(0)
        
        response = self.client.post(reverse('shiritori_game:image_upload'), {
            'image': img_file,
            'reading': 'いち, に, さん, よん, ご, ろく'
        })
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertTrue(form.errors)
        self.assertIn('reading', form.errors)

    def test_model_readings_limit_fail(self):
        from .models import GameImage, ImageReading
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.core.exceptions import ValidationError
        
        # Create GameImage
        image_file = SimpleUploadedFile("test.png", b"file_content", content_type="image/png")
        game_image = GameImage.objects.create(image=image_file)
        
        # Add 5 readings
        for i in range(5):
            ImageReading.objects.create(image=game_image, reading=f'よみ{i}')
            
        # Attempt to add a 6th reading
        new_reading = ImageReading(image=game_image, reading='よみろく')
        with self.assertRaises(ValidationError):
            new_reading.full_clean()





