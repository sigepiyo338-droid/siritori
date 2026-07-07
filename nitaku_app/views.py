import sqlite3
import os
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json

# nitaku_app の SQLite DB パス（Flask 時代からの instance/database.db）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'database.db')


def get_db():
    """SQLite 接続を返すヘルパー"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def index(request):
    """究極二択くんのトップページ"""
    return render(request, 'index.html')


def get_personalities(request):
    """性格一覧を返す API"""
    try:
        conn = get_db()
        rows = conn.execute('SELECT id, name, label FROM personalities').fetchall()
        conn.close()
        data = [{'id': r['id'], 'name': r['name'], 'label': r['label']} for r in rows]
        return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_questions(request):
    """質問一覧を返す API"""
    try:
        count_param = request.GET.get('count', '10')
        try:
            limit = int(count_param)
        except ValueError:
            limit = 10

        conn = get_db()
        rows = conn.execute(
            'SELECT id, text, option_a, option_b, author FROM questions ORDER BY RANDOM() LIMIT ?',
            (limit,)
        ).fetchall()
        conn.close()
        data = [
            {
                'id': r['id'],
                'text': r['text'],
                'option_a': r['option_a'],
                'option_b': r['option_b'],
                'author': r['author'],
            }
            for r in rows
        ]
        return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_POST
def post_question(request):
    """新しい質問を投稿する API"""
    try:
        body = json.loads(request.body)
        text = body.get('text', '').strip()
        option_a = body.get('option_a', '').strip()
        option_b = body.get('option_b', '').strip()
        author = body.get('author', 'ゲスト').strip() or 'ゲスト'

        posted_by = request.user.username if request.user.is_authenticated else None

        if not text or not option_a or not option_b:
            return JsonResponse({'error': '必須項目が不足しています'}, status=400)

        conn = get_db()
        conn.execute(
            'INSERT INTO questions (text, option_a, option_b, author, posted_by) VALUES (?, ?, ?, ?, ?)',
            (text, option_a, option_b, author, posted_by),
        )
        conn.commit()
        conn.close()
        return JsonResponse({'message': '質問を登録しました'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def my_questions(request):
    """ログインユーザーが投稿した質問一覧を返す API"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'ログインが必要です'}, status=401)
        
    try:
        conn = get_db()
        rows = conn.execute(
            'SELECT id, text, option_a, option_b, author FROM questions WHERE posted_by = ? ORDER BY id DESC',
            (request.user.username,)
        ).fetchall()
        conn.close()
        
        data = [
            {
                'id': r['id'],
                'text': r['text'],
                'option_a': r['option_a'],
                'option_b': r['option_b'],
                'author': r['author'],
            }
            for r in rows
        ]
        return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_POST
def delete_question(request, question_id):
    """ログインユーザーが自分の投稿を削除する API"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'ログインが必要です'}, status=401)
        
    try:
        conn = get_db()
        # まず対象の質問が存在し、投稿者が自分であるか確認
        row = conn.execute(
            'SELECT id FROM questions WHERE id = ? AND posted_by = ?',
            (question_id, request.user.username)
        ).fetchone()
        
        if not row:
            conn.close()
            return JsonResponse({'error': '削除権限がないか、質問が存在しません'}, status=403)
            
        # 関連するscoresを削除
        conn.execute('DELETE FROM scores WHERE question_id = ?', (question_id,))
        # 関連するanswersを削除
        conn.execute('DELETE FROM answers WHERE question_id = ?', (question_id,))
        # 質問本体を削除
        conn.execute('DELETE FROM questions WHERE id = ?', (question_id,))
        
        conn.commit()
        conn.close()
        
        return JsonResponse({'message': '質問を削除しました'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_POST
def post_personality(request):
    """新しい性格を投稿する API"""
    try:
        body = json.loads(request.body)
        name = body.get('name', '').strip()
        label = body.get('label', '').strip()
        author = body.get('author', 'ゲスト').strip() or 'ゲスト'

        if not name or not label:
            return JsonResponse({'error': '性格名とラベルは必須です'}, status=400)
            
        posted_by = request.user.username if request.user.is_authenticated else None

        conn = get_db()
        conn.execute(
            'INSERT INTO personalities (name, label, author, posted_by) VALUES (?, ?, ?, ?)',
            (name, label, author, posted_by),
        )
        conn.commit()
        conn.close()
        return JsonResponse({'message': '性格を登録しました'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def my_personalities(request):
    """ログインユーザーが投稿した性格一覧を返す API"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'ログインが必要です'}, status=401)
        
    try:
        conn = get_db()
        rows = conn.execute(
            'SELECT id, name, label FROM personalities WHERE posted_by = ? ORDER BY id DESC',
            (request.user.username,)
        ).fetchall()
        conn.close()
        
        data = [
            {
                'id': r['id'],
                'name': r['name'],
                'label': r['label'],
            }
            for r in rows
        ]
        return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_POST
