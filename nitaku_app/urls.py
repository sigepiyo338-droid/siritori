from django.urls import path
from . import views

app_name = 'nitaku_app'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/personalities', views.get_personalities, name='get_personalities'),
    path('api/questions', views.get_questions, name='get_questions'),
    path('api/post/question', views.post_question, name='post_question'),
    path('api/post/personality', views.post_personality, name='post_personality'),
    path('api/answer', views.submit_answer, name='submit_answer'),
    path('api/radar-scores', views.radar_scores, name='radar_scores'),
    path('api/my_questions', views.my_questions, name='my_questions'),
    path('api/delete/question/<int:question_id>', views.delete_question, name='delete_question'),
    path('api/my_personalities', views.my_personalities, name='my_personalities'),
    path('api/delete/personality/<int:personality_id>', views.delete_personality, name='delete_personality'),
]
