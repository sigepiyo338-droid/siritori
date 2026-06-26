from django.db import models
from django.core.validators import RegexValidator

# ひらがな制限のバリデーター (長音「ー」も許容)
hiragana_validator = RegexValidator(
    regex=r'^[ぁ-んー]+$',
    message='読み方はひらがな（および長音符「ー」）のみで入力してください。',
    code='invalid_hiragana'
)

class GameImage(models.Model):
    image = models.ImageField(
        upload_to='uploads/%Y/%m/%d/',
        verbose_name='画像ファイル'
    )
    is_approved = models.BooleanField(
        default=False,
        verbose_name='承認フラグ',
        help_text='管理者が承認するまでゲーム内には表示されません。'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='登録日時'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新日時'
    )

    class Meta:
        verbose_name = 'ゲーム画像'
        verbose_name_plural = 'ゲーム画像一覧'
        ordering = ['-created_at']

    def __str__(self):
        return f"画像 ID: {self.id} ({self.image.name})"

    @property
    def readings_list(self):
        return [r.reading for r in self.readings.all()]


class ImageReading(models.Model):
    image = models.ForeignKey(
        GameImage,
        on_delete=models.CASCADE,
        related_name='readings',
        verbose_name='対象画像'
    )
    reading = models.CharField(
        max_length=100,
        validators=[hiragana_validator],
        verbose_name='読み方（ひらがな）',
        help_text='しりとり用の読み方をひらがなで入力してください（例: りんご）。'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='登録日時'
    )

    class Meta:
        verbose_name = '画像の読み方'
        verbose_name_plural = '画像の読み方一覧'
        unique_together = ('image', 'reading')
        ordering = ['created_at']

    def __str__(self):
        return f"{self.reading} (画像ID: {self.image.id})"
