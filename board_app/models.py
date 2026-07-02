from django.db import models
from django.contrib.auth.models import User

class Post(models.Model):
    author_name = models.CharField(max_length=50, blank=True, verbose_name='投稿者名')
    message = models.TextField(verbose_name='メッセージ')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='ユーザー')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='投稿日時')

    class Meta:
        verbose_name = '投稿'
        verbose_name_plural = '投稿一覧'
        ordering = ['-created_at']

    def __str__(self):
        name = self.author_name if self.author_name else "名無しさん"
        return f"{name} の投稿 ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

