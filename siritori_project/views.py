from django.shortcuts import render


def landing(request):
    """
    アプリ選択用ランディングページを表示するビュー
    """
    return render(request, 'landing.html')

def developer_info(request):
    """
    デベロッパー・リクルーター様向け資料ページを表示するビュー
    """
    return render(request, 'developer_info.html')
