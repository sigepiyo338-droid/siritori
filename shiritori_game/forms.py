from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import GameImage, ImageReading
from .models import hiragana_validator


class UserRegistrationForm(UserCreationForm):
    """新規ユーザー登録フォーム"""
    email = forms.EmailField(
        required=False,
        label='メールアドレス（任意）',
        widget=forms.EmailInput(attrs={
            'placeholder': 'example@email.com',
            'autocomplete': 'email',
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ウィジェット属性をカスタマイズ
        self.fields['username'].widget.attrs.update({
            'placeholder': '半角英数字・@/./+/-/_ のみ使用可',
            'autocomplete': 'username',
        })
        self.fields['password1'].widget.attrs.update({
            'placeholder': '8文字以上のパスワード',
            'autocomplete': 'new-password',
        })
        self.fields['password2'].widget.attrs.update({
            'placeholder': 'パスワードをもう一度入力',
            'autocomplete': 'new-password',
        })

class ImageUploadForm(forms.ModelForm):
    field_order = ['image', 'reading', 'remarks']
    
    reading = forms.CharField(
        label='読み方（ひらがな）',
        max_length=100,
        help_text='しりとり用の読み方をひらがなで入力してください（最大5個。複数の場合はカンマ「,」や「、」で区切ってください。例: りんご, らいおん）。',
        widget=forms.TextInput(attrs={
            'placeholder': '例: りんご, らいおん',
            'autocomplete': 'off'
        })
    )

    def clean_reading(self):
        reading_text = self.cleaned_data.get('reading', '')
        
        # カンマ「,」「，」や読点「、」で分割
        import re
        readings = [r.strip() for r in re.split(r'[,，、]', reading_text) if r.strip()]
        
        if not readings:
            raise forms.ValidationError('読み方を入力してください。')
            
        if len(readings) > 5:
            raise forms.ValidationError('読み方は1枚の画像に対して最大5個までしか登録できません。')
            
        # 各読み方がひらがなのみか検証
        from django.core.exceptions import ValidationError
        for reading in readings:
            try:
                hiragana_validator(reading)
            except ValidationError:
                raise forms.ValidationError(f'読み方「{reading}」はひらがな（および長音符「ー」）のみで入力してください。')
                
        return readings

    class Meta:
        model = GameImage
        fields = ['image', 'remarks']
        widgets = {
            'remarks': forms.Textarea(attrs={
                'placeholder': '画像の出典や補足情報などがあればご記入ください（任意）',
                'rows': 3,
            })
        }
