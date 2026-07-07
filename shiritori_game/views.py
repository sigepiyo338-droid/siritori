from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from .models import GameImage, ImageReading
from .forms import ImageUploadForm, UserRegistrationForm

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
            
            # 読み方を保存 (フォーム検証済みのリストを使用。タプル (reading, display_name) が入っている)
            readings = form.cleaned_data['reading']
            for reading, display_name in readings:
                ImageReading.objects.create(image=game_image, reading=reading, display_name=display_name)
                
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
    
    if game_image.user != request.user and not request.user.is_superuser:
        messages.error(request, '自分が投稿した画像以外は削除できません。')
        return redirect('shiritori_game:my_images')
        
    game_image.delete()
    messages.success(request, '画像を削除しました。')
    
    # 管理者が他人の画像を削除した場合は全画像一覧へ戻る
    if request.user.is_superuser and game_image.user != request.user:
        return redirect('shiritori_game:all_users_images')
    return redirect('shiritori_game:my_images')


@login_required(login_url='shiritori_game:login')
def edit_image(request, image_id):
    """
    ログインユーザーが自身で投稿した画像の付随情報を編集するビュー
    """
    import json
    from .forms import ImageEditForm
    
    game_image = get_object_or_404(GameImage, pk=image_id)
    
    if game_image.user != request.user and not request.user.is_superuser:
        messages.error(request, '自分が投稿した画像以外は編集できません。')
        return redirect('shiritori_game:my_images')
        
    if request.method == 'POST':
        form = ImageEditForm(request.POST, instance=game_image)
        if form.is_valid():
            form.save()
            
            # 既存の読み方をクリアして再登録
            game_image.readings.all().delete()
            readings = form.cleaned_data['reading']
            for reading, display_name in readings:
                ImageReading.objects.create(image=game_image, reading=reading, display_name=display_name)
                
            messages.success(request, '画像情報を更新しました。')
            if request.user.is_superuser and game_image.user != request.user:
                return redirect('shiritori_game:all_users_images')
            return redirect('shiritori_game:my_images')
    else:
        # 現在の読み方をJSON文字列にして初期値としてセット
        existing_readings = [
            {'reading': r.reading, 'display_name': r.display_name or ''}
            for r in game_image.readings.all()
        ]
        initial_data = {'reading': json.dumps(existing_readings, ensure_ascii=False)}
        form = ImageEditForm(instance=game_image, initial=initial_data)
        
    return render(request, 'shiritori_game/edit_image.html', {'form': form, 'game_image': game_image})



def get_least_used_characters():
    import random
    from .models import ImageReading
    HIRAGANA = list("あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわん")
    
    small_to_large = {
        'ぁ': 'あ', 'ぃ': 'い', 'ぅ': 'う', 'ぇ': 'え', 'ぉ': 'お',
        'っ': 'つ', 'ゃ': 'や', 'ゅ': 'ゆ', 'ょ': 'よ', 'ゎ': 'わ'
    }
    voiced_to_clear = {
        'が': 'か', 'ぎ': 'き', 'ぐ': 'く', 'げ': 'け', 'ご': 'こ',
        'ざ': 'さ', 'じ': 'し', 'ず': 'す', 'ぜ': 'せ', 'ぞ': 'そ',
        'だ': 'た', 'ぢ': 'ち', 'づ': 'つ', 'で': 'て', 'ど': 'と',
        'ば': 'は', 'び': 'ひ', 'ぶ': 'ふ', 'べ': 'へ', 'ぼ': 'ほ',
        'ぱ': 'は', 'ぴ': 'ひ', 'ぷ': 'ふ', 'ぺ': 'へ', 'ぽ': 'ほ'
    }

    def normalize(char):
        if not char: return ''
        c = small_to_large.get(char, char)
        c = voiced_to_clear.get(c, c)
        return c

    readings = ImageReading.objects.filter(image__is_approved=True).values_list('reading', flat=True)
    
    start_counts = {char: 0 for char in HIRAGANA}
    end_counts = {char: 0 for char in HIRAGANA}
    
    for r in readings:
        if not r: continue
        
        first_char = normalize(r[0])
        if first_char in start_counts:
            start_counts[first_char] += 1
            
        last_char = r[-1]
        if last_char == 'ー' and len(r) > 1:
            last_char = r[-2]
            
        last_char = normalize(last_char)
        if last_char in end_counts:
            end_counts[last_char] += 1
            
    min_start_count = min(start_counts.values()) if start_counts else 0
    min_end_count = min(end_counts.values()) if end_counts else 0
    
    least_starts = [char for char, count in start_counts.items() if count == min_start_count]
    least_ends = [char for char, count in end_counts.items() if count == min_end_count]
    
    return random.choice(least_starts) if least_starts else 'あ', random.choice(least_ends) if least_ends else 'あ'

