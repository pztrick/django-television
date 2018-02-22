from functools import wraps
from pydoc import locate

from django.conf import settings
from django.dispatch import receiver
from django.test.signals import setting_changed
from django.db import connection

from channels.binding.base import BindingMetaclass
from channels.binding.websockets import WebsocketBindingWithMembers
from channels.generic.websockets import WebsocketDemultiplexer

from television.registry import LISTENERS, DEMULTIPLEXERS
from television.exceptions import ListenerNotFound


def require_auth(fun):
    @wraps(fun)
    def _inner(message, *args, **kwargs):
        if not message.user.is_authenticated():
            raise Exception("NOAUTH")
        return fun(message, *args, **kwargs)
    return _inner


def require_staff(fun):
    @wraps(fun)
    def _inner(message, *args, **kwargs):
        if not message.user.is_staff:
            raise Exception("NOSTAFF")
        return fun(message, *args, **kwargs)
    return _inner


def require_superuser(fun):
    @wraps(fun)
    def _inner(message, *args, **kwargs):
        if not message.user.is_superuser:
            raise Exception("NOSUDO")
        return fun(message, *args, **kwargs)
    return _inner


APPS_FINISHED_LOADING = False
def add_listener(channel):
    def decorator(fun):
        @wraps(fun)
        def _inner(*args, **kwargs):
            return fun(*args, **kwargs)
        if channel in LISTENERS:
            if not APPS_FINISHED_LOADING: # prevent test runner from blowing up with exception 'Listener already registered...'
                raise Exception(f"Listener already registered for channel: {channel}")
        module_value = "%s.%s" % (fun.__module__, fun.__name__)
        if module_value.split('.')[0] == 'television':
            # is OK to map anonymous function created in this library
            LISTENERS[channel] = fun
        elif module_value in LISTENERS.values():
            # throw helpful error explaining function name is defined twice
            raise Exception(f"Listener callback function defined twice: {module_value}")
        else:
            LISTENERS[channel] = module_value
        return _inner
    return decorator


def call_listener(channel, message, *args, **kwargs):
    try:
        listener = LISTENERS[channel]
    except KeyError:
        raise ListenerNotFound(f"Listener not defined for channel '{channel}'")
    if not callable(listener):
        listener = locate(listener)  # may be of form: 'module.path.function'
    return listener(message, *args, **kwargs)


def add_data_binding_staff(fields='__all__', send_members=[], exclude=[]):
    def decorate(model_class):
        nonlocal fields

        send_members.append('pk')  # always send pk

        if fields == '__all__':
            fields = [x.name for x in model_class._meta.fields]
        elif fields == None:
            fields = []

        class StaffAuthModelBinding(WebsocketBindingWithMembers):
            model = model_class
            stream = 'television-updates'

            @classmethod
            def group_names(cls, instance):
                return ['staff']

            def has_permission(self, user, action, pk):
                return user.is_staff

        setattr(StaffAuthModelBinding, 'fields', fields)
        setattr(StaffAuthModelBinding, 'send_members', send_members)
        setattr(StaffAuthModelBinding, 'exclude', exclude)

        class Demultiplexer(WebsocketDemultiplexer):
            consumers = {
                'television-updates': StaffAuthModelBinding.consumer,
            }

            def connection_groups(self):
                return ["staff"]

        DEMULTIPLEXERS.append(Demultiplexer)

        # add 'app.model.list' endpoint for serialized objects
        serialize_data = StaffAuthModelBinding().serialize_data
        listener_name = f'{model_class._meta.label_lower}.list'
        @require_staff
        @add_listener(listener_name)
        def listener(message):
            queryset = model_class.objects.all().order_by('-id')
            result = []
            for instance in queryset:
                result.append(serialize_data(instance))
            return result

        return model_class
    return decorate


def add_data_binding_superuser(fields='__all__', send_members=[], exclude=[]):
    def decorate(model_class):
        nonlocal fields

        send_members.append('pk')  # always send pk

        if fields == '__all__':
            fields = [x.name for x in model_class._meta.fields]
        elif fields == None:
            fields = []

        class SuperuserAuthModelBinding(WebsocketBindingWithMembers):
            model = model_class
            stream = 'television-updates'

            @classmethod
            def group_names(cls, instance):
                return ['superusers']

            def has_permission(self, user, action, pk):
                return user.is_superuser

        setattr(SuperuserAuthModelBinding, 'fields', fields)
        setattr(SuperuserAuthModelBinding, 'send_members', send_members)
        setattr(SuperuserAuthModelBinding, 'exclude', exclude)

        class Demultiplexer(WebsocketDemultiplexer):
            consumers = {
                'television-updates': SuperuserAuthModelBinding.consumer,
            }

            def connection_groups(self):
                return ["superusers"]

        DEMULTIPLEXERS.append(Demultiplexer)

        # add 'app.model.list' endpoint for serialized objects
        serialize_data = SuperuserAuthModelBinding().serialize_data
        listener_name = f'{model_class._meta.label_lower}.list'
        @require_superuser
        @add_listener(listener_name)
        def listener(message):
            queryset = model_class.objects.all().order_by('-id')
            result = []
            for instance in queryset:
                result.append(serialize_data(instance))
            return result

        return model_class
    return decorate


def add_data_binding_owner(fields='__all__', send_members=[], exclude=[], owner_field='user'):
    raise NotImplementedError('To do.')

    def decorate(model_class):
        nonlocal fields

        send_members.append('pk')  # always send pk

        if fields == '__all__':
            fields = [x.name for x in model_class._meta.fields]
        elif fields == None:
            fields = []

        class OwnerAuthModelBinding(WebsocketBindingWithMembers):
            model = model_class
            stream = 'television-updates'

            @classmethod
            def group_names(cls, instance):
                owner = instance
                for attr in cls.owner_field.split('.'):
                    owner = getattr(owner, attr)
                return ["users", f'users.{owner.id}']

            def has_permission(self, user, action, pk):
                raise NotImplementedError('To do.')

        setattr(OwnerAuthModelBinding, 'fields', fields)
        setattr(OwnerAuthModelBinding, 'send_members', send_members)
        setattr(OwnerAuthModelBinding, 'exclude', exclude)
        setattr(OwnerAuthModelBinding, 'owner_field', owner_field)

        class Demultiplexer(WebsocketDemultiplexer):
            consumers = {
                'television-updates': OwnerAuthModelBinding.consumer,
            }

            def connection_groups(self):
                return ["users"]

        DEMULTIPLEXERS.append(Demultiplexer)

        # add 'app.model.list' endpoint for serialized objects
        serialize_data = SuperuserAuthModelBinding().serialize_data
        listener_name = f'{model_class._meta.label_lower}.list'
        @require_auth
        @add_listener(listener_name)
        def listener(message):
            raise NotImplementedError('To do.')

        return model_class
    return decorate
