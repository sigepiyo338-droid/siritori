from django.urls import path
from . import views

app_name = 'board'

urlpatterns = [
    path('', views.board_list, name='board_list'),
    path('delete/<int:post_id>/', views.post_delete, name='post_delete'),
]
