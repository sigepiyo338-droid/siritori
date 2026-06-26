from django import forms
from .models import GameImage, ImageReading
from .models import hiragana_validator

class ImageUploadForm(forms.ModelForm):
    reading = forms.CharField(
        label='読み方（ひらがな）',
        max_length=100,
        validators=[hiragana_validator],
        help_text='しりとり用の読み方をひらがなで入力してください（複数の場合はカンマ「,」や「、」で区切ってください。例: りんご, らいおん）。',
        widget=forms.TextInput(attrs={
            'placeholder': '例: りんご',
            'autocomplete': 'off'
        })
    )

    class Meta:
        model = GameImage
        fields = ['image']
