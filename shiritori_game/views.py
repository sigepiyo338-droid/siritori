from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from .models import GameImage

def game_index(request):
    """
    ゲーム本体のHTMLページを表示するビュー
    """
    return render(request, 'shiritori_game/index.html')

def user_login(request):
    """
    ユーザーログイン画面の表示と処理を行うビュー
    """
    if request.user.is_authenticated:
        return redirect('shiritori_game:game_index')
        
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            return redirect('shiritori_game:game_index')
    else:
        form = AuthenticationForm()
        
    return render(request, 'shiritori_game/login.html', {'form': form})

def user_logout(request):
    """
    ログアウト処理を行い、トップ画面へリダイレクトするビュー
    """
    auth_logout(request)
    return redirect('shiritori_game:game_index')


def image_list_api(request):
    """
    承認済みの画像としりとり用読み方のリストをJSON形式で返すAPI
    """
    approved_images = GameImage.objects.filter(is_approved=True).prefetch_related('readings')
    
    data = []
    for img in approved_images:
        # 画像ファイルが存在する場合のみリストに含める
        if img.image:
            data.append({
                'id': img.id,
                'image_url': img.image.url,
                'readings': [r.reading for r in img.readings.all()]
            })
            
    return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})
