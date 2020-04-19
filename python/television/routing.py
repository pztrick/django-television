from .registry import EXTRA_ROUTES

from django.urls import re_path

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

from television.consumers import TelevisionConsumer

websocket_urlpatterns = [
    re_path(r'tv/$', TelevisionConsumer),
]

application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})

# @FIXME: enable support for EXTRA_ROUTES
for route in EXTRA_ROUTES:
    raise NotImplementedError('django-television: configuration option EXTRA_ROUTES not implemented')
