from django import forms
from .models import Post

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['author_name', 'message']
        widgets = {
            'author_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '名無しさん (任意)',
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'メッセージを入力してください...',
                'rows': 4,
                'required': True,
            }),
        }
