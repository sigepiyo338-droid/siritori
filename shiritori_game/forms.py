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
        label='読み方・表示名',
        max_length=2000,
        required=False,
        help_text='しりとり用の読み方をひらがなで入力してください（最大5個まで追加可能）。<br>'
                  '表示名を入力すると、ゲーム内でその名前が表示されます。',
    )

    def clean_reading(self):
        reading_text = self.cleaned_data.get('reading', '')
        
        if not reading_text:
            raise forms.ValidationError('読み方を入力してください。')

        import json
        from django.core.exceptions import ValidationError
        
        try:
            raw_data = json.loads(reading_text)
        except Exception:
            raise forms.ValidationError('データの形式が不正です。')
            
        if not isinstance(raw_data, list) or not raw_data:
            raise forms.ValidationError('読み方を入力してください。')
            
        if len(raw_data) > 5:
            raise forms.ValidationError('読み方は1枚の画像に対して最大5個までしか登録できません。')
            
        parsed_readings = []
        
        for item in raw_data:
            if not isinstance(item, dict):
                continue
            reading = item.get('reading', '').strip()
            display_name = item.get('display_name', '').strip()
            
            if not reading:
                raise forms.ValidationError('読み方が空欄になっている項目があります。')
                
            try:
                hiragana_validator(reading)
            except ValidationError:
                raise forms.ValidationError(f'読み方「{reading}」はひらがな（および長音符「ー」）のみで入力してください。')
                
            parsed_readings.append((reading, display_name if display_name else None))
            
        if not parsed_readings:
            raise forms.ValidationError('有効な読み方が入力されていません。')
            
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


class ImageEditForm(ImageUploadForm):
    """画像付随情報編集用フォーム（画像ファイルは変更不可）"""
    field_order = ['reading', 'remarks']
    
    class Meta(ImageUploadForm.Meta):
        fields = ['remarks']
