from __future__ import annotations

from datetime import datetime
import re
import sqlite3
import subprocess
import shutil
import sys
import webbrowser
from pathlib import Path
from urllib.request import urlopen

import tkinter as tk
from tkinter import messagebox, ttk
import os


# パスの設定
# C:\Users\frontier-Pythin\Documents または C:\Users\frontier-Pythin\Documents\siritori
# どちらから実行されても動作するように親ディレクトリと子ディレクトリの両方をチェックする
BASE_DIR = Path(__file__).resolve().parent
if (BASE_DIR / "siritori").exists():
    PROJECT_DIR = BASE_DIR / "siritori"
else:
    PROJECT_DIR = BASE_DIR

INDEX_PATH = PROJECT_DIR / "shiritori_game" / "templates" / "shiritori_game" / "index.html"
DB_PATH = PROJECT_DIR / "db.sqlite3"
DB_BACKUP_DIR = PROJECT_DIR / "backups"
MEDIA_ROOT = PROJECT_DIR / "media"

DB_URL = "https://sigepiyo338.pythonanywhere.com/static/db.sqlite3"
LOCAL_APP_URL = "http://127.0.0.1:8000/"
CHROME_WINDOW_SIZE = "800,950"

VERSION_PATTERN = re.compile(r'(<span id="app-version">)([^<]*)(</span>)')
UPDATED_PATTERN = re.compile(
    r"<span(?:\s+id=\"last-updated\")?>\s*最終更新:\s*[^<]*</span>"
)


def read_index() -> str:
    if not INDEX_PATH.exists():
        raise FileNotFoundError(f"index.html が見つかりません: {INDEX_PATH}")
    return INDEX_PATH.read_text(encoding="utf-8")


def write_index(content: str) -> None:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(content, encoding="utf-8")


def extract_meta(content: str) -> tuple[str, str]:
    version_match = VERSION_PATTERN.search(content)
    version = version_match.group(2).strip() if version_match else ""

    updated_match = re.search(r"最終更新:\s*([^<\n\)]+)", content)
    updated = updated_match.group(1).strip() if updated_match else ""

    return version, updated


def replace_meta(content: str, version: str, updated: str) -> str:
    new_content, version_replaced = VERSION_PATTERN.subn(
        rf"\1{version}\3", content, count=1
    )
    if version_replaced == 0:
        raise ValueError("app-version の `<span id=\"app-version\">` が見つかりません。")

    replacement = f'<span id="last-updated">最終更新: {updated}</span>'
    new_content, updated_replaced = UPDATED_PATTERN.subn(
        replacement, new_content, count=1
    )
    if updated_replaced == 0:
        raise ValueError("最終更新表示の `<span>` が見つかりません。")

    return new_content


def update_meta(version: str, updated: str) -> None:
    if not version or not updated:
        raise ValueError("バージョンと最終更新日は必須です。")

    content = read_index()
    updated_content = replace_meta(content, version=version, updated=updated)
    write_index(updated_content)


NITAKU_INDEX_PATH = PROJECT_DIR / "nitaku_app" / "templates" / "index.html"
NITAKU_VERSION_PATTERN = re.compile(r'(<span id="app-version">)([^<]*)(</span>)')
NITAKU_UPDATED_PATTERN = re.compile(
    r"<span(?:\s+id=\"last-updated\")?>\s*最終更新:\s*[^<]*</span>"
)


def read_nitaku_index() -> str:
    if not NITAKU_INDEX_PATH.exists():
        raise FileNotFoundError(f"index.html が見つかりません: {NITAKU_INDEX_PATH}")
    return NITAKU_INDEX_PATH.read_text(encoding="utf-8")


def write_nitaku_index(content: str) -> None:
    NITAKU_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    NITAKU_INDEX_PATH.write_text(content, encoding="utf-8")


def extract_nitaku_meta(content: str) -> tuple[str, str]:
    version_match = NITAKU_VERSION_PATTERN.search(content)
    version = version_match.group(2).strip() if version_match else ""

    updated_match = re.search(r"最終更新:\s*([^<\n]+)", content)
    updated = updated_match.group(1).strip() if updated_match else ""

    return version, updated


def replace_nitaku_meta(content: str, version: str, updated: str) -> str:
    new_content, version_replaced = NITAKU_VERSION_PATTERN.subn(
        rf"\1{version}\3", content, count=1
    )
    if version_replaced == 0:
        raise ValueError("app-version の `<span id=\"app-version\">` が見つかりません。")

    replacement = f"<span>最終更新: {updated}</span>"
    new_content, updated_replaced = NITAKU_UPDATED_PATTERN.subn(
        replacement, new_content, count=1
    )
    if updated_replaced == 0:
        raise ValueError("最終更新表示の `<span>` が見つかりません。")

    return new_content


def update_nitaku_meta(version: str, updated: str) -> None:
    if not version or not updated:
        raise ValueError("バージョンと最終更新日は必須です。")

    content = read_nitaku_index()
    updated_content = replace_nitaku_meta(content, version=version, updated=updated)
    write_nitaku_index(updated_content)


