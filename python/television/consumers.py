import json
import traceback
from django.http import HttpResponse
from channels.handler import AsgiHandler
from channels import Group
from .decorators import add_listener, call_listener
from django.conf import settings
from django.db import connection
from channels.auth import http_session_user, channel_session_user, channel_session_user_from_http
from .utils import timestamp

@channel_session_user_from_http
def ws_connect(message):
    if message.user.is_authenticated:
        Group(f"users").add(message.reply_channel)
        Group(f"users.{message.user.id}").add(message.reply_channel)
        print(f"ws_connect: added to group 'users'")
    if message.user.is_superuser:
        Group("superusers").add(message.reply_channel)
        print("ws_connect: added to group 'superusers'")
    if message.user.is_staff:
        Group("staff").add(message.reply_channel)
        print("ws_connect: added to group 'staff'")
    Group("chat").add(message.reply_channel)
    message.reply_channel.send({"accept": True})

@channel_session_user
def ws_message(message):
    try:
        request = json.loads(message['text'])
        replyTo = request.get('replyTo', None)
        channel = request['channel']
        payload = request.get('payload', [])
        if settings.DEBUG:
            print(f"[{timestamp()}] ws_message received on channel '{channel}'")
        n_queries = len(connection.queries)
        result = call_listener(channel, message, *payload)
        n_queries = len(connection.queries) - n_queries
        response = {
            'replyTo': replyTo,
            'payload': result
        }
        message.reply_channel.send({
            'text': json.dumps(response, default=str)
        })
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
        message.reply_channel.send({
            'text': json.dumps(response, default=str)
        })
        raise ex

@channel_session_user
def ws_disconnect(message):
    if message.user.is_authenticated:
        print("ws_disconnect: %s" % message.user.email)
        Group(f"users").discard(message.reply_channel)
        Group(f"users.{message.user.id}").discard(message.reply_channel)
    if message.user.is_superuser:
        Group("superusers").discard(message.reply_channel)
    if message.user.is_staff:
        Group("staff").discard(message.reply_channel)
    Group("chat").discard(message.reply_channel)
