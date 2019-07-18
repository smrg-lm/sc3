"""Platform.sc"""

from pathlib import Path # es el equivalente a sclang PathName


class Platform():
    # TODO: lo anterior


    # // directories
    # TODO: revisar si estos métodos de clase no podrían ser de instancia con valores por defecto.
    # TODO: en los métodos de clase llama a ^thisProcess.platform que se inicializa en Main que es un Process.
    # TODO: en Python no pueden haber métodos de clase e instancia con el mismo nombre.
    def class_library_dir(self): pass # BUG: TODO: ver la manera Python.
    def help_dir(self): pass # BUG: TODO: ver la manera Python.
    def user_home_dir(self): return Path('~').expanduser()
    def system_app_support_dir(self): pass
    @staticmethod
    def user_app_support_dir(): return Path('~/.local/share/SuperCollider').expanduser()
    def system_extension_dir(self): pass # Alla Python
    def user_extension_dir(self): pass # Alla Python
    def user_config_dir(self): pass
    def resource_dir(self): pass
    def recordings_dir(self): pass
    def default_tmp_dir(self): pass


    # TODO: lo siguiente