def sync_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(DB_URL, timeout=20) as response:
        data = response.read()
    if not data:
        raise ValueError("ダウンロードしたDBが空です。")
    DB_PATH.write_bytes(data)


def backup_db() -> Path:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"バックアップ対象の db.sqlite3 が見つかりません: {DB_PATH}")
    DB_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = DB_BACKUP_DIR / f"db_{timestamp}.sqlite3"
    shutil.copy2(DB_PATH, backup_path)
    return backup_path


def format_db_last_modified() -> str:
    if not DB_PATH.exists():
        return "ローカルDB最終更新日: （db.sqlite3 が存在しません）"
    modified_at = datetime.fromtimestamp(DB_PATH.stat().st_mtime)
    return f"ローカルDB最終更新日: {modified_at.strftime('%Y-%m-%d %H:%M:%S')}"




def read_personalities() -> tuple[list[str], list[tuple]]:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"db.sqlite3 が見つかりません: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        columns_cursor = conn.execute("PRAGMA table_info(personalities)")
        columns = [row[1] for row in columns_cursor.fetchall()]
        if not columns:
            raise ValueError("personalities テーブルが見つかりません。")

        rows_cursor = conn.execute("SELECT * FROM personalities ORDER BY id")
        rows = rows_cursor.fetchall()
    return columns, rows


def delete_personality_and_related_scores(personality_id: int) -> tuple[int, int]:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"db.sqlite3 が見つかりません: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM scores WHERE personality_id = ?", (personality_id,))
        deleted_scores = cursor.rowcount if cursor.rowcount != -1 else 0
        cursor.execute("DELETE FROM personalities WHERE id = ?", (personality_id,))
        deleted_personalities = cursor.rowcount if cursor.rowcount != -1 else 0
        conn.commit()

    if deleted_personalities == 0:
        raise ValueError("選択された personality は既に存在しない可能性があります。")
    return deleted_personalities, deleted_scores


def read_questions() -> tuple[list[str], list[tuple]]:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"db.sqlite3 が見つかりません: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        columns_cursor = conn.execute("PRAGMA table_info(questions)")
        columns = [row[1] for row in columns_cursor.fetchall()]
        if not columns:
            raise ValueError("questions テーブルが見つかりません。")

        rows_cursor = conn.execute("SELECT * FROM questions ORDER BY id")
        rows = rows_cursor.fetchall()
    return columns, rows


def delete_question_and_related_records(question_id: int) -> tuple[int, int, int]:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"db.sqlite3 が見つかりません: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM answers WHERE question_id = ?", (question_id,))
        deleted_answers = cursor.rowcount if cursor.rowcount != -1 else 0
        cursor.execute("DELETE FROM scores WHERE question_id = ?", (question_id,))
        deleted_scores = cursor.rowcount if cursor.rowcount != -1 else 0
        cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        deleted_questions = cursor.rowcount if cursor.rowcount != -1 else 0
        conn.commit()

    if deleted_questions == 0:
        raise ValueError("選択された question は既に存在しない可能性があります。")
    return deleted_questions, deleted_answers, deleted_scores


def find_chrome_executable() -> str | None:
    # 1. 環境変数 PATH から検索
    candidates = [
        "chrome",
        "chrome.exe",
        "google-chrome",
        "msedge",
        "msedge.exe",
    ]
    for candidate in candidates:
        executable = shutil.which(candidate)
        if executable:
            return executable
            
    # 2. Windows の標準的なインストールパスを直接チェック
    if sys.platform == "win32":
        # 一般的なインストール先候補
        win_candidates = [
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("LocalAppData", "C:/Users/Default/AppData/Local")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Microsoft/Edge/Application/msedge.exe",
        ]
        for p in win_candidates:
            if p.exists():
                return str(p)
                
    return None


def open_main_screen_in_app_mode(url: str) -> bool:
    chrome_path = find_chrome_executable()
    if not chrome_path:
        return False
    
    # 専用のプロファイル保存場所
    profile_path = PROJECT_DIR / "temp_profile"
    
    subprocess.Popen(
        [
            chrome_path,
            f"--app={url}",
            f"--window-size={CHROME_WINDOW_SIZE}",
            f"--user-data-dir={profile_path}",
            "--force-device-scale-factor=1",
        ]
    )
    return True


