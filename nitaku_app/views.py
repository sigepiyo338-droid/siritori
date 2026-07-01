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
        conn = get_db()
        rows = conn.execute(
            'SELECT id, text, option_a, option_b, author FROM questions'
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

        if not text or not option_a or not option_b:
            return JsonResponse({'error': '必須項目が不足しています'}, status=400)

        conn = get_db()
        conn.execute(
            'INSERT INTO questions (text, option_a, option_b, author) VALUES (?, ?, ?, ?)',
            (text, option_a, option_b, author),
        )
        conn.commit()
        conn.close()
        return JsonResponse({'message': '質問を登録しました'})
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

        if not name or not label:
            return JsonResponse({'error': '性格名とラベルは必須です'}, status=400)

        conn = get_db()
        conn.execute(
            'INSERT INTO personalities (name, label) VALUES (?, ?)',
            (name, label),
        )
        conn.commit()
        conn.close()
        return JsonResponse({'message': '性格を登録しました'})
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

        return JsonResponse(
            {'total_a': total_a, 'total_b': total_b},
            json_dumps_params={'ensure_ascii': False},
        )
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def radar_scores(request):
    """性格ごとのスコア集計を返す API"""
    try:
        question_ids_param = request.GET.get('question_ids', '')
        personality_ids_param = request.GET.get('personality_ids', '')

        if not question_ids_param or not personality_ids_param:
            return JsonResponse({'error': 'パラメータが不足しています'}, status=400)

        question_ids = [int(x) for x in question_ids_param.split(',') if x]
        personality_ids = [int(x) for x in personality_ids_param.split(',') if x]

        conn = get_db()
        result = {}

        for pid in personality_ids:
            p = conn.execute(
                'SELECT name, label FROM personalities WHERE id=?', (pid,)
            ).fetchone()
            if not p:
                continue

            scores_data = {}
            for qid in question_ids:
                row = conn.execute(
                    'SELECT option, count FROM scores WHERE question_id=? AND personality_id=?',
                    (qid, pid),
                ).fetchall()
                for r in row:
                    opt = r['option']
                    scores_data[f'{qid}_{opt}'] = r['count']

            result[pid] = {
                'name': p['name'],
                'label': p['label'],
                'scores': scores_data,
            }

        conn.close()
        return JsonResponse(result, json_dumps_params={'ensure_ascii': False})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
