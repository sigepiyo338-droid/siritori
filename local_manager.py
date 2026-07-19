from __future__ import annotations

from datetime import datetime
import re
import sqlite3
import subprocess
import shutil
import sys
import json
import webbrowser
from pathlib import Path
from urllib.request import urlopen
import ssl

import tkinter as tk
from tkinter import messagebox, ttk
import os


# パスの設定
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

SHIRITORI_DB_URL = "https://sigepiyo338.pythonanywhere.com/static/db.sqlite3"
NITAKU_DB_URL = "https://sigepiyo338.pythonanywhere.com/static/database.db"
NITAKU_DB_PATH = PROJECT_DIR / "nitaku_app" / "instance" / "database.db"
SHIRITORI_DB_PATH = DB_PATH
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


def sync_db(url: str, db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    context = ssl._create_unverified_context()
    with urlopen(url, timeout=20, context=context) as response:
        data = response.read()
    if not data:
        raise ValueError("ダウンロードしたDBが空です。")
    db_path.write_bytes(data)


def backup_db(db_path: Path) -> Path:
    if not db_path.exists():
        raise FileNotFoundError(f"バックアップ対象の {db_path.name} が見つかりません: {db_path}")
    DB_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = DB_BACKUP_DIR / f"{db_path.stem}_{timestamp}{db_path.suffix}"
    shutil.copy2(db_path, backup_path)
    return backup_path


def format_db_last_modified(db_path: Path, label: str) -> str:
    if not db_path.exists():
        return f"{label} 最終更新日: （存在しません）"
    modified_at = datetime.fromtimestamp(db_path.stat().st_mtime)
    return f"{label} 最終更新日: {modified_at.strftime('%Y-%m-%d %H:%M:%S')}"




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


def kill_processes_on_port(port: int) -> None:
    if sys.platform != "win32":
        return
    try:
        result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        pids = set()
        for line in result.stdout.splitlines():
            if f":{port} " in line and "LISTENING" in line:
                parts = line.split()
                if len(parts) >= 5:
                    pids.add(parts[-1])
        for pid in pids:
            if pid != "0":
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        pass


def build_ui() -> tk.Tk:
    root = tk.Tk()
    root.title("ローカル管理ツール")
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


    # ---- 1.5. 二択くん管理タブ ----
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
    notebook.add(nitaku_tab, text="二択くん管理")
    nitaku_tab.columnconfigure(0, weight=1)

    # ---- 二択くん: バージョン管理 (直配置) ----
    nitaku_tab.columnconfigure(1, weight=1)

    ttk.Label(nitaku_tab, text="アプリ情報収集（index.html）").grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
    )
    ttk.Label(nitaku_tab, text=f"対象: {NITAKU_INDEX_PATH}").grid(
        row=1, column=0, columnspan=2, sticky="w", pady=(0, 12)
    )
    ttk.Label(nitaku_tab, text="バージョン").grid(row=2, column=0, sticky="w")
    
    nitaku_version_frame = ttk.Frame(nitaku_tab, style="Manager.TFrame")
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

    ttk.Label(nitaku_tab, text="最終更新日").grid(row=3, column=0, sticky="w")
    nitaku_updated_entry = ttk.Entry(nitaku_tab, textvariable=nitaku_updated_var)
    nitaku_updated_entry.grid(row=3, column=1, sticky="ew", padx=(8, 0), pady=(0, 8))

    def set_nitaku_today() -> None:
        nitaku_updated_var.set(datetime.now().strftime("%Y-%m-%d"))

    ttk.Button(nitaku_tab, text="本日の日付にする", command=set_nitaku_today).grid(
        row=4, column=1, sticky="w", padx=(8, 0), pady=(0, 8)
    )

    def handle_update_nitaku_meta() -> None:
        try:
            v_str = f"{nitaku_prefix_var.get()}{nitaku_major_var.get()}.{nitaku_minor_var.get()}.{nitaku_patch_var.get()}"
            update_nitaku_meta(v_str.strip(), nitaku_updated_var.get().strip())
            status_var.set("二択くんの index.html を更新しました。")
            messagebox.showinfo("成功", f"二択くんの index.html を更新しました。\nバージョン: {v_str}")
        except Exception as exc:
            status_var.set(f"更新失敗: {exc}")
            messagebox.showerror("エラー", f"更新失敗: {exc}")

    ttk.Button(nitaku_tab, text="index.html を更新する", command=handle_update_nitaku_meta).grid(
        row=5, column=0, columnspan=2, sticky="ew", pady=(4, 16)
    )



    # ---- 2. DB管理タブ ----
    db_tab = ttk.Frame(notebook, style="Manager.TFrame", padding=12)
    db_tab.columnconfigure(0, weight=1)
    notebook.add(db_tab, text="DB管理")

    ttk.Label(db_tab, text="・Django管理画面 (ローカル環境)").grid(row=0, column=0, sticky="w")
    admin_url_label = ttk.Label(
        db_tab,
        text=f"　-　{LOCAL_APP_URL}admin/",
        foreground="#0066cc",
        cursor="hand2",
    )
    admin_url_label.grid(row=1, column=0, sticky="w", pady=(0, 4))
    admin_url_label.bind(
        "<Button-1>",
        lambda _event: webbrowser.open(f"{LOCAL_APP_URL}admin/"),
    )
    ttk.Separator(db_tab, orient="horizontal").grid(row=2, column=0, sticky="ew", pady=(8, 12))

    ttk.Label(db_tab, text="対象データベースを選択してください:").grid(row=3, column=0, sticky="w", pady=(0, 8))
    
    target_shiritori_var = tk.BooleanVar(value=True)
    target_nitaku_var = tk.BooleanVar(value=False)
    
    ttk.Checkbutton(db_tab, text="しりとり師範くん (db.sqlite3)", variable=target_shiritori_var).grid(row=4, column=0, sticky="w")
    ttk.Checkbutton(db_tab, text="究極二択くん (database.db)", variable=target_nitaku_var).grid(row=5, column=0, sticky="w", pady=(0, 16))

    def get_selected_dbs():
        dbs = []
        if target_shiritori_var.get():
            dbs.append(("しりとり師範くん", SHIRITORI_DB_URL, SHIRITORI_DB_PATH))
        if target_nitaku_var.get():
            dbs.append(("究極二択くん", NITAKU_DB_URL, NITAKU_DB_PATH))
        return dbs

    def handle_backup():
        dbs = get_selected_dbs()
        if not dbs:
            messagebox.showwarning("警告", "対象のデータベースが選択されていません。")
            return
        
        success_msgs = []
        for name, _, path in dbs:
            try:
                b_path = backup_db(path)
                success_msgs.append(f"[{name}] -> {b_path.name}")
            except Exception as e:
                messagebox.showerror("エラー", f"{name}のバックアップ失敗: {e}")
                return
        
        status_var.set(f"バックアップ完了: {len(success_msgs)}件")
        messagebox.showinfo("成功", "バックアップが完了しました。\n" + "\n".join(success_msgs))
        update_db_labels()

    def handle_sync():
        dbs = get_selected_dbs()
        if not dbs:
            messagebox.showwarning("警告", "対象のデータベースが選択されていません。")
            return
            
        if not messagebox.askyesno("確認", "オンライン版のDBでローカルを上書きします。続行しますか？"):
            return
            
        success_msgs = []
        for name, url, path in dbs:
            try:
                b_label = "（既存DBなし）"
                if path.exists():
                    b_path = backup_db(path)
                    b_label = b_path.name
                sync_db(url, path)
                success_msgs.append(f"[{name}] 同期完了 (バックアップ: {b_label})")
            except Exception as e:
                messagebox.showerror("エラー", f"{name}の同期失敗: {e}")
                return
                
        status_var.set(f"同期完了: {len(success_msgs)}件")
        messagebox.showinfo("成功", "オンライン同期が完了しました。\n" + "\n".join(success_msgs))
        update_db_labels()

    def handle_restore():
        from tkinter import filedialog
        
        dbs = get_selected_dbs()
        if not dbs:
            messagebox.showwarning("警告", "対象のデータベースが選択されていません。")
            return
        if len(dbs) > 1:
            messagebox.showwarning("警告", "復元は1つのデータベースに対してのみ実行できます。")
            return
            
        name, _, path = dbs[0]
        
        backup_file = filedialog.askopenfilename(
            title=f"{name} のバックアップファイルを選択",
            initialdir=str(DB_BACKUP_DIR),
            filetypes=[("SQLite DB", "*.sqlite3 *.db"), ("All Files", "*.*")]
        )
        
        if not backup_file:
            return
            
        if not messagebox.askyesno("確認", f"選択したファイルで {name} を復元します。現在の状態はバックアップされます。続行しますか？"):
            return
            
        try:
            if path.exists():
                backup_db(path)
            shutil.copy2(backup_file, path)
            status_var.set(f"{name} を復元しました: {Path(backup_file).name}")
            messagebox.showinfo("成功", f"{name} の復元が完了しました。")
            update_db_labels()
        except Exception as e:
            messagebox.showerror("エラー", f"復元失敗: {e}")

    ttk.Button(db_tab, text="オンライン版で上書き", command=handle_sync).grid(row=6, column=0, sticky="ew", pady=(0, 8))
    ttk.Button(db_tab, text="バックアップ", command=handle_backup).grid(row=7, column=0, sticky="ew", pady=(0, 8))
    ttk.Button(db_tab, text="ローカル版で復元", command=handle_restore).grid(row=8, column=0, sticky="ew", pady=(0, 16))

    shiritori_status_var = tk.StringVar()
    nitaku_status_var = tk.StringVar()

    def update_db_labels():
        shiritori_status_var.set(format_db_last_modified(SHIRITORI_DB_PATH, "しりとり師範くん"))
        nitaku_status_var.set(format_db_last_modified(NITAKU_DB_PATH, "究極二択くん"))

    ttk.Label(db_tab, textvariable=shiritori_status_var).grid(row=9, column=0, sticky="w", pady=(0, 4))
    ttk.Label(db_tab, textvariable=nitaku_status_var).grid(row=10, column=0, sticky="w", pady=(0, 4))
    
    update_db_labels()

    # ---- 3. テストタブ ----
    test_tab = ttk.Frame(notebook, style="Manager.TFrame", padding=12)
    test_tab.columnconfigure(0, weight=1)
    notebook.insert(0, test_tab, text="テスト")
    app_server_process: subprocess.Popen | None = None

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
            kill_processes_on_port(8000)
            if app_server_process is None or app_server_process.poll() is not None:
                creationflags = 0
                if sys.platform == "win32":
                    creationflags = subprocess.CREATE_NO_WINDOW
                
                # DEBUGがFalseなら、ローカル起動時に静的ファイルが配信されるように --insecure を追加する
                runserver_args = ["manage.py", "runserver"]
                if not debug_var.get():
                    runserver_args.append("--insecure")

                app_server_process = subprocess.Popen(
                    [python_executable] + runserver_args,
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

    # ---- DEBUGモード切り替えの追加 ----
    config_path = PROJECT_DIR / "config.json"
    
    def read_debug_status() -> bool:
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    return config.get("debug", True)
            except Exception:
                pass
        return True

    def write_debug_status(status: bool) -> None:
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({"debug": status}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("エラー", f"設定の保存に失敗しました: {e}")

    debug_var = tk.BooleanVar(value=read_debug_status())
    debug_status_var = tk.StringVar()

    def update_debug_label():
        if debug_var.get():
            debug_status_var.set("現在のモード: デバッグON (開発環境)")
        else:
            debug_status_var.set("現在のモード: デバッグOFF (本番シミュレーション)")

    def on_debug_toggle():
        write_debug_status(debug_var.get())
        update_debug_label()

    update_debug_label()

    def handle_setup_env() -> None:
        status_var.set("セットアップを開始します...")
        setup_btn.config(state="disabled")
        
        def run_setup():
            try:
                creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                
                status_var.set("仮想環境(.venv)を作成中...")
                subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True, cwd=str(PROJECT_DIR), creationflags=creationflags)
                
                status_var.set("requirements.txt をインストール中...")
                venv_python = PROJECT_DIR / ".venv" / "Scripts" / "python.exe"
                if not venv_python.exists():
                    venv_python = PROJECT_DIR / ".venv" / "bin" / "python"
                subprocess.run([str(venv_python), "-m", "pip", "install", "-r", "requirements.txt"], check=True, cwd=str(PROJECT_DIR), creationflags=creationflags)
                
                status_var.set("セットアップが完了しました！")
                messagebox.showinfo("成功", "初期セットアップが完了しました。\n「ローカル起動」をお試しください。")
            except Exception as e:
                status_var.set(f"セットアップ失敗: {e}")
                messagebox.showerror("エラー", f"セットアップに失敗しました:\n{e}")
            finally:
                setup_btn.config(state="normal")
        
        import threading
        threading.Thread(target=run_setup, daemon=True).start()

    # 0. 初期セットアップボタン
    setup_btn = ttk.Button(test_tab, text="初期セットアップ (モジュールインストール)", command=handle_setup_env)
    setup_btn.grid(row=0, column=0, sticky="w", pady=(0, 4))
    
    ttk.Label(
        test_tab,
        text="※ 初めてローカル起動を行う前に1回だけ実行してください",
    ).grid(row=1, column=0, sticky="w", pady=(0, 12))

    # 1. ローカル起動ボタン
    ttk.Button(test_tab, text="ローカル起動", command=handle_run_app_py).grid(
        row=2, column=0, sticky="w"
    )
    # 2. ローカル起動説明文
    ttk.Label(
        test_tab,
        text="※ Django開発サーバーはバックグラウンドで起動します。",
    ).grid(row=3, column=0, sticky="w", pady=(6, 12))

    # 3. 実行対象ラベル
    ttk.Label(test_tab, text=f"実行対象: {PROJECT_DIR / 'manage.py'}").grid(
        row=4, column=0, sticky="w", pady=(0, 8)
    )

    # 4. DEBUGモードフレーム
    debug_frame = ttk.LabelFrame(test_tab, text="Django設定 (DEBUG)", style="Manager.TFrame", padding=8)
    debug_frame.grid(row=5, column=0, sticky="ew", pady=(0, 12))
    debug_frame.columnconfigure(0, weight=1)

    ttk.Checkbutton(
        debug_frame,
        text="デバッグモードを有効にする (CSS表示やエラー詳細表示がONになります)",
        variable=debug_var,
        command=on_debug_toggle
    ).grid(row=0, column=0, sticky="w", pady=(0, 4))

    ttk.Label(
        debug_frame,
        textvariable=debug_status_var,
        font=("", 9, "bold")
    ).grid(row=1, column=0, sticky="w")


    ttk.Label(frame, textvariable=status_var).grid(
        row=1, column=0, sticky="w", pady=(10, 0)
    )

    notebook.select(test_tab)

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
