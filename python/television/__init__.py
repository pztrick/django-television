# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

default_app_config = 'television.app.AppConfig'

from .decorators import add_listener, call_listener, require_auth, require_staff, require_superuser, add_data_binding_staff, add_data_binding_superuser, add_data_binding_owner