from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import GameImage, ImageReading
from .forms import ImageUploadForm

@login_required(login_url='shiritori_game:login')
def image_upload(request):
    """
    ユーザーが画像を新規投稿（アップロード）するビュー
    """
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # GameImageオブジェクトを作成（未承認状態）
            game_image = form.save(commit=False)
            game_image.is_approved = False
            game_image.user = request.user
            
            # 画像処理 (中央正方形クロップ & 600px上限縮小)
            uploaded_image = request.FILES.get('image')
            if uploaded_image:
                from PIL import Image
                import io
                from django.core.files.base import ContentFile
                
                img = Image.open(uploaded_image)
                original_format = img.format if img.format else 'PNG'
                width, height = img.size
                
                # 1. 正方形クロップ
                if width != height:
                    size = min(width, height)
                    left = (width - size) // 2
                    top = (height - size) // 2
                    right = left + size
                    bottom = top + size
                    img = img.crop((left, top, right, bottom))
                
                # 2. 600px上限縮小
                if img.size[0] > 600:
                    img = img.resize((600, 600), Image.Resampling.LANCZOS)
                
                # メモリ上バッファへ保存
                buffer = io.BytesIO()
                img.save(buffer, format=original_format)
                
                # フィールド値を新しいバイナリで更新
                filename = uploaded_image.name
                game_image.image.save(filename, ContentFile(buffer.getvalue()), save=False)
                
            game_image.save()
            
            # 読み方を保存 (フォーム検証済みのリストを使用)
            readings = form.cleaned_data['reading']
            for reading in readings:
                ImageReading.objects.create(image=game_image, reading=reading)
                
            messages.success(request, '画像を投稿しました！管理者が承認するまでゲーム内には表示されません。')
            return redirect('shiritori_game:game_index')
    else:
        form = ImageUploadForm()
        
    return render(request, 'shiritori_game/upload.html', {'form': form})


@login_required(login_url='shiritori_game:login')
def my_images(request):
    """
    ログインユーザーが自身で投稿した画像の一覧を表示するビュー
    """
    images = GameImage.objects.filter(user=request.user).prefetch_related('readings')
    return render(request, 'shiritori_game/my_images.html', {'images': images})


@login_required(login_url='shiritori_game:login')
def delete_image(request, image_id):
    """
    ログインユーザーが自身で投稿した画像を削除するビュー
    """
    from django.shortcuts import get_object_or_404
    from django.views.decorators.http import require_POST
    
    if request.method != 'POST':
        messages.error(request, '不正なリクエスト方法です。')
        return redirect('shiritori_game:my_images')
        
    game_image = get_object_or_404(GameImage, pk=image_id)
    
    if game_image.user != request.user:
        messages.error(request, '自分が投稿した画像以外は削除できません。')
        return redirect('shiritori_game:my_images')
        
    game_image.delete()
    messages.success(request, '画像を削除しました。')
    return redirect('shiritori_game:my_images')



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
