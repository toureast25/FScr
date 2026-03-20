import io
import threading
import time
import os
import ctypes
import tkinter as tk
import mss
import keyboard
import win32clipboard
import win32con
from PIL import Image, ImageDraw, ImageTk
from pystray import Icon, Menu, MenuItem

# ========== НАСТРАИВАЕМЫЕ ПАРАМЕТРЫ ==========
HOTKEY = 'ctrl+alt+s'
CANCEL_KEYS = ['<Escape>', '<Button-3>']
FRAME_COLOR = 'red'
FRAME_WIDTH = 2
MIN_CROP_SIZE = 5
TOAST_DURATION = 1500
TOAST_SIZE = "200x30"
TOAST_POSITION_OFFSET = (210, 70)
# =============================================

def copy_to_clipboard(img):
    output = io.BytesIO()
    img.convert('RGB').save(output, 'BMP')
    data = output.getvalue()[14:]
    for _ in range(5):
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_DIB, data)
            win32clipboard.CloseClipboard()
            return True
        except:
            time.sleep(0.05)
    return False

def show_toast(msg):
    def run():
        root = tk.Tk()
        root.overrideredirect(True)
        root.attributes('-topmost', True)
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        x = sw - TOAST_POSITION_OFFSET[0]
        y = sh - TOAST_POSITION_OFFSET[1]
        root.geometry(f'{TOAST_SIZE}+{x}+{y}')
        tk.Label(root, text=msg, bg='#2b2b2b', fg='white').pack(fill='both', expand=True)
        root.after(TOAST_DURATION, root.destroy)
        root.mainloop()
    threading.Thread(target=run, daemon=True).start()

class CaptureTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self._init_capture()

    def _init_capture(self):
        with mss.mss() as sct:
            self.mon = sct.monitors[0]
            sct_img = sct.grab(self.mon)
            self.screen = Image.frombytes('RGB', (self.mon['width'], self.mon['height']),
                                        sct_img.bgra, 'raw', 'BGRX')

        self.root.deiconify()
        self.root.focus_force()
        self.root.grab_set()
        self.root.attributes('-topmost', True)
        self.root.geometry(f"{self.mon['width']}x{self.mon['height']}+0+0")
        self.root.config(cursor='cross')

        self.canvas = tk.Canvas(self.root, cursor='cross', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)

        self.tk_img = ImageTk.PhotoImage(self.screen)
        self.screen_ref = self.screen
        self.canvas.create_image(0, 0, anchor='nw', image=self.tk_img)

        self.rect = None
        self.start_x = self.start_y = 0

        self.root.bind('<ButtonPress-1>', self.on_press)
        self.root.bind('<B1-Motion>', self.on_drag)
        self.root.bind('<ButtonRelease-1>', self.on_release)

        for key in CANCEL_KEYS:
            self.root.bind(key, lambda e: self.root.destroy())

        self.root.update_idletasks()
        self.root.mainloop()

    def on_press(self, e):
        self.start_x, self.start_y = e.x, e.y
        self.rect = self.canvas.create_rectangle(
            e.x, e.y, e.x, e.y,
            outline=FRAME_COLOR,
            width=FRAME_WIDTH
        )

    def on_drag(self, e):
        self.canvas.coords(self.rect, self.start_x, self.start_y, e.x, e.y)

    def on_release(self, e):
        x1, y1 = min(self.start_x, e.x), min(self.start_y, e.y)
        x2, y2 = max(self.start_x, e.x), max(self.start_y, e.y)
        self.root.destroy()
        if (x2 - x1) > MIN_CROP_SIZE and (y2 - y1) > MIN_CROP_SIZE:
            crop = self.screen.crop((x1, y1, x2, y2))
            if copy_to_clipboard(crop):
                show_toast("Скопировано!")

def create_capture_window():
    CaptureTool()

def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    def run_capture():
        threading.Thread(target=create_capture_window, daemon=True).start()

    icon_img = Image.new('RGB', (64, 64), (40, 40, 40))
    d = ImageDraw.Draw(icon_img)
    d.rectangle([10, 10, 54, 54], outline='white', width=4)

    icon = Icon('FScr', icon_img, 'FScr', menu=Menu(
        MenuItem('Скриншот', run_capture, default=True),
        MenuItem('Выход', lambda i, m: [i.stop(), os._exit(0)])
    ))

    keyboard.add_hotkey(HOTKEY, run_capture, suppress=True)
    icon.run_detached()
    keyboard.wait()

if __name__ == '__main__':
    main()
