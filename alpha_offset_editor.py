"""Standalone visual Alpha 1 Pro servo-offset editor for Windows."""

from __future__ import annotations

import argparse
import json
import sys
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageTk


if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).resolve().parent
    RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", ROOT))
else:
    ROOT = Path(__file__).resolve().parent
    RESOURCE_ROOT = ROOT
VID, PID = 0x0483, 0x5750

SERVO_NAMES = {
    1: "right hand 3", 2: "right hand 2", 3: "right hand 1",
    4: "left hand 3", 5: "left hand 2", 6: "left hand 1",
    7: "right leg 5", 8: "right leg 4", 9: "right leg 3",
    10: "right leg 2", 11: "right leg 1",
    12: "left leg 5", 13: "left leg 4", 14: "left leg 3",
    15: "left leg 2", 16: "lift leg 1",
}

# Coordinates are taken from the original AlphaRobot Editor map, not inferred
# from a generic humanoid drawing. The background image is the original map.
JOINTS = {
    1: (117, 84), 2: (97, 123), 3: (87, 154),
    4: (188, 84), 5: (198, 123), 6: (208, 154),
    7: (127, 133), 8: (127, 166), 9: (127, 205), 10: (117, 235), 11: (107, 270),
    12: (168, 133), 13: (168, 166), 14: (168, 205), 15: (178, 235), 16: (190, 270),
}


def packet(command: int, servo_id: int, value: int = 0) -> bytes:
    raw = value & 0xFFFF
    hi, lo = (raw >> 8) & 0xFF, raw & 0xFF
    checksum = (command + servo_id + hi + lo) & 0xFF
    return bytes([0xFA, 0xAF, servo_id, command, 0, 0, hi, lo, checksum, 0xED])


class AlphaUsb:
    def __init__(self):
        try:
            import hid  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Не найден hidapi. Установи: python -m pip install --user hidapi") from exc
        self.hid = hid
        devices = hid.enumerate(VID, PID)
        if not devices:
            raise RuntimeError("Alpha1 не найден по USB (VID 0483 / PID 5750)")
        self.device = hid.device()
        self.device.open_path(devices[0]["path"])

    def close(self):
        self.device.close()

    def transact(self, data: bytes):
        self.device.write(bytes([0]) + data)
        return list(self.device.read(64, 350))

    def get_offset(self, servo_id: int) -> int:
        response = self.transact(packet(0xD4, servo_id))
        if len(response) < 8:
            raise RuntimeError(f"Нет ответа от ID{servo_id}: {response}")
        return int.from_bytes(bytes(response[6:8]), "big", signed=True)

    def set_offset(self, servo_id: int, value: int) -> int:
        self.transact(packet(0xD2, servo_id, value))
        return self.get_offset(servo_id)


class OffsetEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Alpha 1 Pro — Servo Offset Editor")
        icon_path = RESOURCE_ROOT / "AlphaRobot.ico"
        if icon_path.exists():
            self.iconbitmap(default=str(icon_path))
        self.geometry("1030x720")
        self.minsize(900, 620)
        self.usb: AlphaUsb | None = None
        self.current: dict[int, int] = {}
        self.entries: dict[int, tk.StringVar] = {}
        self.status_vars: dict[int, tk.StringVar] = {}
        self.row_frames: dict[int, tk.Frame] = {}
        self.joint_items: dict[int, tuple[int, int]] = {}
        self.map_photo = None
        self.backup_path: Path | None = None
        self._build()
        self.after(250, self.connect_and_read)

    def _build(self):
        style = ttk.Style(self)
        style.configure("Header.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("Small.TLabel", font=("Segoe UI", 9))
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        ttk.Button(top, text="Подключить / перечитать", command=self.connect_and_read).pack(side="left")
        ttk.Button(top, text="Применить все", command=self.apply_all).pack(side="left", padx=(8, 0))
        self.connection_var = tk.StringVar(value="Подключение...")
        ttk.Label(top, textvariable=self.connection_var).pack(side="left", padx=14)
        self.global_status = tk.StringVar(value="Запись происходит только по нажатию кнопки.")
        ttk.Label(top, textvariable=self.global_status, style="Small.TLabel").pack(side="right")

        body = ttk.Frame(self, padding=(8, 0, 8, 8))
        body.pack(fill="both", expand=True)
        left = ttk.LabelFrame(body, text="Карта сервоприводов", padding=8)
        left.pack(side="left", fill="y")
        self.canvas = tk.Canvas(left, width=307, height=294, bg="#242424", highlightthickness=0)
        self.canvas.pack()
        self._draw_robot()
        ttk.Label(left, text="Оригинальная карта AlphaRobot Editor. Нажми на ID.", style="Small.TLabel").pack(pady=(8, 0))

        right = ttk.LabelFrame(body, text="Оффсеты EEPROM", padding=8)
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))
        header = ttk.Frame(right)
        header.pack(fill="x")
        for text, width in (("ID", 5), ("Сервопривод", 20), ("Текущее / новое", 17), ("Быстро", 18), ("Состояние", 28)):
            ttk.Label(header, text=text, width=width, style="Header.TLabel").pack(side="left")
        self.rows = ttk.Frame(right)
        self.rows.pack(fill="both", expand=True, pady=(5, 0))
        for servo_id in range(1, 17):
            self._make_row(servo_id)

    def _draw_robot(self):
        c = self.canvas
        original_map = RESOURCE_ROOT / "alpha_joint_map.png"
        if original_map.exists():
            image = Image.open(original_map).convert("RGB")
            self.map_photo = ImageTk.PhotoImage(image)
            c.configure(width=image.width, height=image.height)
            c.create_image(0, 0, anchor="nw", image=self.map_photo)
            c.bind("<Button-1>", self._map_click)
            for servo_id, (x, y) in JOINTS.items():
                halo = c.create_oval(x - 14, y - 14, x + 14, y + 14, outline="", width=3, tags=(f"joint_{servo_id}",))
                text = c.create_text(x, y, text=str(servo_id), fill="", tags=(f"joint_{servo_id}",))
                self.joint_items[servo_id] = (halo, text)
                c.tag_bind(f"joint_{servo_id}", "<Button-1>", lambda _event, i=servo_id: self.select_row(i))
            return

        # Fallback if the reference image is missing from a copied installation.
        c.create_oval(130, 22, 170, 62, fill="#efefef", outline="#777")
        c.create_oval(107, 66, 193, 128, fill="#efefef", outline="#777")
        c.create_rectangle(125, 120, 175, 280, fill="#d8d8d8", outline="#777")
        c.create_line(126, 82, 82, 92, 48, 133, 34, 172, fill="#efefef", width=16, smooth=True)
        c.create_line(174, 82, 218, 92, 252, 133, 268, 172, fill="#efefef", width=16, smooth=True)
        c.create_line(122, 130, 122, 171, 122, 216, 103, 262, 86, 306, fill="#efefef", width=20, smooth=True)
        c.create_line(178, 130, 178, 171, 178, 216, 197, 262, 214, 306, fill="#efefef", width=20, smooth=True)
        c.create_oval(92, 278, 126, 323, fill="#efefef", outline="#777")
        c.create_oval(174, 278, 222, 323, fill="#efefef", outline="#777")
        for servo_id, (x, y) in JOINTS.items():
            halo = c.create_oval(x - 13, y - 13, x + 13, y + 13, fill="#1595d1", outline="#07151d", width=2, tags=(f"joint_{servo_id}",))
            text = c.create_text(x, y, text=str(servo_id), fill="white", font=("Segoe UI", 9, "bold"), tags=(f"joint_{servo_id}",))
            self.joint_items[servo_id] = (halo, text)
            c.tag_bind(f"joint_{servo_id}", "<Button-1>", lambda _event, i=servo_id: self.select_row(i))

    def _map_click(self, event):
        nearest_id, nearest_distance = min(
            ((servo_id, (event.x - x) ** 2 + (event.y - y) ** 2) for servo_id, (x, y) in JOINTS.items()),
            key=lambda item: item[1],
        )
        if nearest_distance <= 28 ** 2:
            self.select_row(nearest_id)

    def _make_row(self, servo_id: int):
        frame = tk.Frame(self.rows, bg=self.cget("background"))
        frame.pack(fill="x", pady=1)
        self.row_frames[servo_id] = frame
        ttk.Label(frame, text=f"{servo_id:02d}", width=5).pack(side="left")
        ttk.Label(frame, text=SERVO_NAMES[servo_id], width=20).pack(side="left")
        var = tk.StringVar(value="—")
        self.entries[servo_id] = var
        ttk.Entry(frame, textvariable=var, width=10, justify="center").pack(side="left")
        ttk.Button(frame, text="−1", width=4, command=lambda i=servo_id: self.nudge(i, -1)).pack(side="left", padx=(6, 1))
        ttk.Button(frame, text="+1", width=4, command=lambda i=servo_id: self.nudge(i, 1)).pack(side="left", padx=1)
        ttk.Button(frame, text="Записать", width=10, command=lambda i=servo_id: self.write_one(i)).pack(side="left", padx=(5, 8))
        status = tk.StringVar(value="не прочитан")
        self.status_vars[servo_id] = status
        ttk.Label(frame, textvariable=status, width=28).pack(side="left")

    def select_row(self, servo_id: int):
        for i, frame in self.row_frames.items():
            frame.configure(bg="#24465d" if i == servo_id else self.cget("background"))
        for i, (halo, _text) in self.joint_items.items():
            # Keep the original map's numbers visible; only outline the selected ID.
            self.canvas.itemconfigure(halo, fill="", outline="#ff9f1c" if i == servo_id else "", width=3)

    def connect_and_read(self):
        self.connection_var.set("Подключение...")
        self.global_status.set("Читаю текущие оффсеты...")
        threading.Thread(target=self._read_worker, daemon=True).start()

    def _read_worker(self):
        try:
            if self.usb:
                self.usb.close()
            usb = AlphaUsb()
            values = {i: usb.get_offset(i) for i in range(1, 17)}
            self.after(0, lambda: self._read_done(usb, values, None))
        except Exception as exc:
            self.after(0, lambda: self._read_done(None, {}, str(exc)))

    def _read_done(self, usb, values, error):
        if error:
            self.connection_var.set("Alpha не подключён")
            self.global_status.set(error)
            return
        self.usb = usb
        self.current = values
        for i, value in values.items():
            self.entries[i].set(str(value))
            self.status_vars[i].set("прочитан")
        self.connection_var.set("Alpha1 подключён по USB HID")
        self.global_status.set("Значения прочитаны; можно менять по одной серве.")

    def ensure_backup(self):
        if self.backup_path:
            return
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = ROOT / f"alpha-offsets-backup-{stamp}.json"
        path.write_text(json.dumps({str(k): v for k, v in self.current.items()}, indent=2), encoding="utf-8")
        self.backup_path = path
        self.global_status.set(f"Резервная копия: {path.name}")

    def parse_value(self, servo_id: int) -> int:
        value = int(self.entries[servo_id].get().strip())
        if not -32768 <= value <= 32767:
            raise ValueError("Оффсет должен быть от −32768 до +32767")
        return value

    def nudge(self, servo_id: int, delta: int):
        try:
            value = self.parse_value(servo_id) + delta
            self.entries[servo_id].set(str(value))
            self.write_value(servo_id, value, ask=False)
        except Exception as exc:
            messagebox.showerror("Оффсет", str(exc))

    def write_one(self, servo_id: int):
        if not self.usb:
            messagebox.showerror("Нет подключения", "Сначала подключи Alpha по USB и перечитай значения.")
            return
        try:
            value = self.parse_value(servo_id)
        except Exception as exc:
            messagebox.showerror("Оффсет", str(exc))
            return
        self.write_value(servo_id, value, ask=True)

    def write_value(self, servo_id: int, value: int, ask: bool):
        if not self.usb:
            messagebox.showerror("Нет подключения", "Сначала подключи Alpha по USB и перечитай значения.")
            return
        if ask and not messagebox.askyesno("Записать оффсет", f"ID{servo_id:02d} ({SERVO_NAMES[servo_id]}): записать {value:+d}°?"):
            return
        self.ensure_backup()
        self.status_vars[servo_id].set("запись...")
        threading.Thread(target=self._write_worker, args=(servo_id, value), daemon=True).start()

    def _write_worker(self, servo_id: int, value: int):
        try:
            checked = self.usb.set_offset(servo_id, value) if self.usb else None
            self.after(0, lambda: self._write_done(servo_id, value, checked, None))
        except Exception as exc:
            self.after(0, lambda: self._write_done(servo_id, value, None, str(exc)))

    def _write_done(self, servo_id, requested, checked, error):
        if error:
            self.status_vars[servo_id].set("ошибка: " + error[:22])
            return
        self.current[servo_id] = checked
        self.entries[servo_id].set(str(checked))
        self.status_vars[servo_id].set(f"записан, подтверждено {checked:+d}")
        self.global_status.set(f"ID{servo_id:02d} изменён: {requested:+d} → {checked:+d}")

    def apply_all(self):
        if not self.usb:
            messagebox.showerror("Нет подключения", "Сначала подключи Alpha по USB.")
            return
        try:
            values = {i: self.parse_value(i) for i in range(1, 17)}
        except Exception as exc:
            messagebox.showerror("Оффсеты", str(exc))
            return
        changes = {i: v for i, v in values.items() if self.current.get(i) != v}
        if not changes:
            messagebox.showinfo("Оффсеты", "Изменений нет.")
            return
        if not messagebox.askyesno("Применить все", f"Записать изменений: {len(changes)}? Робот должен быть надёжно поддержан."):
            return
        self.ensure_backup()
        threading.Thread(target=self._apply_worker, args=(changes,), daemon=True).start()

    def _apply_worker(self, changes):
        for servo_id, value in changes.items():
            try:
                self.after(0, lambda i=servo_id: self.status_vars[i].set("запись..."))
                checked = self.usb.set_offset(servo_id, value) if self.usb else None
                self.current[servo_id] = checked
                self.after(0, lambda i=servo_id, v=checked: self._write_done(i, v, v, None))
            except Exception as exc:
                self.after(0, lambda i=servo_id, e=str(exc): self._write_done(i, 0, None, e))
        self.after(0, lambda: self.global_status.set("Пакетная запись завершена."))


def check_mode():
    usb = AlphaUsb()
    try:
        values = {i: usb.get_offset(i) for i in range(1, 17)}
        print(json.dumps(values, indent=2))
    finally:
        usb.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="прочитать оффсеты и выйти без GUI/записи")
    args = parser.parse_args()
    if args.check:
        check_mode()
    else:
        app = OffsetEditor()
        app.mainloop()
