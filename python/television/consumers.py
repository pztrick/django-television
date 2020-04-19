from django.conf import settings
from django.db import connection
import traceback
from television.utils import timestamp
from television.decorators import call_listener
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer, JsonWebsocketConsumer, AsyncJsonWebsocketConsumer

class TelevisionConsumer(JsonWebsocketConsumer):
    def relay(self, event):
        """ custom handler invoked by television.utils.send_to_group """
        print(f'ws_relay: {event}')
        self.send_json(content=event)

    def connect(self):
        if self.scope['user'].is_authenticated:
            # @FIXME should improve Channels to throw exception if running group_add without async_to_sync here in a synchronous fn ?
            async_to_sync(self.channel_layer.group_add)(f"users", self.channel_name)
            async_to_sync(self.channel_layer.group_add)(f"users.{self.scope['user'].id}", self.channel_name)
            print(f"ws_connect: added to group 'users'")
        if self.scope['user'].is_superuser:
            async_to_sync(self.channel_layer.group_add)("superusers", self.channel_name)
            print("ws_connect: added to group 'superusers'")
        if self.scope['user'].is_staff:
            async_to_sync(self.channel_layer.group_add)("staff", self.channel_name)
            print("ws_connect: added to group 'staff'")
        async_to_sync(self.channel_layer.group_add)("chat", self.channel_name)  # @FIXME not needed, remove
        self.accept()

    def disconnect(self, close_code):
        if self.scope['user'].is_authenticated:
            print("ws_disconnect: %s" % self.scope['user'].email)
            async_to_sync(self.channel_layer.group_discard)(f"users", self.channel_name)
            async_to_sync(self.channel_layer.group_discard)(f"users.{self.scope['user'].id}", self.channel_name)
            print(f"ws_disconnect: removed from group 'users'")
        if self.scope['user'].is_superuser:
            async_to_sync(self.channel_layer.group_discard)("superusers", self.channel_name)
            print(f"ws_disconnect: removed from group 'superusers'")
        if self.scope['user'].is_staff:
            async_to_sync(self.channel_layer.group_discard)("staff", self.channel_name)
            print(f"ws_disconnect: removed from group 'staff'")
        async_to_sync(self.channel_layer.group_discard)("chat", self.channel_name)  # @FIXME not needed, remove

    def receive_json(self, content):
        print(content)
        try:
            request = content
            replyTo = request.get('replyTo', None)
            channel = request['channel']
            payload = request.get('payload', [])
            if settings.DEBUG:
                print(f"[{timestamp()}] ws_message received on channel '{channel}'")
            n_queries = len(connection.queries)
            result = call_listener(channel, self, *payload)
            n_queries = len(connection.queries) - n_queries
            response = {
                'replyTo': replyTo,
                'payload': result
            }
            self.send_json(content=response)
            if settings.DEBUG:
                print(f"[{timestamp()}] ws_message replied to on channel '{channel}' ({n_queries} SQL queries)")

        except Exception as ex:
            print(traceback.format_exc())
            try:
                errorTo = request.get('errorTo', None)
            except:
                errorTo = None
            formatted_lines = traceback.format_exc().splitlines()
            if settings.DEBUG:
                result = "Backend Error\n%s\n%s" % (formatted_lines[1], formatted_lines[-1])
            else:
                result = "Backend Error\n%s" % (formatted_lines[-1], )
            response = {
                'replyTo': errorTo,
                'payload': result
            }
            self.send_json(content=response)
            raise ex