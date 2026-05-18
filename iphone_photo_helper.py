import os
import platform
import shutil
import subprocess
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox


def run_command(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.returncode, (result.stdout or "") + (result.stderr or "")
    except Exception as exc:
        return 1, str(exc)


def detect_iphone_connected() -> tuple[bool, str]:
    system = platform.system().lower()

    if system == "darwin":
        code, output = run_command(["system_profiler", "SPUSBDataType"])
        if code != 0:
            return False, f"無法檢查 USB 裝置：\n{output}"
        keywords = ["iphone", "apple mobile device", "apple iphone"]
        found = any(k in output.lower() for k in keywords)
        return found, "已偵測到 iPhone。" if found else "尚未偵測到 iPhone。"

    if system == "linux":
        code, output = run_command(["lsusb"])
        if code != 0:
            return False, f"無法執行 lsusb：\n{output}"
        keywords = ["iphone", "apple, inc.", "apple mobile"]
        found = any(k in output.lower() for k in keywords)
        return found, "已偵測到 iPhone。" if found else "尚未偵測到 iPhone。"

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


def parse_date(date_text: str) -> datetime:
    text = date_text.strip()
    if '-' in text:
        raise ValueError('日期不可包含 -')
    return datetime.strptime(text, "%Y%m%d")


def is_photo_file(path: Path) -> bool:
    return path.suffix.lower() in {".jpg", ".jpeg", ".png", ".heic", ".mov", ".mp4", ".gif"}


def guess_iphone_photo_source() -> Path | None:
    """嘗試推測 iPhone 已掛載後最可能的照片來源資料夾。"""
    system = platform.system().lower()
    home = Path.home()

    candidates: list[Path] = []
    if system == "darwin":
        candidates.extend(
            [
                Path("/Volumes"),
                Path("/Volumes/iPhone"),
            ]
        )
    elif system == "linux":
        candidates.extend(
            [
                Path("/run/user") / str(os.getuid()) / "gvfs",
                home / "手機",
                home / "Phone",
            ]
        )
    elif system == "windows":
        candidates.extend([home / "Pictures", Path("C:/")])

    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def copy_photos_by_date(source_dir: Path, target_root: Path, prefix: str, start_date: datetime, end_date: datetime) -> tuple[int, Path]:
    date_range_text = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
    target_dir = target_root / f"{prefix}_{date_range_text}"
    target_dir.mkdir(parents=True, exist_ok=True)

    copied_count = 0
    start_ts = datetime.combine(start_date.date(), datetime.min.time()).timestamp()
    end_ts = datetime.combine(end_date.date(), datetime.max.time()).timestamp()

    for root, _, files in os.walk(source_dir):
        for filename in files:
            src_file = Path(root) / filename
            if not is_photo_file(src_file):
                continue

            try:
                file_ts = src_file.stat().st_mtime
            except OSError:
                continue

            if start_ts <= file_ts <= end_ts:
                dst_file = target_dir / src_file.name
                if dst_file.exists():
                    stem = dst_file.stem
                    suffix = dst_file.suffix
                    idx = 1
                    while True:
                        candidate = target_dir / f"{stem}_{idx}{suffix}"
                        if not candidate.exists():
                            dst_file = candidate
                            break
                        idx += 1
                shutil.copy2(src_file, dst_file)
                copied_count += 1

    return copied_count, target_dir


def run_photo_export(person_name: str, start_text: str, end_text: str, custom_name: str):
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
        return

    try:
        start_date = parse_date(start_text)
        end_date = parse_date(end_text)
    except ValueError:
        messagebox.showerror("日期格式錯誤", "請使用 YYYYMMDD 格式，例如 20260518（不可包含 -）")
        return

    if start_date > end_date:
        messagebox.showerror("日期區間錯誤", "開始日期不能晚於結束日期。")
        return

    prefix = custom_name.strip() or person_name

    source_hint = guess_iphone_photo_source()

    if platform.system().lower() == "windows":
        messagebox.showinfo(
            "Windows 提示",
            "若視窗中看不到 iPhone 裝置，請先在檔案總管打開 iPhone 的 DCIM，\n"
            "再把照片複製到本機資料夾後，於此程式選擇該本機資料夾。"
        )

    source = filedialog.askdirectory(
        title="請選擇 iPhone 照片來源資料夾（例如 DCIM）",
        initialdir=str(source_hint) if source_hint else str(Path.home()),
        mustexist=True,
    )
    if not source:
        messagebox.showwarning("未選擇來源", "未選擇 iPhone 照片來源資料夾，已取消。")
        return

    target = filedialog.askdirectory(title="請選擇照片複製輸出資料夾")
    if not target:
        messagebox.showwarning("未選擇輸出", "未選擇輸出資料夾，已取消。")
        return

    copied_count, out_dir = copy_photos_by_date(
        Path(source),
        Path(target),
        prefix,
        start_date,
        end_date,
    )

    messagebox.showinfo(
        "完成",
        f"已完成照片篩選與複製。\n\n"
        f"區間：{start_date.strftime('%Y%m%d')} ~ {end_date.strftime('%Y%m%d')}\n"
        f"輸出資料夾：{out_dir}\n"
        f"複製檔案數量：{copied_count}",
    )


def open_date_window(person_name: str):
    win = tk.Toplevel()
    win.title(f"{person_name} - 選擇照片建立時間區間")
    win.geometry("420x280")

    tk.Label(win, text="開始日期 (YYYYMMDD)").pack(pady=(16, 4))
    start_entry = tk.Entry(win, width=24)
    start_entry.pack()

    tk.Label(win, text="結束日期 (YYYYMMDD)").pack(pady=(14, 4))
    end_entry = tk.Entry(win, width=24)
    end_entry.pack()

    tk.Label(win, text="檔案名稱前綴（可自訂）").pack(pady=(14, 4))
    name_entry = tk.Entry(win, width=24)
    name_entry.insert(0, person_name)
    name_entry.pack()

    tk.Label(win, text="範例輸出資料夾：Xiang_20260101_20260131", fg="gray").pack(pady=(12, 10))

    tk.Button(
        win,
        text="開始複製照片",
        width=18,
        height=2,
        command=lambda: run_photo_export(person_name, start_entry.get(), end_entry.get(), name_entry.get()),
    ).pack()


def build_ui():
    root = tk.Tk()
    root.title("iPhone 照片整理助手")
    root.geometry("460x260")

    label = tk.Label(
        root,
        text="請選擇流程\n1) 進入手機照片\n2) 選建立時間區間\n3) 依區間複製並用名稱+日期命名",
        font=("Arial", 11),
        justify="center",
    )
    label.pack(pady=20)

    button_frame = tk.Frame(root)
    button_frame.pack(pady=10)

    tk.Button(
        button_frame,
        text="Xiang",
        width=12,
        height=2,
        command=lambda: open_date_window("Xiang"),
    ).grid(row=0, column=0, padx=12)

    tk.Button(
        button_frame,
        text="MinJu",
        width=12,
        height=2,
        command=lambda: open_date_window("MinJu"),
    ).grid(row=0, column=1, padx=12)

    tips = tk.Label(
        root,
        text="提示：請先將 iPhone 照片掛載為可讀取資料夾，再由程式選取來源。",
        fg="gray",
        font=("Arial", 9),
    )
    tips.pack(pady=20)

    root.mainloop()


if __name__ == "__main__":
    try:
        build_ui()
    except KeyboardInterrupt:
        pass