def build_ui() -> tk.Tk:
    root = tk.Tk()
    root.title("しりとり師範くん ローカル管理ツール")
    root.geometry("820x450")
    root.resizable(True, True)
    root.minsize(820, 450)
    root.columnconfigure(0, weight=1)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(
        "Manager.TNotebook",
        background="#d6d6d6",
        borderwidth=1,
        relief="solid",
    )
    style.configure(
        "Manager.TNotebook.Tab",
        background="#c8c8c8",
        foreground="#1f1f1f",
        borderwidth=1,
        padding=(12, 5),
    )
    style.map(
        "Manager.TNotebook.Tab",
        background=[("selected", "#ffffff"), ("active", "#e3e3e3")],
        foreground=[("selected", "#000000"), ("active", "#1a1a1a")],
        padding=[("selected", (16, 8)), ("!selected", (12, 5))],
        relief=[("selected", "raised"), ("!selected", "ridge")],
    )
    style.configure("Manager.TFrame", background="#f6f6f6")

    frame = ttk.Frame(root, padding=16)
    frame.grid(row=0, column=0, sticky="nsew")
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)

    nitaku_app_server_process: subprocess.Popen | None = None

    # index.htmlが存在しない場合の初期化/例外回避
    try:
        content = read_index()
        current_version, current_updated = extract_meta(content)
    except Exception:
        current_version = "v1.0.0"
        current_updated = datetime.now().strftime("%Y-%m-%d")

    # バージョンパース (例: "v1.2.3" -> prefix="v", major=1, minor=2, patch=3)
    match = re.match(r"^(v?)(\d+)\.(\d+)\.(\d+)$", current_version.strip())
    if match:
        prefix_val = match.group(1)
        major_val = int(match.group(2))
        minor_val = int(match.group(3))
        patch_val = int(match.group(4))
    else:
        prefix_val = "v"
        major_val = 1
        minor_val = 0
        patch_val = 0

    prefix_var = tk.StringVar(value=prefix_val)
    major_var = tk.IntVar(value=major_val)
    minor_var = tk.IntVar(value=minor_val)
    patch_var = tk.IntVar(value=patch_val)

    updated_var = tk.StringVar(value=current_updated)
    status_var = tk.StringVar(value="準備完了")
    db_last_modified_var = tk.StringVar(value=format_db_last_modified())

    def handle_backup_db() -> None:
        try:
            backup_path = backup_db()
            status_var.set(f"db.sqlite3 をバックアップしました: {backup_path.name}")
            messagebox.showinfo(
                "成功", f"db.sqlite3 をバックアップしました。\n保存先: {backup_path}"
            )
        except Exception as exc:
            status_var.set(f"DBバックアップ失敗: {exc}")
            messagebox.showerror("エラー", f"DBバックアップ失敗: {exc}")

    def handle_sync_db() -> None:
        if not messagebox.askyesno(
            "確認", "オンライン版の db.sqlite3 でローカルを上書きします。続行しますか？"
        ):
            return
        try:
            backup_label = "（既存DBなし）"
            if DB_PATH.exists():
                backup_path = backup_db()
                backup_label = backup_path.name
            sync_db()
            db_last_modified_var.set(format_db_last_modified())
            status_var.set(f"db.sqlite3 を上書き同期しました。バックアップ: {backup_label}")
            messagebox.showinfo(
                "成功",
                "db.sqlite3 を上書き同期しました。\n"
                f"事前バックアップ: {backup_label}",
            )
            # 他のタブの一覧をリロード（該当機能は削除済み）
        except Exception as exc:
            status_var.set(f"DB同期失敗: {exc}")
            messagebox.showerror("エラー", f"DB同期失敗: {exc}")

    notebook = ttk.Notebook(frame, style="Manager.TNotebook")
    notebook.grid(row=0, column=0, sticky="nsew")

    # ---- 1. 師範くん管理タブ ----
    version_tab = ttk.Frame(notebook, style="Manager.TFrame", padding=12)
    version_tab.columnconfigure(1, weight=1)
    notebook.add(version_tab, text="師範くん管理")

    ttk.Label(version_tab, text="アプリ情報収集（index.html）").grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
    )
    ttk.Label(version_tab, text=f"対象: {INDEX_PATH}").grid(
        row=1, column=0, columnspan=2, sticky="w", pady=(0, 12)
    )
    ttk.Label(version_tab, text="バージョン").grid(row=2, column=0, sticky="w")
    
    # バージョンの各桁数をスピンボタンで増減できるようにする
    version_frame = ttk.Frame(version_tab, style="Manager.TFrame")
    version_frame.grid(row=2, column=1, sticky="w", padx=(8, 0), pady=(0, 8))

    prefix_combo = ttk.Combobox(version_frame, textvariable=prefix_var, values=["v", ""], width=3)
    prefix_combo.pack(side="left")

    major_spin = ttk.Spinbox(version_frame, from_=0, to=99, width=4, textvariable=major_var)
    major_spin.pack(side="left", padx=(2, 0))

    ttk.Label(version_frame, text=".").pack(side="left")

    minor_spin = ttk.Spinbox(version_frame, from_=0, to=99, width=4, textvariable=minor_var)
    minor_spin.pack(side="left")

    ttk.Label(version_frame, text=".").pack(side="left")

    patch_spin = ttk.Spinbox(version_frame, from_=0, to=99, width=4, textvariable=patch_var)
    patch_spin.pack(side="left")

    ttk.Label(version_tab, text="最終更新日").grid(row=3, column=0, sticky="w")
    updated_entry = ttk.Entry(version_tab, textvariable=updated_var)
    updated_entry.grid(row=3, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))

    def set_today() -> None:
        updated_var.set(datetime.now().strftime("%Y-%m-%d"))

    ttk.Button(version_tab, text="本日の日付にする", command=set_today).grid(
        row=4, column=1, sticky="w", padx=(8, 0), pady=(0, 8)
    )

    def handle_update_meta() -> None:
        try:
            v_str = f"{prefix_var.get()}{major_var.get()}.{minor_var.get()}.{patch_var.get()}"
            update_meta(v_str.strip(), updated_var.get().strip())
            status_var.set("index.html を更新しました。")
            messagebox.showinfo("成功", f"index.html を更新しました。\nバージョン: {v_str}")
        except Exception as exc:
            status_var.set(f"更新失敗: {exc}")
            messagebox.showerror("エラー", f"更新失敗: {exc}")

    ttk.Button(version_tab, text="index.html を更新する", command=handle_update_meta).grid(
        row=5, column=0, columnspan=2, sticky="ew", pady=(4, 16)
    )

    ttk.Separator(version_tab, orient="horizontal").grid(
        row=6, column=0, columnspan=2, sticky="ew", pady=(8, 16)
    )

    ttk.Label(version_tab, text="db.sqlite3 同期（上書き）").grid(
        row=7, column=0, columnspan=2, sticky="w", pady=(0, 8)
    )
    ttk.Label(version_tab, text=f"ダウンロード元: {DB_URL}").grid(
        row=8, column=0, columnspan=2, sticky="w"
    )
    ttk.Label(version_tab, text=f"保存先: {DB_PATH}").grid(
        row=9, column=0, columnspan=2, sticky="w", pady=(0, 8)
    )

    ttk.Button(version_tab, text="現在のDBをバックアップする", command=handle_backup_db).grid(
        row=10, column=0, columnspan=2, sticky="ew", pady=(4, 6)
    )
    ttk.Button(version_tab, text="オンライン版で上書きする", command=handle_sync_db).grid(
        row=11, column=0, columnspan=2, sticky="ew", pady=(0, 6)
    )
    ttk.Label(version_tab, textvariable=db_last_modified_var).grid(
        row=12, column=0, columnspan=2, sticky="w", pady=(0, 6)
    )

    # ---- 1.5. 2択くん管理タブ ----
    try:
        nitaku_content = read_nitaku_index()
        nitaku_version_val, nitaku_updated_val = extract_nitaku_meta(nitaku_content)
    except Exception:
        nitaku_version_val = "v1.0.0"
        nitaku_updated_val = datetime.now().strftime("%Y-%m-%d")

    nitaku_match = re.match(r"^(v?)(\d+)\.(\d+)\.(\d+)$", nitaku_version_val.strip())
    if nitaku_match:
        n_prefix_val = nitaku_match.group(1)
        n_major_val = int(nitaku_match.group(2))
        n_minor_val = int(nitaku_match.group(3))
        n_patch_val = int(nitaku_match.group(4))
    else:
        n_prefix_val = "v"
        n_major_val = 1
        n_minor_val = 0
        n_patch_val = 0

    nitaku_prefix_var = tk.StringVar(value=n_prefix_val)
    nitaku_major_var = tk.IntVar(value=n_major_val)
    nitaku_minor_var = tk.IntVar(value=n_minor_val)
    nitaku_patch_var = tk.IntVar(value=n_patch_val)
    nitaku_updated_var = tk.StringVar(value=nitaku_updated_val)

    nitaku_tab = ttk.Frame(notebook, style="Manager.TFrame", padding=12)
    notebook.add(nitaku_tab, text="2択くん管理")
    nitaku_tab.columnconfigure(0, weight=1)
    nitaku_tab.rowconfigure(0, weight=1)

    nitaku_notebook = ttk.Notebook(nitaku_tab, style="Manager.TNotebook")
    nitaku_notebook.grid(row=0, column=0, sticky="nsew")

    # ---- 2択くん: バージョン管理 ----
    nitaku_version_tab = ttk.Frame(nitaku_notebook, style="Manager.TFrame", padding=12)
    nitaku_version_tab.columnconfigure(1, weight=1)
    nitaku_notebook.add(nitaku_version_tab, text="バージョン管理")

    ttk.Label(nitaku_version_tab, text="アプリ情報収集（index.html）").grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
    )
    ttk.Label(nitaku_version_tab, text=f"対象: {NITAKU_INDEX_PATH}").grid(
        row=1, column=0, columnspan=2, sticky="w", pady=(0, 12)
    )
    ttk.Label(nitaku_version_tab, text="バージョン").grid(row=2, column=0, sticky="w")
    
    nitaku_version_frame = ttk.Frame(nitaku_version_tab, style="Manager.TFrame")
    nitaku_version_frame.grid(row=2, column=1, sticky="w", padx=(8, 0), pady=(0, 8))

    n_prefix_combo = ttk.Combobox(nitaku_version_frame, textvariable=nitaku_prefix_var, values=["v", ""], width=3)
    n_prefix_combo.pack(side="left")

    n_major_spin = ttk.Spinbox(nitaku_version_frame, from_=0, to=99, width=4, textvariable=nitaku_major_var)
    n_major_spin.pack(side="left", padx=(2, 0))

    ttk.Label(nitaku_version_frame, text=".").pack(side="left")

    n_minor_spin = ttk.Spinbox(nitaku_version_frame, from_=0, to=99, width=4, textvariable=nitaku_minor_var)
    n_minor_spin.pack(side="left")

    ttk.Label(nitaku_version_frame, text=".").pack(side="left")

    n_patch_spin = ttk.Spinbox(nitaku_version_frame, from_=0, to=99, width=4, textvariable=nitaku_patch_var)
    n_patch_spin.pack(side="left")

    ttk.Label(nitaku_version_tab, text="最終更新日").grid(row=3, column=0, sticky="w")
    nitaku_updated_entry = ttk.Entry(nitaku_version_tab, textvariable=nitaku_updated_var)
    nitaku_updated_entry.grid(row=3, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))

    def set_nitaku_today() -> None:
        nitaku_updated_var.set(datetime.now().strftime("%Y-%m-%d"))

    ttk.Button(nitaku_version_tab, text="本日の日付にする", command=set_nitaku_today).grid(
        row=4, column=1, sticky="w", padx=(8, 0), pady=(0, 8)
    )

    def handle_update_nitaku_meta() -> None:
        try:
            v_str = f"{nitaku_prefix_var.get()}{nitaku_major_var.get()}.{nitaku_minor_var.get()}.{nitaku_patch_var.get()}"
            update_nitaku_meta(v_str.strip(), nitaku_updated_var.get().strip())
            status_var.set("2択くんの index.html を更新しました。")
            messagebox.showinfo("成功", f"2択くんの index.html を更新しました。\nバージョン: {v_str}")
        except Exception as exc:
            status_var.set(f"更新失敗: {exc}")
            messagebox.showerror("エラー", f"更新失敗: {exc}")

    ttk.Button(nitaku_version_tab, text="index.html を更新する", command=handle_update_nitaku_meta).grid(
        row=5, column=0, columnspan=2, sticky="ew", pady=(4, 16)
    )

    # ---- 2択くん: DB管理 ----
    nitaku_db_tab = ttk.Frame(nitaku_notebook, style="Manager.TFrame", padding=12)
    nitaku_notebook.add(nitaku_db_tab, text="DB管理")

    ttk.Label(nitaku_db_tab, text="db.sqlite3 バックアップ（Django統合）").grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
    )
    ttk.Label(nitaku_db_tab, text="※ データベースはDjangoプロジェクトと統合されています。").grid(
        row=1, column=0, columnspan=2, sticky="w"
    )
    ttk.Label(nitaku_db_tab, text=f"保存先: {DB_PATH}").grid(
        row=2, column=0, columnspan=2, sticky="w", pady=(0, 8)
    )

    ttk.Button(nitaku_db_tab, text="現在のDBをバックアップする", command=handle_backup_db).grid(
        row=3, column=0, columnspan=2, sticky="ew", pady=(4, 6)
    )
    ttk.Button(nitaku_db_tab, text="オンライン版で上書きする", command=handle_sync_db).grid(
        row=4, column=0, columnspan=2, sticky="ew", pady=(0, 6)
    )
    ttk.Label(nitaku_db_tab, textvariable=db_last_modified_var).grid(
        row=5, column=0, columnspan=2, sticky="w", pady=(0, 6)
    )

    # ---- 2択くん: テスト ----
    nitaku_test_tab = ttk.Frame(nitaku_notebook, style="Manager.TFrame", padding=12)
    nitaku_test_tab.columnconfigure(0, weight=1)
    nitaku_notebook.add(nitaku_test_tab, text="テスト")
    
    NITAKU_APP_PATH = PROJECT_DIR / "nitaku_app" / "app.py"

    ttk.Label(nitaku_test_tab, text=f"実行対象: {NITAKU_APP_PATH}").grid(
        row=1, column=0, sticky="w", pady=(0, 8)
    )

    def handle_run_nitaku_app_py() -> None:
        nonlocal nitaku_app_server_process
        if not NITAKU_APP_PATH.exists():
            status_var.set("app.py 実行失敗: app.py が見つかりません。")
            messagebox.showerror("エラー", f"app.py が見つかりません: {NITAKU_APP_PATH}")
            return
            
        venv_python = PROJECT_DIR / ".venv" / "Scripts" / "python.exe"
        python_executable = str(venv_python) if venv_python.exists() else sys.executable
            
        try:
            if nitaku_app_server_process is None or nitaku_app_server_process.poll() is not None:
                creationflags = 0
                if sys.platform == "win32":
                    creationflags = subprocess.CREATE_NO_WINDOW
                nitaku_app_server_process = subprocess.Popen(
                    [python_executable, str(NITAKU_APP_PATH)],
                    cwd=str(PROJECT_DIR / "nitaku_app"),
                    creationflags=creationflags,
                )
                status_var.set("app.py を起動しました。")
            else:
                status_var.set("app.py は起動済みです。")

            nitaku_local_url = "http://127.0.0.1:5000/"
            if open_main_screen_in_app_mode(nitaku_local_url):
                status_var.set("メイン画面をChromeアプリモードで開きました。")
            else:
                webbrowser.open(nitaku_local_url)
                status_var.set(
                    "Chromeが見つからないため通常ブラウザでメイン画面を開きました。"
                )
        except Exception as exc:
            status_var.set(f"app.py 実行失敗: {exc}")
            messagebox.showerror("エラー", f"app.py 実行失敗: {exc}")

    ttk.Button(nitaku_test_tab, text="ローカル起動", command=handle_run_nitaku_app_py).grid(
        row=2, column=0, sticky="w"
    )
    ttk.Label(
        nitaku_test_tab,
        text="※ ローカル起動中はX ポスト機能が制限されます。",
    ).grid(row=3, column=0, sticky="w", pady=(6, 0))

    # ---- 2択くん: 性格 ----
    personalities_tab = ttk.Frame(nitaku_notebook, style="Manager.TFrame", padding=12)
    personalities_tab.columnconfigure(0, weight=1)
    personalities_tab.rowconfigure(2, weight=1)
    nitaku_notebook.add(personalities_tab, text="性格")

    ttk.Label(personalities_tab, text="性格一覧（db.sqlite3）").grid(
        row=0, column=0, sticky="w", pady=(0, 8)
    )

    personalities_container = ttk.Frame(personalities_tab)
    personalities_container.grid(row=2, column=0, sticky="nsew")
    personalities_container.columnconfigure(0, weight=1)
    personalities_container.rowconfigure(0, weight=1)

    personalities_tree = ttk.Treeview(
        personalities_container,
        show="headings",
        height=9,
    )
    personalities_tree.grid(row=0, column=0, sticky="nsew")

    personalities_scroll_y = ttk.Scrollbar(
        personalities_container,
        orient="vertical",
        command=personalities_tree.yview,
    )
    personalities_scroll_y.grid(row=0, column=1, sticky="ns")
    personalities_tree.configure(yscrollcommand=personalities_scroll_y.set)

    personalities_status_var = tk.StringVar(value="未読込")
    ttk.Label(personalities_tab, textvariable=personalities_status_var).grid(
        row=3, column=0, sticky="w", pady=(8, 0)
    )

    def reload_personalities() -> None:
        try:
            columns, rows = read_personalities()

            personalities_tree.delete(*personalities_tree.get_children())
            personalities_tree.configure(columns=columns)
            for column in columns:
                personalities_tree.heading(column, text=column)
                personalities_tree.column(column, width=110, anchor="w")

            for row in rows:
                personalities_tree.insert("", "end", values=row)

            personalities_status_var.set(f"{len(rows)} 件表示")
        except Exception as exc:
            personalities_status_var.set(f"読込失敗: {exc}")
            status_var.set(f"性格タブ読込失敗: {exc}")

    def handle_delete_selected_personality() -> None:
        selected_items = personalities_tree.selection()
        if not selected_items:
            messagebox.showwarning("未選択", "削除する行を選択してください。")
            return

        item_id = selected_items[0]
        values = personalities_tree.item(item_id, "values")
        if not values:
            messagebox.showerror("エラー", "選択行の値を取得できませんでした。")
            return

        try:
            personality_id = int(values[0])
        except (TypeError, ValueError):
            messagebox.showerror("エラー", "選択行のIDが不正です。")
            return

        if not messagebox.askyesno(
            "確認",
            f"personality_id={personality_id} を削除します。\n"
            "関連する scores も削除されます。続行しますか？",
        ):
            return

        try:
            deleted_personalities, deleted_scores = delete_personality_and_related_scores(
                personality_id
            )
            reload_personalities()
            status_var.set(
                f"性格ID {personality_id} を削除（personalities:{deleted_personalities}, scores:{deleted_scores}）"
            )
            messagebox.showinfo(
                "削除完了",
                f"personalities: {deleted_personalities} 件\nscores: {deleted_scores} 件 を削除しました。",
            )
        except Exception as exc:
            status_var.set(f"性格削除失敗: {exc}")
            messagebox.showerror("エラー", f"性格削除失敗: {exc}")

    ttk.Button(
        personalities_tab, text="一覧を再読込", command=reload_personalities
    ).grid(row=1, column=0, sticky="w")
    ttk.Button(
        personalities_tab,
        text="選択中の性格を削除（scoresも削除）",
        command=handle_delete_selected_personality,
    ).grid(row=1, column=0, sticky="e")
    
    try:
        reload_personalities()
    except Exception:
        pass

    # ---- 2択くん: 質問 ----
    questions_tab = ttk.Frame(nitaku_notebook, style="Manager.TFrame", padding=12)
    questions_tab.columnconfigure(0, weight=1)
    questions_tab.rowconfigure(2, weight=1)
    nitaku_notebook.add(questions_tab, text="質問")

    ttk.Label(questions_tab, text="質問一覧（db.sqlite3）").grid(
        row=0, column=0, sticky="w", pady=(0, 8)
    )

    questions_container = ttk.Frame(questions_tab)
    questions_container.grid(row=2, column=0, sticky="nsew")
    questions_container.columnconfigure(0, weight=1)
    questions_container.rowconfigure(0, weight=1)

    questions_tree = ttk.Treeview(
        questions_container,
        show="headings",
        height=9,
    )
    questions_tree.grid(row=0, column=0, sticky="nsew")

    questions_scroll_y = ttk.Scrollbar(
        questions_container,
        orient="vertical",
        command=questions_tree.yview,
    )
    questions_scroll_y.grid(row=0, column=1, sticky="ns")
    questions_tree.configure(yscrollcommand=questions_scroll_y.set)

    questions_status_var = tk.StringVar(value="未読込")
    ttk.Label(questions_tab, textvariable=questions_status_var).grid(
        row=3, column=0, sticky="w", pady=(8, 0)
    )

    def reload_questions() -> None:
        try:
            columns, rows = read_questions()

            questions_tree.delete(*questions_tree.get_children())
            questions_tree.configure(columns=columns)
            for column in columns:
                questions_tree.heading(column, text=column)
                questions_tree.column(column, width=140, anchor="w")

            for row in rows:
                questions_tree.insert("", "end", values=row)

            questions_status_var.set(f"{len(rows)} 件表示")
        except Exception as exc:
            questions_status_var.set(f"読込失敗: {exc}")
            status_var.set(f"質問タブ読込失敗: {exc}")

    def handle_delete_selected_question() -> None:
        selected_items = questions_tree.selection()
        if not selected_items:
            messagebox.showwarning("未選択", "削除する行を選択してください。")
            return

        item_id = selected_items[0]
        values = questions_tree.item(item_id, "values")
        if not values:
            messagebox.showerror("エラー", "選択行の値を取得できませんでした。")
            return

        try:
            question_id = int(values[0])
        except (TypeError, ValueError):
            messagebox.showerror("エラー", "選択行のIDが不正です。")
            return

        if not messagebox.askyesno(
            "確認",
            f"question_id={question_id} を削除します。\n"
            "関連する answers と scores も削除されます。続行しますか？",
        ):
            return

        try:
            deleted_questions, deleted_answers, deleted_scores = (
                delete_question_and_related_records(question_id)
            )
            reload_questions()
            status_var.set(
                f"質問ID {question_id} を削除（questions:{deleted_questions}, answers:{deleted_answers}, scores:{deleted_scores}）"
            )
            messagebox.showinfo(
                "削除完了",
                f"questions: {deleted_questions} 件\n"
                f"answers: {deleted_answers} 件\n"
                f"scores: {deleted_scores} 件 を削除しました。",
            )
        except Exception as exc:
            status_var.set(f"質問削除失敗: {exc}")
            messagebox.showerror("エラー", f"質問削除失敗: {exc}")

    ttk.Button(questions_tab, text="一覧を再読込", command=reload_questions).grid(
        row=1, column=0, sticky="w"
    )
    ttk.Button(
        questions_tab,
        text="選択中の質問を削除（answers/scoresも削除）",
        command=handle_delete_selected_question,
    ).grid(row=1, column=0, sticky="e")
    
    try:
        reload_questions()
    except Exception:
        pass

    # ---- 2択くん: 外部ツール ----
    nitaku_tools_tab = ttk.Frame(nitaku_notebook, style="Manager.TFrame", padding=12)
    nitaku_tools_tab.columnconfigure(0, weight=1)
    nitaku_notebook.add(nitaku_tools_tab, text="外部ツール")

    ttk.Label(nitaku_tools_tab, text="・究極二択くん(オンライン版)").grid(
        row=0, column=0, sticky="w"
    )
    online_url = ttk.Label(
        nitaku_tools_tab,
        text="　-　https://sigepiyo338.pythonanywhere.com/",
        foreground="#0066cc",
        cursor="hand2",
    )
    online_url.grid(row=1, column=0, sticky="w", pady=(0, 8))
    online_url.bind(
        "<Button-1>",
        lambda _event: webbrowser.open("https://sigepiyo338.pythonanywhere.com/"),
    )

    ttk.Label(nitaku_tools_tab, text="・PythonAnywhere Dashboard").grid(
        row=2, column=0, sticky="w"
    )
    pa_url_nitaku = ttk.Label(
        nitaku_tools_tab,
        text="　-　https://www.pythonanywhere.com/",
        foreground="#0066cc",
        cursor="hand2",
    )
    pa_url_nitaku.grid(row=3, column=0, sticky="w", pady=(0, 8))
    pa_url_nitaku.bind(
        "<Button-1>",
        lambda _event: webbrowser.open("https://www.pythonanywhere.com/"),
    )

    ttk.Label(nitaku_tools_tab, text="・Github - 2takukun_web").grid(
        row=4, column=0, sticky="w"
    )
    github_url_nitaku = ttk.Label(
        nitaku_tools_tab,
        text="　-　https://github.com/sigepiyo338-droid/2takukun_web",
        foreground="#0066cc",
        cursor="hand2",
    )
    github_url_nitaku.grid(row=5, column=0, sticky="w")
    github_url_nitaku.bind(
        "<Button-1>",
        lambda _event: webbrowser.open(
            "https://github.com/sigepiyo338-droid/2takukun_web"
        ),
    )




    # ---- 3. テストタブ ----
    test_tab = ttk.Frame(notebook, style="Manager.TFrame", padding=12)
    test_tab.columnconfigure(0, weight=1)
    notebook.add(test_tab, text="テスト")
    app_server_process: subprocess.Popen | None = None

    ttk.Label(test_tab, text=f"実行対象: {PROJECT_DIR / 'manage.py'}").grid(
        row=1, column=0, sticky="w", pady=(0, 8)
    )

    def handle_run_app_py() -> None:
        nonlocal app_server_process
        manage_path = PROJECT_DIR / "manage.py"
        if not manage_path.exists():
            status_var.set("manage.py 実行失敗: manage.py が見つかりません。")
            messagebox.showerror("エラー", f"manage.py が見つかりません: {manage_path}")
            return
        
        venv_python = PROJECT_DIR / ".venv" / "Scripts" / "python.exe"
        python_executable = str(venv_python) if venv_python.exists() else sys.executable

        try:
            if app_server_process is None or app_server_process.poll() is not None:
                creationflags = 0
                if sys.platform == "win32":
                    creationflags = subprocess.CREATE_NO_WINDOW
                app_server_process = subprocess.Popen(
                    [python_executable, "manage.py", "runserver"],
                    cwd=str(PROJECT_DIR),
                    creationflags=creationflags,
                )
                status_var.set("Django開発サーバーを起動しました。")
            else:
                status_var.set("Django開発サーバーは起動済みです。")

            if open_main_screen_in_app_mode(LOCAL_APP_URL):
                status_var.set("メイン画面をChromeアプリモードで開きました。")
            else:
                webbrowser.open(LOCAL_APP_URL)
                status_var.set(
                    "Chromeが見つからないため通常ブラウザでメイン画面を開きました。"
                )
        except Exception as exc:
            status_var.set(f"Djangoサーバー起動失敗: {exc}")
            messagebox.showerror("エラー", f"Djangoサーバー起動失敗: {exc}")

    ttk.Button(test_tab, text="ローカル起動", command=handle_run_app_py).grid(
        row=2, column=0, sticky="w"
    )
    ttk.Label(
        test_tab,
        text="※ Django開発サーバーはバックグラウンドで起動します。",
    ).grid(row=3, column=0, sticky="w", pady=(6, 0))


    # ---- 6. 外部ツールタブ ----
    tools_tab = ttk.Frame(notebook, style="Manager.TFrame", padding=12)
    tools_tab.columnconfigure(0, weight=1)
    notebook.add(tools_tab, text="外部ツール")

    ttk.Label(tools_tab, text="・Django管理画面 (ローカル環境)").grid(
        row=0, column=0, sticky="w"
    )
    admin_url_label = ttk.Label(
        tools_tab,
        text=f"　-　{LOCAL_APP_URL}admin/",
        foreground="#0066cc",
        cursor="hand2",
    )
    admin_url_label.grid(row=1, column=0, sticky="w", pady=(0, 8))
    admin_url_label.bind(
        "<Button-1>",
        lambda _event: webbrowser.open(f"{LOCAL_APP_URL}admin/"),
    )

    ttk.Label(tools_tab, text="・PythonAnywhere Dashboard").grid(
        row=2, column=0, sticky="w"
    )
    pa_url = ttk.Label(
        tools_tab,
        text="　-　https://www.pythonanywhere.com/",
        foreground="#0066cc",
        cursor="hand2",
    )
    pa_url.grid(row=3, column=0, sticky="w", pady=(0, 8))
    pa_url.bind(
        "<Button-1>",
        lambda _event: webbrowser.open("https://www.pythonanywhere.com/"),
    )

    ttk.Label(frame, textvariable=status_var).grid(
        row=1, column=0, sticky="w", pady=(10, 0)
    )

    major_spin.focus_set()
    updated_entry.icursor(tk.END)

    # 終了時のサーバー停止処理
    def on_closing():
        nonlocal app_server_process, nitaku_app_server_process
        if app_server_process and app_server_process.poll() is None:
            if messagebox.askyesno("終了確認", "Django開発サーバーも停止しますか？"):
                try:
                    app_server_process.terminate()
                    app_server_process.wait(timeout=2)
                except Exception:
                    pass
        if nitaku_app_server_process and nitaku_app_server_process.poll() is None:
            try:
                nitaku_app_server_process.terminate()
                nitaku_app_server_process.wait(timeout=2)
            except Exception:
                pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    return root


if __name__ == "__main__":
    app_ui = build_ui()
    app_ui.mainloop()
