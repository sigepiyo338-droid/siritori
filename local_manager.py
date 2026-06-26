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


def read_game_images() -> tuple[list[str], list[tuple]]:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"db.sqlite3 が見つかりません: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        columns = ["id", "image", "is_approved", "readings", "created_at", "updated_at"]
        rows_cursor = conn.execute(
            """
            SELECT img.id, img.image, img.is_approved,
                   (SELECT GROUP_CONCAT(r.reading, ', ') FROM shiritori_game_imagereading r WHERE r.image_id = img.id) as readings,
                   img.created_at, img.updated_at
            FROM shiritori_game_gameimage img
            ORDER BY img.id DESC
            """
        )
        rows = rows_cursor.fetchall()
    return columns, rows


def set_image_approval(image_id: int, is_approved: bool) -> int:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"db.sqlite3 が見つかりません: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE shiritori_game_gameimage SET is_approved = ? WHERE id = ?",
            (1 if is_approved else 0, image_id)
        )
        updated_rows = cursor.rowcount
        conn.commit()
    return updated_rows


def delete_game_image(image_id: int) -> tuple[int, int]:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"db.sqlite3 が見つかりません: {DB_PATH}")

    image_file_path = None
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT image FROM shiritori_game_gameimage WHERE id = ?", (image_id,))
        row = cursor.fetchone()
        if row:
            image_file_path = row[0]

        cursor.execute("DELETE FROM shiritori_game_imagereading WHERE image_id = ?", (image_id,))
        deleted_readings = cursor.rowcount
        cursor.execute("DELETE FROM shiritori_game_gameimage WHERE id = ?", (image_id,))
        deleted_images = cursor.rowcount
        conn.commit()

    # 画像ファイルの削除
    if image_file_path:
        media_file = MEDIA_ROOT / image_file_path
        if media_file.exists() and media_file.is_file():
            try:
                os.remove(media_file)
            except Exception as e:
                print(f"Failed to delete image file {media_file}: {e}")

    return deleted_images, deleted_readings


def read_image_readings() -> tuple[list[str], list[tuple]]:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"db.sqlite3 が見つかりません: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        columns = ["id", "image_id", "reading", "image", "created_at"]
        rows_cursor = conn.execute(
            """
            SELECT r.id, r.image_id, r.reading, img.image, r.created_at
            FROM shiritori_game_imagereading r
            LEFT JOIN shiritori_game_gameimage img ON r.image_id = img.id
            ORDER BY r.id DESC
            """
        )
        rows = rows_cursor.fetchall()
    return columns, rows


