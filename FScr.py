import sys
import io
import threading
import time
import os
import ctypes
import tkinter as tk

import mss
from PIL import Image, ImageDraw, ImageTk
import win32clipboard
import win32con
from pystray import Icon, Menu, MenuItem
import keyboard


def log(msg):
    print(f'[ScreenshotTool] {msg}')


def copy_to_clipboard(img):
    output = io.BytesIO()
    img.convert('RGB').save(output, 'BMP')
    data = output.getvalue()[14:]
    output.close()
    
    for _ in range(5):
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_DIB, data)
            win32clipboard.CloseClipboard()
            log('Скриншот скопирован в буфер')
            return
        except:
            time.sleep(0.05)


def show_notification(msg):
    def popup():
        try:
            root = tk.Tk()
            root.withdraw()
            root.after(0, lambda: root.attributes('-topmost', True))
            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()
            root.geometry(f'250x40+{sw - 260}+{sh - 80}')
            frame = tk.Frame(root, bg='#1e1e1e', bd=1, relief='solid')
            frame.pack(fill='both', expand=True)
            tk.Label(frame, text=msg, bg='#1e1e1e', fg='white',
                     font=('Segoe UI', 10), anchor='w').pack(side='left', padx=10)
            root.after(1800, root.destroy)
            root.mainloop()
        except:
            pass
    threading.Thread(target=popup, daemon=True).start()


def do_capture():
    log('Захват начат')
    try:
        with mss.mss() as sct:
            mon = sct.monitors[0]
            raw = sct.grab(mon)
        
        screen = Image.frombytes('RGB', raw.size, raw.bgra, 'raw', 'BGRX')
        sw, sh = raw.size
        
        root = tk.Tk()
        root.overrideredirect(True)
        root.geometry(f'{sw}x{sh}+0+0')
        root.attributes('-topmost', True)
        root.configure(bg='black')
        root.focus_force()
        
        tk_img = ImageTk.PhotoImage(master=root, image=screen)
        canvas = tk.Canvas(root, width=sw, height=sh,
                           highlightthickness=0, cursor='cross')
        canvas.pack()
        canvas.create_image(0, 0, anchor='nw', image=tk_img)
        
        rect_id = [None]
        sx = [0]
        sy = [0]
        
        def press(e):
            sx[0], sy[0] = e.x, e.y
            if rect_id[0]:
                canvas.delete(rect_id[0])
            rect_id[0] = canvas.create_rectangle(
                e.x, e.y, e.x, e.y, outline='red', width=2, dash=(6, 4))
        
        def drag(e):
            if rect_id[0]:
                canvas.delete(rect_id[0])
            rect_id[0] = canvas.create_rectangle(
                sx[0], sy[0], e.x, e.y, outline='red', width=2, dash=(6, 4))
        
        def release(e):
            x1 = min(sx[0], e.x)
            y1 = min(sy[0], e.y)
            x2 = max(sx[0], e.x)
            y2 = max(sy[0], e.y)
            root.quit()
            root.destroy()
            if x2 - x1 > 5 and y2 - y1 > 5:
                cropped = screen.crop((x1, y1, x2, y2))
                copy_to_clipboard(cropped)
                show_notification('Скриншот скопирован')
        
        canvas.bind('<ButtonPress-1>', press)
        canvas.bind('<B1-Motion>', drag)
        canvas.bind('<ButtonRelease-1>', release)
        root.bind('<Escape>', lambda e: root.destroy())
        root.bind('<Button-3>', lambda e: root.destroy())
        
        root.mainloop()
    except:
        pass


def on_hotkey():
    log('Горячая клавиша нажата')
    threading.Thread(target=do_capture, daemon=True).start()


def on_exit(icon, item):
    icon.stop()
    os._exit(0)


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([8, 18, 56, 46], outline='white', width=3)
    d.line([33, 8, 33, 18], fill='white', width=3)
    d.line([27, 10, 39, 10], fill='white', width=3)
    
    icon = Icon('screenshot_tool', img, 'Screenshot Tool',
                menu=Menu(
                    MenuItem('Сделать скриншот', lambda _: on_hotkey()),
                    MenuItem('Выход', on_exit),
                ))
    
    keyboard.add_hotkey('ctrl+alt+s', on_hotkey)
    log('Горячая клавиша: Ctrl+Alt+S')
    
    icon.run()


if __name__ == '__main__':
    main()
