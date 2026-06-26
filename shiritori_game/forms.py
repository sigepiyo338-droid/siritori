from django import forms
from .models import GameImage, ImageReading
from .models import hiragana_validator

class ImageUploadForm(forms.ModelForm):
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
        fields = ['image']
