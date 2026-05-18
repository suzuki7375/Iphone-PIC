import platform
import subprocess
import tkinter as tk
from tkinter import messagebox


def run_command(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.returncode, (result.stdout or "") + (result.stderr or "")
    except Exception as exc:
        return 1, str(exc)


def detect_iphone_connected() -> tuple[bool, str]:
    system = platform.system().lower()

    # macOS: use system_profiler to detect iPhone over USB
    if system == "darwin":
        code, output = run_command(["system_profiler", "SPUSBDataType"])
        if code != 0:
            return False, f"無法檢查 USB 裝置：\n{output}"
        keywords = ["iphone", "apple mobile device", "apple iphone"]
        found = any(k in output.lower() for k in keywords)
        return found, "已偵測到 iPhone。" if found else "尚未偵測到 iPhone。"

    # Linux: use lsusb
    if system == "linux":
        code, output = run_command(["lsusb"])
        if code != 0:
            return False, f"無法執行 lsusb：\n{output}"
        keywords = ["iphone", "apple, inc.", "apple mobile"]
        found = any(k in output.lower() for k in keywords)
        return found, "已偵測到 iPhone。" if found else "尚未偵測到 iPhone。"

    # Windows: fallback to PowerShell PnP query
    if system == "windows":
        ps_cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-PnpDevice | Where-Object { $_.FriendlyName -match 'iPhone|Apple Mobile' }",
        ]
        code, output = run_command(ps_cmd)
        if code != 0:
            return False, f"無法檢查裝置：\n{output}"
        found = bool(output.strip())
        return found, "已偵測到 iPhone。" if found else "尚未偵測到 iPhone。"

    return False, f"目前不支援的系統：{platform.system()}"


def run_flow(person_name: str):
    connected, detail = detect_iphone_connected()

    if not connected:
        messagebox.showwarning(
            "未偵測到 iPhone",
            "請先確認 iPhone 已透過 USB Type-C 連接到電腦。\n\n"
            f"系統檢查結果：{detail}",
        )
        return

    trust_ok = messagebox.askyesno(
        "確認信任與解鎖",
        "已偵測到 iPhone。\n\n"
        "請確認手機上是否已按下『信任』，並完成密碼輸入解鎖。\n"
        "如果已完成，請按『是』繼續。",
    )

    if not trust_ok:
        messagebox.showinfo("操作中止", "請先在 iPhone 上完成『信任』與密碼輸入，再重新執行。")
        return

    messagebox.showinfo(
        "檢查完成",
        f"{person_name} 流程已準備完成：\n"
        "1) iPhone 已連線\n"
        "2) 已提醒確認信任與密碼輸入\n\n"
        "下一步可接續執行照片整理程序。",
    )


def build_ui():
    root = tk.Tk()
    root.title("iPhone 照片整理助手")
    root.geometry("420x220")

    label = tk.Label(
        root,
        text="請選擇要執行的流程：\n按下按鈕後會檢查 iPhone 連線與信任狀態",
        font=("Arial", 11),
        justify="center",
    )
    label.pack(pady=20)

    button_frame = tk.Frame(root)
    button_frame.pack(pady=10)

    btn_xiang = tk.Button(
        button_frame,
        text="Xiang",
        width=12,
        height=2,
        command=lambda: run_flow("Xiang"),
    )
    btn_xiang.grid(row=0, column=0, padx=12)

    btn_minju = tk.Button(
        button_frame,
        text="MinJu",
        width=12,
        height=2,
        command=lambda: run_flow("MinJu"),
    )
    btn_minju.grid(row=0, column=1, padx=12)

    tips = tk.Label(
        root,
        text="提示：若未安裝對應驅動/工具，裝置偵測可能失敗。",
        fg="gray",
        font=("Arial", 9),
    )
    tips.pack(pady=20)

    root.mainloop()


if __name__ == "__main__":
    build_ui()
