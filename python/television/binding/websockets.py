# https://raw.githubusercontent.com/django/channels/fb6b467c7a7bdd203e25851684742dc48ec1ea42/channels/binding/websockets.py

import json

from django.core import serializers
from django.core.serializers.json import DjangoJSONEncoder

from television.binding.base import Binding

class WebsocketMultiplexer(object):
    """
    The opposite of the demultiplexer, to send a message though a multiplexed channel.

    The multiplexer object is passed as a kwargs to the consumer when the message is dispatched.
    This pattern allows the consumer class to be independent of the stream name.
    """

    stream = None
    reply_channel = None

    def __init__(self, stream, reply_channel):
        self.stream = stream
        self.reply_channel = reply_channel

    def send(self, payload):
        """Multiplex the payload using the stream name and send it."""
        self.reply_channel.send(self.encode(self.stream, payload))

    @classmethod
    def encode_json(cls, content):
        return json.dumps(content, cls=DjangoJSONEncoder)

    @classmethod
    def encode(cls, stream, payload):
        """
        Encodes stream + payload for outbound sending.
        """
        content = {"stream": stream, "payload": payload}
        return {"text": cls.encode_json(content)}

    @classmethod
    def group_send(cls, name, stream, payload, close=False):
        message = cls.encode(stream, payload)
        if close:
            message["close"] = True
        Group(name).send(message)



class WebsocketBindingWithMembers(Binding):
    model = None
    send_members = []

    encoder = DjangoJSONEncoder()

    # Stream multiplexing name
    stream = None

    # Outbound
    @classmethod
    def encode(cls, stream, payload):
        return WebsocketMultiplexer.encode(stream, payload)

    def serialize(self, instance, action):
        payload = {
            "action": action,
            "pk": instance.pk,
            "data": self.serialize_data(instance),
            "model": self.model_label,
        }
        return payload

    def serialize_data(self, instance):
        """
        Serializes model data into JSON-compatible types.
        """
        print('television.bindings.websockets -> serialize_data')
        if self.fields is not None:
            if self.fields == '__all__' or list(self.fields) == ['__all__']:
                fields = None
            else:
                fields = self.fields
        else:
            fields = [f.name for f in instance._meta.get_fields() if f.name not in self.exclude]
        data_json = serializers.serialize('json', [instance], fields=fields)
        data = json.loads(data_json)[0]['fields']
        data['pk'] = instance.pk

        # add any extra properties passed via send_members=[...] argument
        member_data = {}
        for m in self.send_members:
            member = instance
            for s in m.split('.'):
                member = getattr(member, s)
            if callable(member):
                member_data[m.replace('.', '__')] = member()
            else:
                member_data[m.replace('.', '__')] = member
        member_data = json.loads(self.encoder.encode(member_data))
        data.update(member_data)

        return data

    # Inbound
    @classmethod
    def get_handler(cls):
        """
        Adds decorators to trigger_inbound.
        """
        # Get super-handler
        handler = super(WebsocketBinding, cls).get_handler()
        return handler

    @classmethod
    def trigger_inbound(cls, message, **kwargs):
        """
        Overrides base trigger_inbound to ignore connect/disconnect.
        """
        # Only allow received packets through further.
        if message.channel.name != "websocket.receive":
            return
        super(WebsocketBinding, cls).trigger_inbound(message, **kwargs)

    def deserialize(self, message):
        """
        You must hook this up behind a Deserializer, so we expect the JSON
        already dealt with.
        """
        print('television.bindings.websockets -> deserialize')
        body = json.loads(message['text'])
        action = body['action']
        pk = body.get('pk', None)
        data = body.get('data', None)
        return action, pk, data

    def _hydrate(self, pk, data):
        """
        Given a raw "data" section of an incoming message, returns a
        DeserializedObject.
        """
        s_data = [
            {
                "pk": pk,
                "model": self.model_label,
                "fields": data,
            }
        ]
        return list(serializers.deserialize("python", s_data))[0]

    def create(self, data):
        self._hydrate(None, data).save()

    def update(self, pk, data):
        instance = self.model.objects.get(pk=pk)
        hydrated = self._hydrate(pk, data)

        if self.fields is not None:
            for name in data.keys():
                if name in self.fields or self.fields == ['__all__']:
                    setattr(instance, name, getattr(hydrated.object, name))
        else:
            for name in data.keys():
                if name not in self.exclude:
                    setattr(instance, name, getattr(hydrated.object, name))
        instance.save()

