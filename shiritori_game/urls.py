from django.urls import path
from . import views

app_name = 'shiritori_game'

urlpatterns = [
    path('', views.game_index, name='game_index'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.user_register, name='register'),
    path('upload/', views.image_upload, name='image_upload'),
    path('my-images/', views.my_images, name='my_images'),
    path('my-images/delete/<int:image_id>/', views.delete_image, name='delete_image'),
    path('my-images/edit/<int:image_id>/', views.edit_image, name='edit_image'),
    path('api/images/', views.image_list_api, name='image_list_api'),
    path('settings/', views.game_settings, name='game_settings'),
    path('management/', views.post_management, name='post_management'),
    path('account/', views.account_settings, name='account_settings'),
]