def delete_image_reading(reading_id: int) -> int:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"db.sqlite3 が見つかりません: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM shiritori_game_imagereading WHERE id = ?", (reading_id,))
        deleted_count = cursor.rowcount
        conn.commit()
    return deleted_count


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

    notebook = ttk.Notebook(frame, style="Manager.TNotebook")
    notebook.grid(row=0, column=0, sticky="nsew")

    # ---- 1. バージョン管理タブ ----
    version_tab = ttk.Frame(notebook, style="Manager.TFrame", padding=12)
    version_tab.columnconfigure(1, weight=1)
    notebook.add(version_tab, text="バージョン管理")

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

    # ---- 2. DB管理タブ ----
    db_tab = ttk.Frame(notebook, style="Manager.TFrame", padding=12)
    notebook.add(db_tab, text="DB管理")

    ttk.Label(db_tab, text="db.sqlite3 同期（上書き）").grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
    )
    ttk.Label(db_tab, text=f"ダウンロード元: {DB_URL}").grid(
        row=1, column=0, columnspan=2, sticky="w"
    )
    ttk.Label(db_tab, text=f"保存先: {DB_PATH}").grid(
        row=2, column=0, columnspan=2, sticky="w", pady=(0, 8)
    )

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
            # 他のタブの一覧をリロード
            reload_game_images_ui()
            reload_readings_ui()
        except Exception as exc:
            status_var.set(f"DB同期失敗: {exc}")
            messagebox.showerror("エラー", f"DB同期失敗: {exc}")

    ttk.Button(db_tab, text="現在のDBをバックアップする", command=handle_backup_db).grid(
        row=3, column=0, columnspan=2, sticky="ew", pady=(4, 6)
    )
    ttk.Button(db_tab, text="オンライン版で上書きする", command=handle_sync_db).grid(
        row=4, column=0, columnspan=2, sticky="ew", pady=(0, 6)
    )
    ttk.Label(db_tab, textvariable=db_last_modified_var).grid(
        row=5, column=0, columnspan=2, sticky="w", pady=(0, 6)
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

    # ---- 4. 画像管理タブ ----
    images_tab = ttk.Frame(notebook, style="Manager.TFrame", padding=12)
    images_tab.columnconfigure(0, weight=1)
    images_tab.rowconfigure(2, weight=1)
    notebook.add(images_tab, text="画像管理")

    ttk.Label(images_tab, text="ゲーム画像一覧（db.sqlite3）").grid(
        row=0, column=0, sticky="w", pady=(0, 8)
    )

    images_container = ttk.Frame(images_tab)
    images_container.grid(row=2, column=0, sticky="nsew")
    images_container.columnconfigure(0, weight=1)
    images_container.rowconfigure(0, weight=1)

    images_tree = ttk.Treeview(
        images_container,
        show="headings",
        height=9,
    )
    images_tree.grid(row=0, column=0, sticky="nsew")

    images_scroll_y = ttk.Scrollbar(
        images_container,
        orient="vertical",
        command=images_tree.yview,
    )
    images_scroll_y.grid(row=0, column=1, sticky="ns")
    images_tree.configure(yscrollcommand=images_scroll_y.set)

    images_scroll_x = ttk.Scrollbar(
        images_container,
        orient="horizontal",
        command=images_tree.xview,
    )
    images_scroll_x.grid(row=1, column=0, sticky="ew")
    images_tree.configure(xscrollcommand=images_scroll_x.set)

    images_status_var = tk.StringVar(value="未読込")
    ttk.Label(images_tab, textvariable=images_status_var).grid(
        row=3, column=0, sticky="w", pady=(8, 0)
    )

    def reload_game_images_ui() -> None:
        try:
            columns, rows = read_game_images()

            images_tree.delete(*images_tree.get_children())
            images_tree.configure(columns=columns)
            
            # カラムヘッダーと幅設定
            column_widths = {
                "id": 40,
                "image": 220,
                "is_approved": 60,
                "readings": 200,
                "created_at": 130,
                "updated_at": 130
            }
            
            for column in columns:
                images_tree.heading(column, text=column)
                images_tree.column(column, width=column_widths.get(column, 100), anchor="w")

            for row in rows:
                images_tree.insert("", "end", values=row)

            images_status_var.set(f"{len(rows)} 件表示")
        except Exception as exc:
            images_status_var.set(f"読込失敗: {exc}")
            status_var.set(f"画像タブ読込失敗: {exc}")

    def handle_toggle_approval(approved: bool) -> None:
        selected_items = images_tree.selection()
        if not selected_items:
            messagebox.showwarning("未選択", "処理を行う画像を選択してください。")
            return

        item_id = selected_items[0]
        values = images_tree.item(item_id, "values")
        if not values:
            messagebox.showerror("エラー", "選択行の値を取得できませんでした。")
            return

        try:
            image_id = int(values[0])
        except (TypeError, ValueError):
            messagebox.showerror("エラー", "選択行のIDが不正です。")
            return

        try:
            updated_rows = set_image_approval(image_id, approved)
            reload_game_images_ui()
            status_var.set(f"画像ID {image_id} の承認状態を {approved} に更新しました。")
        except Exception as exc:
            status_var.set(f"承認変更失敗: {exc}")
            messagebox.showerror("エラー", f"承認変更失敗: {exc}")

    def handle_delete_selected_image() -> None:
        selected_items = images_tree.selection()
        if not selected_items:
            messagebox.showwarning("未選択", "削除する行を選択してください。")
            return

        item_id = selected_items[0]
        values = images_tree.item(item_id, "values")
        if not values:
            messagebox.showerror("エラー", "選択行の値を取得できませんでした。")
            return

        try:
            image_id = int(values[0])
        except (TypeError, ValueError):
            messagebox.showerror("エラー", "選択行のIDが不正です。")
            return

        if not messagebox.askyesno(
            "確認",
            f"画像ID={image_id} を削除します。\n"
            "関連する読み方、およびアップロードされた画像ファイルも削除されます。続行しますか？",
        ):
            return

        try:
            deleted_images, deleted_readings = delete_game_image(image_id)
            reload_game_images_ui()
            reload_readings_ui() # 読み方タブも連動してリロード
            status_var.set(
                f"画像ID {image_id} を削除（images:{deleted_images}, readings:{deleted_readings}）"
            )
            messagebox.showinfo(
                "削除完了",
                f"画像レコード: {deleted_images} 件\n"
                f"読み方レコード: {deleted_readings} 件\n"
                "および画像ファイルを削除しました。",
            )
        except Exception as exc:
            status_var.set(f"画像削除失敗: {exc}")
            messagebox.showerror("エラー", f"画像削除失敗: {exc}")

    # ボタンレイアウト
    images_btn_frame = ttk.Frame(images_tab, style="Manager.TFrame")
    images_btn_frame.grid(row=1, column=0, sticky="ew", pady=(0, 6))

    ttk.Button(
        images_btn_frame, text="一覧を再読込", command=reload_game_images_ui
    ).pack(side="left", padx=(0, 6))
    ttk.Button(
        images_btn_frame, text="承認する", command=lambda: handle_toggle_approval(True)
    ).pack(side="left", padx=6)
    ttk.Button(
        images_btn_frame, text="非承認にする", command=lambda: handle_toggle_approval(False)
    ).pack(side="left", padx=6)
    ttk.Button(
        images_btn_frame, text="選択中の画像を削除", command=handle_delete_selected_image
    ).pack(side="right", padx=(6, 0))

    try:
        reload_game_images_ui()
    except Exception:
        pass

    # ---- 5. 読み方管理タブ ----
    readings_tab = ttk.Frame(notebook, style="Manager.TFrame", padding=12)
    readings_tab.columnconfigure(0, weight=1)
    readings_tab.rowconfigure(2, weight=1)
    notebook.add(readings_tab, text="読み方管理")

    ttk.Label(readings_tab, text="画像読み方一覧（db.sqlite3）").grid(
        row=0, column=0, sticky="w", pady=(0, 8)
    )

    readings_container = ttk.Frame(readings_tab)
    readings_container.grid(row=2, column=0, sticky="nsew")
    readings_container.columnconfigure(0, weight=1)
    readings_container.rowconfigure(0, weight=1)

    readings_tree = ttk.Treeview(
        readings_container,
        show="headings",
        height=9,
    )
    readings_tree.grid(row=0, column=0, sticky="nsew")

    readings_scroll_y = ttk.Scrollbar(
        readings_container,
        orient="vertical",
        command=readings_tree.yview,
    )
    readings_scroll_y.grid(row=0, column=1, sticky="ns")
    readings_tree.configure(yscrollcommand=readings_scroll_y.set)

    readings_scroll_x = ttk.Scrollbar(
        readings_container,
        orient="horizontal",
        command=readings_tree.xview,
    )
    readings_scroll_x.grid(row=1, column=0, sticky="ew")
    readings_tree.configure(xscrollcommand=readings_scroll_x.set)

    readings_status_var = tk.StringVar(value="未読込")
    ttk.Label(readings_tab, textvariable=readings_status_var).grid(
        row=3, column=0, sticky="w", pady=(8, 0)
    )

    def reload_readings_ui() -> None:
        try:
            columns, rows = read_image_readings()

            readings_tree.delete(*readings_tree.get_children())
            readings_tree.configure(columns=columns)
            
            column_widths = {
                "id": 50,
                "image_id": 70,
                "reading": 150,
                "image": 250,
                "created_at": 150
            }
            
            for column in columns:
                readings_tree.heading(column, text=column)
                readings_tree.column(column, width=column_widths.get(column, 100), anchor="w")

            for row in rows:
                readings_tree.insert("", "end", values=row)

            readings_status_var.set(f"{len(rows)} 件表示")
        except Exception as exc:
            readings_status_var.set(f"読込失敗: {exc}")
            status_var.set(f"読み方タブ読込失敗: {exc}")

    def handle_delete_selected_reading() -> None:
        selected_items = readings_tree.selection()
        if not selected_items:
            messagebox.showwarning("未選択", "削除する行を選択してください。")
            return

        item_id = selected_items[0]
        values = readings_tree.item(item_id, "values")
        if not values:
            messagebox.showerror("エラー", "選択行の値を取得できませんでした。")
            return

        try:
            reading_id = int(values[0])
        except (TypeError, ValueError):
            messagebox.showerror("エラー", "選択行のIDが不正です。")
            return

        if not messagebox.askyesno(
            "確認",
            f"読み方ID={reading_id} を削除します。続行しますか？",
        ):
            return

        try:
            deleted_count = delete_image_reading(reading_id)
            reload_readings_ui()
            reload_game_images_ui() # 画像タブの読み方列表示も更新するためリロード
            status_var.set(f"読み方ID {reading_id} を削除しました（count: {deleted_count}）")
            messagebox.showinfo("削除完了", f"読み方レコード {deleted_count} 件を削除しました。")
        except Exception as exc:
            status_var.set(f"読み方削除失敗: {exc}")
            messagebox.showerror("エラー", f"読み方削除失敗: {exc}")

    readings_btn_frame = ttk.Frame(readings_tab, style="Manager.TFrame")
    readings_btn_frame.grid(row=1, column=0, sticky="ew", pady=(0, 6))

    ttk.Button(
        readings_btn_frame, text="一覧を再読込", command=reload_readings_ui
    ).pack(side="left", padx=(0, 6))
    ttk.Button(
        readings_btn_frame, text="選択中の読み方を削除", command=handle_delete_selected_reading
    ).pack(side="right", padx=(6, 0))

    try:
        reload_readings_ui()
    except Exception:
        pass

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

    # 終了時のDjangoサーバー停止処理
    def on_closing():
        nonlocal app_server_process
        if app_server_process and app_server_process.poll() is None:
            if messagebox.askyesno("終了確認", "Django開発サーバーも停止しますか？"):
                try:
                    app_server_process.terminate()
                    app_server_process.wait(timeout=2)
                except Exception:
                    pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    return root


if __name__ == "__main__":
    app_ui = build_ui()
    app_ui.mainloop()
