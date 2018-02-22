from channels import Group
import json
import hashlib
import datetime


def timestamp():
    return datetime.datetime.now().strftime('%Y-%b-%d %H:%M:%S.%f')[:-3]


def send_to_group(group, channel, payload):
    return Group(group).send({'text': json.dumps({'stream': channel, 'payload': payload})})


def staff_log(message):
    return send_to_group('staff', 'staff.log', {'message': message})
