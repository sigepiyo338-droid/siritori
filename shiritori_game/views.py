from django.shortcuts import render
from django.http import JsonResponse
from .models import GameImage

def game_index(request):
    """
    ゲーム本体のHTMLページを表示するビュー
    """
    return render(request, 'shiritori_game/index.html')

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
