# Django Television

Television is small websockets library wrapping most of the configuration required for [Channels](https://github.com/django/channels) `1.x` through the use of simple, opinionated Python decorators. It also includes a JavaScript library for use in the front-end.

Python event listeners are declared using the `@television.add_listener` decorator.

Django models can be decorated to emit data-binding updates using the `@television.add_data_binding_staff` decorator on model class definitions.

A Javascript library is also provided to invoke these listeners with `Television.promise(...)` or to receive two-way data binding updates from Channels with `Television.bindState(...)`.

*Channels `2.x` is not supported at this time. Requires Python 3.6 or newer.*

## Quickstart

1. Install `django-television` in your Python 3.6+ project.

```
pip install django-television
```

2. Add `television` and `channels` to your `settings.py` file and set up your initial URL routing for websockets connections.

```
INSTALLED_APPS = [
    # ...
    'channels',
    'television'
]

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "asgiref.inmemory.ChannelLayer",
        "ROUTING": "television.routing.channel_routing",
    },
}
```

3. Create your first `app/listeners.py` file.

```
# app/listeners.py
import television

@television.add_listener('ping')
def ping(message):
    return 'pong!'
```

4. Add `django-television.js` to any template.

```
{% load static %}
<script type="text/javascript" src="{% static "django-television.js" %}">
```

5. Visit the web application in your browser at this template-view and open Chrome Dev Tools:

```
Television.promise('ping')
.then((result)=>{
    console.log(result);
});
```

6. Pong!

## Simple Usage

Python event listeners (handlers) can be added using the `@add_listener` decorator anywhere in your code base.

```
@add_listener('polls.create')
def create_poll(message, poll_name):
    poll = Poll()
    poll.name = poll_name
    poll.save()
```

Django models can be indicated for two-way data binding using the `@add_data_binding_staff` decorators as below:

```
@add_data_binding_staff(send_members=['extra'])
class Contact(models.Model):
    email = models.EmailField()
    full_name = models.TextField()

    @property
    def extra(self):
        return {
          'name': self.full_name.title()
        }
```

The `television` module will search all installed Django applications for a `listeners.py` file or module from which to import event listeners (if the decorated function is not placed in a regularly imported `views.py` or similar).

## Detailed Usage

```
# app/listeners.py

from television import add_listener
from .models import Poll

@add_listener('polls.fetch')
def fetch_polls(message, arg1, arg2, arg3):
    return list(Poll.objects.values())
```

The first argument is always the Django Channels websocket message object.

These listeners can then be invoked from the front-end using the accompanying Javascript module `television`:

```
// src/main.js
import { Television } from 'django-television';

// The first parameter is the television channel name (listener)
Television.promise('polls.fetch', arg1, arg2, arg3)
.then((result)=>{
    this.setState({
        polls: result.polls,
        message: null
    })
})
.catch((error)=>{
    this.setState({
        polls: [],
        message: 'Unable to fetch polls.'
    });
    throw error;
});
```

The client-side Javascript exception that is thrown includes the original Python exception (and also traceback when `DEBUG` is `True`).

Often it is useful to rely on data-binding to update the DOM for `create`, `update`, and `delete` events, and to limit `Television.promise` listener calls to creating/other actions.

### Data-binding

```
# app/models.py
from television import add_data_binding_staff

@add_data_binding_staff(fields=['email'], send_members=['tags_pretty'])
class Contact(models.Model):
    email = models.EmailField(null=False)
    tags = models.ManyToManyField('marketing.ContactTag', related_name='contacts')

    @property
    def tags_pretty(self):
        return ", ".join([x.name for x in self.tags.all()])
```

```
# app/main.js
import { Television } from 'django-television';

// Television.bindState is provided as a helper for React components
export class ContactList extends React.Component {
    constructor() {
        super()
        this.state = {
            contacts: []
        }
    }

    componentDidMount() {
        // bind Django Channels data updates to `this.state.contacts`
        Television.bindState(this, 'app.contact', 'contacts');
    }

    // ...
}

// For non-React apps you can handle model updates yourself.
// Two attributes: payload.action and payload.data
Television.on('app.contact', (payload)=>{
  switch(payload.action){
    case 'create':
      // ...
    case 'update':
      // ...
    case 'delete':
      // ...
    default:
      throw new Error(`slug ${payload.pk} not found.`);
  }
});
```

### Decorators

A handful of other decorators for listeners are available, including `require_auth`, `require_staff`, and `require_superuser`.


```
# listeners.py

@require_auth
@add_listener('profile.fetch')
def fetch_profile(message):
    return {
        'username': message.user.username,
        'email': message.user.email
    }

@require_staff
@add_listener('user.create')
def add_user(message, email):
    user = User()
    user.email = email
    user.username = email
    user.save()
    return {
        'message': f'User {email} was created.'
    }

@require_superuser
@add_listener('staff.create')
def add_staff_user(message, email):
    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        user = User()
        user.email = email
        user.username = email
    user.is_staff = True
    user.save()
    return {
        'message': f'Staff user {email} was created.'
    }

```

### Other utilities

Staff and superusers are automatically added to Channels groups named `staff` and `superusers`, respectively.

You can use `television.utils.staff_log` to send a log statement over the websocket to all staff users. This is useful for long-running asynchronous tasks or in addition to `logger` or `print` statements.

## FAQ

**Q. Why name this project *django-television*?**

**A.** It plays on both the meaning of the word *television* (i.e. this project ties Django to SPA front-end code) as well as the oft-cited description of Django as an *MTV* (model-template-view) framework (and this project tends to substitute the use of vanilla Django templates and views).

**Q. Who is library this for?**

**A.** This library aims to provide the bulk of sexy Channels/WebSockets functionality through a handful of opinionated one-liner decorators with minimal setup. Additionally, this repo also hosts an `npm` package with Javascript utilities for communicating with Django/Channels/Television.

It is further intended that the bulk of this library can be name-spaced to the route `wss://.../tv/` and still allow more experienced developers to make direct use of the underlying Channels project. Custom routes can be added using the `television.registry` module:

```
# add your routes to `television.routing` using the registry module:
from television.registry import EXTRA_ROUTES
EXTRA_ROUTES.append(route(...))

# or conversely, add `television.routing` to your own routing module specified in settings.py
from television.routing import channel_routing as tv_routing
# ...
channel_routing.extend(tv_routing)
```

## Development

```
# Recommended to install as git-submodule to existing Django project
cd /opt/project
mkdir -p bundle
git clone git@github.com:pztrick/django-television.git bundle/django-television

# back-end module
pip install -e /opt/project/bundle/django-television/python

# front-end module
cd /opt/project/bundle/django-televison/javascript
npm link  # installs package to ../../.npm -> /opt/project/bundle/.npm/lib/node_modules/django-television
cd /opt/project
NODE_PATH=/opt/project/bundle/.npm/lib/node_modules

# webpack configuration:
{
  resolve: {
    extensions: ['.js', '.jsx', '.json'],
    modules: ['/opt/project/bundle/.npm/lib/node_modules', 'node_modules']
  }
}

# You should also run `npm run dev` if working on dj-tv JavaScript
cd bundle/django-television/javascript
npm run dev  # watches for changes
```