import sqlite3
import os

db_path = os.path.join('nitaku_app', 'instance', 'database.db')
conn = sqlite3.connect(db_path)

conn.execute('''
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    option_a TEXT NOT NULL,
    option_b TEXT NOT NULL,
    author TEXT DEFAULT 'ゲスト'
)
''')

conn.execute('''
CREATE TABLE IF NOT EXISTS personalities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    label TEXT NOT NULL
)
''')

conn.execute('''
CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER,
    choice TEXT NOT NULL,
    FOREIGN KEY (question_id) REFERENCES questions(id)
)
''')

conn.execute('''
CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER,
    personality_id INTEGER,
    option TEXT,
    count INTEGER DEFAULT 0,
    FOREIGN KEY (question_id) REFERENCES questions(id),
    FOREIGN KEY (personality_id) REFERENCES personalities(id)
)
''')

# サンプルデータ（性格）
personalities = [
    ('慎重', '慎重度'),
    ('社交的', '社交度'),
    ('感情的', '感情度'),
    ('楽観的', '楽観度'),
]
for name, label in personalities:
    existing = conn.execute('SELECT id FROM personalities WHERE name=?', (name,)).fetchone()
    if not existing:
        conn.execute('INSERT INTO personalities (name, label) VALUES (?, ?)', (name, label))

# サンプルデータ（質問）
questions = [
    ('一生夏か、一生冬か？', '一生夏', '一生冬', 'サンプル'),
    ('犬派か、猫派か？', '犬派', '猫派', 'サンプル'),
    ('朝型か、夜型か？', '朝型', '夜型', 'サンプル'),
]
for text, a, b, author in questions:
    existing = conn.execute('SELECT id FROM questions WHERE text=?', (text,)).fetchone()
    if not existing:
        conn.execute(
            'INSERT INTO questions (text, option_a, option_b, author) VALUES (?, ?, ?, ?)',
            (text, a, b, author)
        )

conn.commit()
conn.close()
print('DB initialized successfully at', db_path)
