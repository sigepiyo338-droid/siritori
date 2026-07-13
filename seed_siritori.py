import os
import django
import sys
from pathlib import Path

# Django環境のセットアップ
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'siritori_project.settings')
django.setup()

from django.contrib.auth.models import User
from shiritori_game.models import GameImage, ImageReading

def seed():
    print("マイグレーションを実行中...")
    from django.core.management import call_command
    call_command("migrate", interactive=False)

    print("管理者ユーザーを作成中...")
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'adminpass')
        print("管理者ユーザー (admin / adminpass) を作成しました。")
    else:
        print("管理者ユーザー (admin) は既に存在します。")

    # 登録するシード画像と読み仮名
    seeds = [
        ('apple.png', ['りんご']),
        ('gorilla.png', ['ごりら']),
        ('trumpet.png', ['らっぱ']),
        ('panda.png', ['ぱんだ']),
        ('ostrich.png', ['だちょう']),
        ('fan.png', ['うちわ']),
        ('crocodile.png', ['わに']),
        ('carrot.png', ['にんじん']),
    ]

    print("サンプル画像をデータベースに登録中...")
    admin_user = User.objects.get(username='admin')
    
    for filename, readings in seeds:
        db_path = f"uploads/seed/{filename}"
        
        # 既に登録されているかチェック
        if GameImage.objects.filter(image=db_path).exists():
            print(f"画像 {filename} は既に登録されています。")
            continue
            
        # GameImageの作成（承認済み状態）
        game_image = GameImage.objects.create(
            user=admin_user,
            image=db_path,
            is_approved=True
        )
        
        # 読み仮名の登録
        for reading in readings:
            ImageReading.objects.create(
                image=game_image,
                reading=reading
            )
        print(f"画像 {filename} (読み: {readings}) を登録しました。")

if __name__ == '__main__':
    seed()
