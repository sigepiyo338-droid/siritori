from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
import os

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

    def test_image_upload_sets_user(self):
        self.client.login(username=self.username, password=self.password)
        from PIL import Image
        import io
        img_file = io.BytesIO()
        img = Image.new('RGB', (100, 100))
        img.save(img_file, format='PNG')
        img_file.name = 'test_owner.png'
        img_file.seek(0)
        
        response = self.client.post(reverse('shiritori_game:image_upload'), {
            'image': img_file,
            'reading': 'あるじ'
        })
        self.assertRedirects(response, reverse('shiritori_game:game_index'))
        
        from .models import GameImage
        game_image = GameImage.objects.filter(readings__reading='あるじ').last()
        self.assertIsNotNone(game_image)
        self.assertEqual(game_image.user, self.user)

    def test_my_images_view_requires_login(self):
        response = self.client.get(reverse('shiritori_game:my_images'))
        self.assertRedirects(response, reverse('shiritori_game:login') + '?next=' + reverse('shiritori_game:my_images'))

    def test_my_images_view_renders_for_logged_in_user(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('shiritori_game:my_images'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'shiritori_game/my_images.html')

    def test_delete_image_success(self):
        import os
        from django.core.files.uploadedfile import SimpleUploadedFile
        from .models import GameImage, ImageReading
        
        # Create an image uploaded by self.user
        image_file = SimpleUploadedFile("test_delete.png", b"file_content", content_type="image/png")
        game_image = GameImage.objects.create(user=self.user, image=image_file)
        ImageReading.objects.create(image=game_image, reading='てすと')
        
        image_path = game_image.image.path
        self.assertTrue(os.path.exists(image_path))
        
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(reverse('shiritori_game:delete_image', args=[game_image.id]))
        self.assertRedirects(response, reverse('shiritori_game:my_images'))
        
        # Verify deletion from database
        self.assertFalse(GameImage.objects.filter(pk=game_image.id).exists())
        self.assertFalse(ImageReading.objects.filter(image=game_image).exists())
        
        # Verify physical file deletion
        self.assertFalse(os.path.exists(image_path))

    def test_delete_image_unauthorized(self):
        from django.contrib.auth.models import User
        from django.core.files.uploadedfile import SimpleUploadedFile
        from .models import GameImage, ImageReading
        
        # Create another user and an image they uploaded
        other_user = User.objects.create_user(username='otheruser', password='password123')
        image_file = SimpleUploadedFile("test_other.png", b"file_content", content_type="image/png")
        game_image = GameImage.objects.create(user=other_user, image=image_file)
        ImageReading.objects.create(image=game_image, reading='たにん')
        
        # Log in as self.user and try to delete other_user's image
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(reverse('shiritori_game:delete_image', args=[game_image.id]))
        self.assertRedirects(response, reverse('shiritori_game:my_images'))
        
        # Verify image is NOT deleted
        self.assertTrue(GameImage.objects.filter(pk=game_image.id).exists())
        self.assertTrue(ImageReading.objects.filter(image=game_image).exists())
        
        # Clean up other_user's physical file manually
        if game_image.image and os.path.exists(game_image.image.path):
            os.remove(game_image.image.path)






