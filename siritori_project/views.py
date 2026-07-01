from django.shortcuts import render


def landing(request):
    """
    アプリ選択用ランディングページを表示するビュー
    """
    return render(request, 'landing.html')
