from ETS2LA.frontend.webpageExtras.utils import ColorTitleBar, CheckIfWindowStillOpen, get_screen_dimensions, check_valid_window_position, get_theme, window_position
from ETS2LA.frontend.webpageExtras.html import html
import ETS2LA.variables as variables
import ETS2LA.backend.settings as settings
from multiprocessing import JoinableQueue
import multiprocessing  
import logging
import webview
import time
import os

if os.name == 'nt':
    import win32gui

DEBUG_MODE = settings.Get("global", "debug_mode", False)
FRONTEND_PORT = settings.Get("global", "frontend_port", 3005)

queue:JoinableQueue = JoinableQueue()

webview.settings = {
    'ALLOW_DOWNLOADS': False,
    'ALLOW_FILE_URLS': True,
    'OPEN_EXTERNAL_LINKS_IN_BROWSER': True,
    'OPEN_DEVTOOLS_IN_DEBUG': True
}

def set_on_top(state: bool):
    queue.put({"type": "stay_on_top", "state": state})
    # Wait for the queue to be processed
    queue.join()
    value = queue.get()
    queue.task_done()
    return value

def get_on_top():
    queue.put({"type": "stay_on_top", "state": None})
    queue.join() # Wait for the queue to be processed
    value = queue.get()
    queue.task_done()
    return value

def minimize_window():
    queue.put({"type": "minimize"})
    queue.join() # Wait for the queue to be processed
    value = queue.get()
    queue.task_done()
    return value

def start_webpage(queue: JoinableQueue):
    global webview_window
    
    def load_website(window:webview.Window):
        time.sleep(3)
        window.load_url('http://localhost:' + str(FRONTEND_PORT))
        while True:
            time.sleep(0.01)
            try:
                data = queue.get_nowait()
                
                if data["type"] == "stay_on_top":
                    if data["state"] == None:
                        queue.task_done()
                        queue.put(window.on_top)
                        continue
                    
                    window.on_top = data["state"]
                    queue.task_done()
                    queue.put(data["state"])
                    
                if data["type"] == "minimize":
                    window.minimize()
                    queue.task_done()
                    queue.put(True)
                    
            except:
                pass

    window_x = settings.Get("global", "window_position", (get_screen_dimensions()[2]//2 - 1280//2, get_screen_dimensions()[3]//2 - 720//2))[0]
    window_y = settings.Get("global", "window_position", (get_screen_dimensions()[2]//2 - 1280//2, get_screen_dimensions()[3]//2 - 720//2))[1]

    window_x, window_y = check_valid_window_position(window_x, window_y)

    window = webview.create_window(
        f'ETS2LA - Tumppi066 & Contributors © {variables.YEAR}', 
        html=html, 
        x = window_x,
        y = window_y,
        width=1280, 
        height=720,
        background_color=get_theme(),
        resizable=True, 
        zoomable=True,
        confirm_close=False, 
        text_select=True,
        frameless=True, 
        easy_drag=False
    )
    
    webview_window = window
    
    webview.start(
        load_website, 
        window,
        private_mode=False, # Save cookies, local storage and cache
        debug=DEBUG_MODE, # Show developer tools
        storage_path=f"{variables.PATH}cache"
    )

def run():
    p = multiprocessing.Process(target=start_webpage, args=(queue, ), daemon=True)
    p.start()
    if os.name == 'nt':
        ColorTitleBar()
        logging.info('ETS2LA UI opened.')