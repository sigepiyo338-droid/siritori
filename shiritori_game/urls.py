from django.urls import path
from . import views

app_name = 'shiritori_game'

urlpatterns = [
    path('', views.game_index, name='game_index'),
    path('api/images/', views.image_list_api, name='image_list_api'),
]