def game_index(request):
    """
    ゲーム本体のHTMLページを表示するビュー
    """
    needed_start, needed_end = get_least_used_characters()
    return render(request, 'shiritori_game/index.html', {
        'needed_start': needed_start,
        'needed_end': needed_end
    })

def user_register(request):
    """
    新規ユーザー登録画面の表示と処理を行うビュー
    """
    if request.user.is_authenticated:
        return redirect('landing')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # 登録後、自動でログインする
            auth_login(request, user)
            messages.success(request, f'ようこそ、{user.username}さん！アカウントが作成されました。')
            return redirect('landing')
    else:
        form = UserRegistrationForm()

    return render(request, 'shiritori_game/register.html', {'form': form})


def user_login(request):
    """
    ユーザーログイン画面の表示と処理を行うビュー
    """
    if request.user.is_authenticated:
        return redirect('landing')
        
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            return redirect('landing')
    else:
        form = AuthenticationForm()
        
    return render(request, 'shiritori_game/login.html', {'form': form})

def user_logout(request):
    """
    ログアウト処理を行い、トップ画面へリダイレクトするビュー
    """
    auth_logout(request)
    return redirect('landing')


def image_list_api(request):
    """
    設定に基づく画像としりとり用読み方のリストをJSON形式で返すAPI
    """
    include_unapproved_others = request.GET.get('include_unapproved_others', 'false') == 'true'

    if include_unapproved_others:
        # 他人の未承認画像も含むすべての画像が対象
        query = Q()
    else:
        # すべての承認済み画像と自分が投稿した未承認画像が出題の対象
        if request.user.is_authenticated:
            query = Q(is_approved=True) | Q(user=request.user)
        else:
            query = Q(is_approved=True)

    # フィルタを適用して画像を取得（重複を避けるためにdistinct）
    images = GameImage.objects.filter(query).select_related('user', 'user__profile').prefetch_related('readings').distinct()
    
    data = []
    for img in images:
        # 画像ファイルが存在する場合のみリストに含める
        if img.image:
            submitter_name = "名無し"
            if img.user:
                if hasattr(img.user, 'profile') and img.user.profile.nickname:
                    submitter_name = img.user.profile.nickname
                else:
                    submitter_name = img.user.username

            data.append({
                'id': img.id,
                'image_url': img.image_url,
                'readings': [
                    {
                        'reading': r.reading,
                        'display_name': r.display_name if r.display_name else ''
                    }
                    for r in img.readings.all()
                ],
                'user_id': img.user_id,
                'submitter_name': submitter_name,
                'remarks': img.remarks,
            })
            
    return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})


def game_settings(request):
    """
    出題設定画面を表示するビュー
    """
    return render(request, 'shiritori_game/settings.html')


@login_required(login_url='shiritori_game:login')
def post_management(request):
    """
    投稿管理画面を表示するビュー
    """
    return render(request, 'shiritori_game/management.html')

@user_passes_test(lambda u: u.is_superuser)
def all_users_images(request):
    """
    管理者専用: 全ユーザーの投稿画像一覧を表示するビュー
    """
    images = GameImage.objects.all().select_related('user').prefetch_related('readings')
    return render(request, 'shiritori_game/all_images.html', {'images': images})


@login_required(login_url='shiritori_game:login')
def account_settings(request):
    """
    アカウント設定画面を表示・アカウントの変更を行うビュー
    """
    user = request.user
    from .models import UserProfile
    profile, created = UserProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        if user.username == 'guest':
            messages.error(request, 'guestアカウントの登録情報は変更できません。')
            return redirect('shiritori_game:account_settings')
            
        email = request.POST.get('email', '').strip()
        nickname = request.POST.get('nickname', '').strip()
        user.email = email
        user.save()
        profile.nickname = nickname if nickname else None
        profile.save()
        messages.success(request, '設定を保存しました。')
        return redirect('shiritori_game:account_settings')
        
    return render(request, 'shiritori_game/account.html', {'profile': profile})
