# from channels import Group
import json
import hashlib
import datetime
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def timestamp():
    return datetime.datetime.now().strftime('%Y-%b-%d %H:%M:%S.%f')[:-3]


def send_to_group(group, stream, payload):
    channel_layer = get_channel_layer()
    r = async_to_sync(channel_layer.group_send)(group, {'type': 'relay', 'stream': stream, 'payload': payload})
    return r


def staff_log(message):
    return send_to_group('staff', 'staff.log', {'message': message})
