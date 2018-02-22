from channels.routing import route, route_class
from .consumers import ws_message, ws_connect, ws_disconnect
from .registry import DEMULTIPLEXERS
from .registry import EXTRA_ROUTES

channel_routing = [
    route("websocket.connect", ws_connect, path=r"^/tv/$"),
    route("websocket.receive", ws_message, path=r"^/tv/$"),
    route("websocket.disconnect", ws_disconnect, path=r"^/tv/$"),
]

for Demultiplexer in DEMULTIPLEXERS:
    channel_routing.append(
        route_class(Demultiplexer)
    )

for route in EXTRA_ROUTES:
    channel_routing.append(route)
