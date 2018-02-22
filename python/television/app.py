from django.apps import AppConfig, apps
import importlib
import traceback

from .registry import LISTENERS

class AppConfig(AppConfig): # Our app config class
    name = 'television'
    verbose_name = 'Television'

    def ready(self):
        # 1) Register all listeners
        for app in apps.app_configs.keys():
            app_config = apps.app_configs[app]
            module_name = f'{app_config.module.__name__}.listeners'
            try:
                importlib.import_module(module_name)
            except ModuleNotFoundError as ex:
                if 'listeners' not in ex.name:
                    raise # import failed within module.listeners source
                pass  # This means module.listeners does not exist.
            except ImportError:
                raise  # Syntax/other error. Raise.
        if LISTENERS:
            print('\n[django-television]')
            for listener, fn in LISTENERS.items():
                print(f'\t* {listener}: {fn}')
            print('\n')
        else:
            print('\n[django-television] No listeners.py found for INSTALLED_APPS modules.')

        import television.decorators
        television.decorators.APPS_FINISHED_LOADING = True