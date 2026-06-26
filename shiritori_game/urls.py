from django.urls import path
from . import views

app_name = 'shiritori_game'

urlpatterns = [
    path('', views.game_index, name='game_index'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('upload/', views.image_upload, name='image_upload'),
    path('api/images/', views.image_list_api, name='image_list_api'),
]
