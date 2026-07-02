from django.contrib import admin
from .models import Post

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'author_name', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('author_name', 'message')

