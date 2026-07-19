from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from .models import GameImage, ImageReading, UserReadingCompletion

class ImageReadingInline(admin.TabularInline):
    model = ImageReading
    extra = 1  # デフォルトで追加用フォームを1つ表示

@admin.register(GameImage)
class GameImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'image', 'user', 'is_approved', 'readings_summary', 'created_at', 'remarks')
    list_filter = ('is_approved', 'created_at')
    list_editable = ('is_approved',)  # リスト画面から直接承認状態を変更できるようにする
    inlines = [ImageReadingInline]
    search_fields = ('readings__reading', 'user__username')

    def readings_summary(self, obj):
        # 紐づく読み方をカンマ区切りで表示するヘルパー
        return ", ".join(obj.readings_display_list)
    readings_summary.short_description = '登録されている読み方'

@admin.register(ImageReading)
class ImageReadingAdmin(admin.ModelAdmin):
    list_display = ('id', 'image', 'reading', 'display_name', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('reading', 'image__id')

@admin.register(UserReadingCompletion)
class UserReadingCompletionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'reading_name', 'image_id', 'created_at')
    list_filter = ('created_at', 'user')
    search_fields = ('user__username', 'reading__reading', 'reading__image__id')

    def reading_name(self, obj):
        return obj.reading.reading
    reading_name.short_description = '読み方'

    def image_id(self, obj):
        return obj.reading.image.id
    image_id.short_description = '画像ID'

# --- Userモデルのカスタマイズ ---
# 「名 (first_name)」のラベルを「ニックネーム」に変更
User._meta.get_field('first_name').verbose_name = 'ニックネーム'


# デフォルトのUserAdminの登録を解除
admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # 「姓 (last_name)」を表示しないように fieldsets を上書き
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'email')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    # 一覧表示からも last_name を除外し、first_name に差し替え
    list_display = ('username', 'email', 'first_name', 'is_staff')
    search_fields = ('username', 'first_name', 'email')
