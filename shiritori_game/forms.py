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
        max_length=200,
        help_text='しりとり用の読み方をひらがなで入力してください（最大5個。複数の場合はカンマ「,」や「、」で区切ってください。例: りんご, らいおん）。<br>'
                  '表示名（名前）を設定したい場合は「ひらがな:表示名」のようにコロンで繋いで入力してください（例: りんご:林檎, あっぷる:Apple, ごりら）。',
        widget=forms.TextInput(attrs={
            'placeholder': '例: りんご:林檎, あっぷる:Apple, ごりら',
            'autocomplete': 'off'
        })
    )

    def clean_reading(self):
        reading_text = self.cleaned_data.get('reading', '')
        
        # カンマ「,」「，」や読点「、」で分割
        import re
        raw_readings = [r.strip() for r in re.split(r'[,，、]', reading_text) if r.strip()]
        
        if not raw_readings:
            raise forms.ValidationError('読み方を入力してください。')
            
        if len(raw_readings) > 5:
            raise forms.ValidationError('読み方は1枚の画像に対して最大5個までしか登録できません。')
            
        parsed_readings = []
        from django.core.exceptions import ValidationError
        
        for item in raw_readings:
            # コロン「:」「：」で読み方と表示名に分割
            parts = re.split(r'[:：]', item, maxsplit=1)
            reading = parts[0].strip()
            display_name = parts[1].strip() if len(parts) > 1 else ''
            
            if not reading:
                raise forms.ValidationError('読み方が空欄になっている項目があります。')
                
            try:
                hiragana_validator(reading)
            except ValidationError:
                raise forms.ValidationError(f'読み方「{reading}」はひらがな（および長音符「ー」）のみで入力してください。')
                
            parsed_readings.append((reading, display_name if display_name else None))
                
        return parsed_readings

    class Meta:
        model = GameImage
        fields = ['image', 'remarks']
        widgets = {
            'remarks': forms.Textarea(attrs={
                'placeholder': '画像の出典や補足情報などがあればご記入ください（任意）',
                'rows': 3,
            })
        }
