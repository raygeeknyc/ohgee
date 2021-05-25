#!/usr/bin/python3
import logging

# reorder as appropriate
_DEBUG = logging.DEBUG
_DEBUG = logging.INFO

import tkinter as tk
import PIL
from PIL import ImageTk, Image

import time
import io
import sys

def maintainDisplay(root_window):
    image = Image.open('resources/test.jpg')
    tk_image = ImageTk.PhotoImage(image)
    tk.Label(root_window, image=tk_image).pack()
    root_window.mainloop()
    time.sleep(3)
    root_window.quit()
    
if __name__ == '__main__':
    root = tk.Tk()
    root.wm_attributes('-type', 'splash')
    root.geometry("%dx%d+%d+%d" % (root.winfo_screenwidth(), root.winfo_screenheight(), 0, 0))
    print("%dx%d" % (root.winfo_screenwidth(), root.winfo_screenheight()))

    maintainDisplay(root)
    sys.exit(0)
