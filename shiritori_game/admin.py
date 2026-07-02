from django.contrib import admin
from .models import GameImage, ImageReading

class ImageReadingInline(admin.TabularInline):
    model = ImageReading
    extra = 1  # デフォルトで追加用フォームを1つ表示

@admin.register(GameImage)
class GameImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'image', 'user', 'is_approved', 'readings_summary', 'created_at')
    list_filter = ('is_approved', 'created_at')
    list_editable = ('is_approved',)  # リスト画面から直接承認状態を変更できるようにする
    inlines = [ImageReadingInline]
    search_fields = ('readings__reading', 'user__username')

    def readings_summary(self, obj):
        # 紐づく読み方をカンマ区切りで表示するヘルパー
        return ", ".join(obj.readings_list)
    readings_summary.short_description = '登録されている読み方'

@admin.register(ImageReading)
class ImageReadingAdmin(admin.ModelAdmin):
    list_display = ('id', 'image', 'reading', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('reading', 'image__id')
