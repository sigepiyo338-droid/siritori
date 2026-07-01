import tkinter as tk
from tkinter import ttk

def build_ui() -> tk.Tk:
    root = tk.Tk()
    root.title("2択くん管理ツール (移行済み)")
    root.geometry("400x200")
    
    frame = ttk.Frame(root, padding=20)
    frame.pack(expand=True, fill="both")
    
    ttk.Label(frame, text="このツールは siritori/local_manager.py に統合されました。", font=("", 10, "bold")).pack(pady=20)
    ttk.Label(frame, text="siritori フォルダの local_manager.py を起動し、\n「2択くん管理」タブから各機能をご利用ください。").pack()
    
    ttk.Button(frame, text="閉じる", command=root.destroy).pack(pady=20)
    
    return root

if __name__ == "__main__":
    app_ui = build_ui()
    app_ui.mainloop()
