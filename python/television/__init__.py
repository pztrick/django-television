# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

import sys

__version__ = "0.1.7"

if sys.version_info < (3, 6):
    raise RuntimeError("django-television requires Python 3.6 or later.")

default_app_config = 'television.app.AppConfig'

try:
    from .decorators import add_listener, call_listener, require_auth, require_staff, require_superuser, add_data_binding_staff, add_data_binding_superuser, add_data_binding_owner
except ImportError:
    pass