def delete_personality(request, personality_id):
    """ログインユーザーが自分の投稿した性格を削除する API"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'ログインが必要です'}, status=401)
        
    try:
        conn = get_db()
        row = conn.execute(
            'SELECT id FROM personalities WHERE id = ? AND posted_by = ?',
            (personality_id, request.user.username)
        ).fetchone()
        
        if not row:
            conn.close()
            return JsonResponse({'error': '削除権限がないか、性格が存在しません'}, status=403)
            
        # 関連するscoresの削除
        conn.execute('DELETE FROM scores WHERE personality_id = ?', (personality_id,))
        # 自身を削除
        conn.execute('DELETE FROM personalities WHERE id = ?', (personality_id,))
        
        conn.commit()
        conn.close()
        
        return JsonResponse({'message': '性格を削除しました'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_POST
def submit_answer(request):
    """回答を記録する API"""
    try:
        body = json.loads(request.body)
        question_id = body.get('question_id')
        choice = body.get('choice')
        personality_ids = body.get('personality_ids', [])

        if not question_id or choice not in ('A', 'B'):
            return JsonResponse({'error': '不正なリクエストです'}, status=400)

        conn = get_db()

        # 回答を記録
        conn.execute(
            'INSERT INTO answers (question_id, choice) VALUES (?, ?)',
            (question_id, choice),
        )

        # 性格スコアを更新
        for pid in personality_ids:
            existing = conn.execute(
                'SELECT id FROM scores WHERE question_id=? AND personality_id=? AND option=?',
                (question_id, pid, choice),
            ).fetchone()
            if existing:
                conn.execute(
                    'UPDATE scores SET count = count + 1 WHERE id=?',
                    (existing['id'],),
                )
            else:
                conn.execute(
                    'INSERT INTO scores (question_id, personality_id, option, count) VALUES (?, ?, ?, 1)',
                    (question_id, pid, choice),
                )

        conn.commit()
        conn.close()

        # 集計結果を返す
        conn = get_db()
        total_a = conn.execute(
            'SELECT COUNT(*) as cnt FROM answers WHERE question_id=? AND choice="A"',
            (question_id,),
        ).fetchone()['cnt']
        total_b = conn.execute(
            'SELECT COUNT(*) as cnt FROM answers WHERE question_id=? AND choice="B"',
            (question_id,),
        ).fetchone()['cnt']
        conn.close()

        total = total_a + total_b
        percent_a = int((total_a / total) * 100) if total > 0 else 0
        percent_b = 100 - percent_a if total > 0 else 0

        return JsonResponse(
            {
                'total_a': total_a,
                'total_b': total_b,
                'percent_a': percent_a,
                'percent_b': percent_b
            },
            json_dumps_params={'ensure_ascii': False},
        )
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_POST
def radar_scores(request):
    """性格ごとのスコア集計を返す API"""
    try:
        body = json.loads(request.body)
        personality_ids = body.get('personality_ids', [])
        answers = body.get('answers', [])

        if not personality_ids or not answers:
            return JsonResponse([], safe=False)

        conn = get_db()
        series = []

        for pid in personality_ids:
            p = conn.execute(
                'SELECT name, label FROM personalities WHERE id=?', (pid,)
            ).fetchone()
            if not p:
                continue
            
            total_score = 0
            for ans in answers:
                qid = ans.get('question_id')
                choice = ans.get('choice')
                if not qid or not choice:
                    continue
                
                row = conn.execute(
                    'SELECT count FROM scores WHERE question_id=? AND personality_id=? AND option=?',
                    (qid, pid, choice)
                ).fetchone()
                if row:
                    total_score += row['count']
            
            normalized_score = min(total_score, 5)

            series.append({
                'name': p['name'],
                'label': p['label'],
                'value': normalized_score
            })

        conn.close()
        return JsonResponse(series, safe=False, json_dumps_params={'ensure_ascii': False})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
