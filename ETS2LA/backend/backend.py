from ETS2LA.Plugin import *
from ETS2LA.UI import *
import multiprocessing
import threading
import logging
import inspect
import time
import os

plugin_path = "plugins"
plugin_target_class = "Plugin"

AVAILABLE_PLUGINS: list[tuple[str, PluginDescription, Author, ETS2LASettingsMenu]] = []

class PluginHandler:
    
    plugin_name: str
    plugin_description: PluginDescription
    data = None
    
    return_queue: multiprocessing.JoinableQueue
    
    plugins_queue: multiprocessing.JoinableQueue
    plugins_return_queue: multiprocessing.JoinableQueue
    
    tags_queue: multiprocessing.JoinableQueue
    tags_return_queue: multiprocessing.JoinableQueue
    
    tags: dict[str, any]
    
    def __init__(self, plugin_name: str, plugin_description: PluginDescription):
        self.tags = {}
        self.plugin_name = plugin_name
        self.plugin_description = plugin_description
        self.return_queue = multiprocessing.JoinableQueue()
        self.plugins_queue = multiprocessing.JoinableQueue()
        self.plugins_return_queue = multiprocessing.JoinableQueue()
        self.tags_queue = multiprocessing.JoinableQueue()
        self.tags_return_queue = multiprocessing.JoinableQueue()
        self.settings_menu_queue = multiprocessing.JoinableQueue()
        self.settings_menu_return_queue = multiprocessing.JoinableQueue()
        self.frontend_queue = multiprocessing.JoinableQueue()
        self.frontend_return_queue = multiprocessing.JoinableQueue()
        self.process = multiprocessing.Process(target=PluginRunner, args=(self.plugin_name, self.plugin_description,
                                                                          self.return_queue,
                                                                          self.plugins_queue, self.plugins_return_queue,
                                                                          self.tags_queue, self.tags_return_queue,
                                                                          self.settings_menu_queue, self.settings_menu_return_queue,
                                                                          self.frontend_queue, self.frontend_return_queue
                                                                          ), daemon=True)
        self.process.start()
        RUNNING_PLUGINS.append(self)
        threading.Thread(target=self.data_handler, daemon=True).start()
        threading.Thread(target=self.plugins_handler, daemon=True).start()
        threading.Thread(target=self.tags_handler, daemon=True).start()
        
    def tags_handler(self):
        while True:
            tag_dict = self.tags_queue.get()
            if tag_dict["operation"] == "read":
                tag = tag_dict["tag"]
                return_data = {}
                for plugin in RUNNING_PLUGINS:
                    if tag in plugin.tags:
                        return_data[plugin.plugin_name] = plugin.tags[tag]
                self.tags_return_queue.put(return_data)
            elif tag_dict["operation"] == "write":
                self.tags[tag_dict["tag"]] = tag_dict["value"]
                self.tags_return_queue.put(True)
            else:
                self.tags_return_queue.put(False)

    def plugins_handler(self):
        while True:
            plugin_name = self.plugins_queue.get()
            plugins = [plugin.plugin_name for plugin in RUNNING_PLUGINS]
            if plugin_name in plugins:
                index = plugins.index(plugin_name)
                self.plugins_return_queue.put(RUNNING_PLUGINS[index].data)
            else:
                self.plugins_return_queue.put(None)

    def data_handler(self):
        while True:
            if not self.return_queue.empty():
                data = self.return_queue.get()
                self.data = data
            else:
                time.sleep(0.01) # 100fps
                
    def get_settings(self):
        self.settings_menu_queue.put(True)
        return self.settings_menu_return_queue.get()
    
    def call_function(self, name: str, *args, **kwargs):
        self.frontend_queue.put({
            "operation": "function",
            "target": name,
            "args": args,
            "kwargs": kwargs
        })
        return_data = self.frontend_return_queue.get()
        self.frontend_return_queue.task_done()
        return return_data

RUNNING_PLUGINS: list[PluginHandler] = []

def get_plugin_class(module_name):
    module = __import__(module_name, fromlist=['*'])
    for name, cls in inspect.getmembers(module):
        if inspect.isclass(cls) and issubclass(cls, ETS2LAPlugin) and cls != ETS2LAPlugin:
            return cls
    return None

def find_plugins() -> list[tuple[str, PluginDescription, Author]]:
    folders = os.listdir(plugin_path)
    plugins = []
    for folder in folders:
        if "main.py" in os.listdir(f"{plugin_path}/{folder}"):
            plugin_class = get_plugin_class(f"{plugin_path}.{folder}.main")
            if plugin_class is not None:
                information = getattr(plugin_class, "description", None)
                author = getattr(plugin_class, "author", None)
                settings = getattr(plugin_class, "settings_menu", None)
                plugins.append((folder, information, author, settings))
            del plugin_class
            
    return plugins

def enable_plugin(plugin_name: str):
    runner = threading.Thread(target=PluginHandler, args=(plugin_name, PluginDescription()), daemon=True)
    runner.start()
    
def disable_plugin(plugin_name: str):
    for plugin in RUNNING_PLUGINS:
        if plugin.plugin_name == plugin_name:
            plugin.process.terminate()
            RUNNING_PLUGINS.remove(plugin)
            return True
    return False
    
def get_plugin_data(plugin_name: str):
    for plugin in RUNNING_PLUGINS:
        if plugin.plugin_name == plugin_name:
            return plugin.data
    return None

def get_plugin_settings() -> dict[str, None | list]:
    settings_dict = {}
    for name, desc, author, settings in AVAILABLE_PLUGINS:
        if settings is None:
            settings_dict[name] = None
            continue
        
        elif not settings.dynamic:
            settings_dict[name] = settings.build()
            
        elif name in [plugin.plugin_name for plugin in RUNNING_PLUGINS]:
            for plugin in RUNNING_PLUGINS:
                if plugin.plugin_name == name:
                    settings_dict[name] = plugin.get_settings()
                    break
                
        elif name not in [plugin.plugin_name for plugin in RUNNING_PLUGINS]:
            settings_dict[name] = settings.build()
        
        else:
            settings_dict[name] = None
            
    return settings_dict

def run():
    global AVAILABLE_PLUGINS
    AVAILABLE_PLUGINS = find_plugins()
    logging.info(f"Discovered {len(AVAILABLE_PLUGINS)} plugins, of which {len([plugin for plugin in AVAILABLE_PLUGINS if plugin[3] is not None])} have settings menus.")