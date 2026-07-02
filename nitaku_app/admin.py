from django.contrib import admin
from .models import Questions, Personalities, Answers, Scores

@admin.register(Questions)
class QuestionsAdmin(admin.ModelAdmin):
    list_display = ('id', 'text', 'option_a', 'option_b', 'author', 'posted_by')
    search_fields = ('text', 'author', 'posted_by')

@admin.register(Personalities)
class PersonalitiesAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'label', 'author')
    search_fields = ('name', 'author')

@admin.register(Answers)
class AnswersAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'choice')

@admin.register(Scores)
class ScoresAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'personality', 'option', 'count')
