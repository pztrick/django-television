import './style.styl';
import EventEmitter2 from 'eventemitter2';
import moment from 'moment';

var emitter = new EventEmitter2({
    wildcard: true,
    delimiter: '.',
    newListener: false,
    maxListeners: 10,
    verboseMemoryLeak: true
});

emitter.pending = {};

emitter.initialize = ()=>{
    emitter.ready = false;

    var websocket_host = window.location.protocol == "https:" ? `wss://${window.location.host}/tv/` : `ws://${window.location.host}/tv/`;

    emitter.socket = new WebSocket(websocket_host);

    emitter.socket.onopen = (event)=>{
        emitter.ready = true;
        console.debug('Television connected.');
    }

    emitter.socket.onerror = (error)=>{
        console.error(error);
    }

    emitter.socket.onmessage = (event)=>{
        var response = JSON.parse(event.data);
        if(response.replyTo !== undefined){
            emitter.emit(response.replyTo, response.payload);
        }else if(response.stream === 'television-updates'){
            console.debug(`emitting model update on channel ${response.payload.model}`);
            emitter.emit(response.payload.model, response.payload);
        }else if(response.stream !== undefined){
            console.debug(`emitting on channel ${response.stream}`);
            emitter.emit(response.stream, response.payload);
        }else{
            console.debug(`ignoring unhandled WebSocket message: ${JSON.stringify(response)}`);
        }
    }

    emitter.socket.onclose = (event)=>{
        console.warn('closed! reopening!');
        emitter.ready = false;
        setTimeout(()=>{emitter.initialize();}, 1000);
    }
}

emitter.initialize();

emitter.initSpinner = ()=>{
    // inject spinner into DOM
    var div = document.createElement("div");
    div.id = "television-spinner";
    div.style.display = 'none';
    div.style.zIndex = 999;
    div.innerHTML = `<svg width="200px" height="200px" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid" class="uil-ring" data-reactid=".0.1.0"><rect x="0" y="0" width="100" height="100" fill="none" class="bk" data-reactid=".0.1.0.0"></rect><circle cx="50" cy="50" r="40" stroke-dasharray="163.36281798666926 87.9645943005142" stroke="#720000" fill="none" stroke-width="20" data-reactid=".0.1.0.1"></circle></svg>`;
    document.body.appendChild(div);

    var spinner = document.getElementById('television-spinner');
    setInterval(()=>{
        if(Object.keys(emitter.pending).length > 0){
            spinner.style.display = 'block';
        }else{
            spinner.style.display = 'none';
        }
    }, 500);
}

var promiseCounter = 0;
emitter.promise = (channel, ...args)=>{
    if(!emitter.ready){
        console.debug('socket not ready; deferring emit');
        return new Promise((resolve, reject)=>{
            setTimeout(()=>{
                console.debug('retrying!');
                emitter.promise(channel, ...args).then(resolve).catch(reject);
            }, 500);
        });
    }
    console.debug(`emitting promise on channel ${channel}, args=`, args);
    if(promiseCounter === Number.MAX_SAFE_INTEGER){
        promiseCounter = 0;
    }else{
        promiseCounter += 1;
    }
    var promiseId = promiseCounter;  // scope promiseId to this block
    emitter.pending[promiseId] = moment();
    var replyTo = `promise-${promiseId}`;
    var errorTo = `error-${promiseId}`;
    var payload = {
        channel: channel,
        replyTo: replyTo,
        errorTo: errorTo,
        payload: args
    };
    return new Promise((resolve, reject)=>{
        emitter.once(replyTo, (payload)=>{
            console.debug(`${channel} replied in ${moment()-emitter.pending[promiseId]}ms`);
            delete emitter.pending[promiseId];
            resolve(payload);
        });
        emitter.once(errorTo, (error)=>{
            delete emitter.pending[promiseId];
            reject(error);
        });
        emitter.socket.send(JSON.stringify(payload));
    });
}

emitter.bindState = (component, channel, attr, fetch=true) => {
    // reciprocal with @add_data_binding_owner decorator in Djangoland
    let unique_key = 'pk';

    // 1) fetch initial state
    if(fetch === true){
        emitter.promise(`${channel}.list`)
        .then((result)=>{
            component.setState({
                [attr]: result
            });
        });
    }

    // 2) listen for model updates
    emitter.on(channel, (payload)=>{
        let instances = component.state[attr] || [];
        let index = null;
        switch (payload.action) {
            case 'update':
                // let instances = component.state[attr];
                index = instances.findIndex((obj)=>{return obj[unique_key] === payload[unique_key];});
                if(index < 0 || index === null){
                    console.warn(`django-television: invalid pk=${payload[unique_key]} on channel ${channel}.`);
                    return;
                }
                instances[index] = {
                    ...instances[index],
                    ...payload.data
                };
                component.setState({
                    [attr]: instances
                });
                break;
            case 'create':
                instances.unshift(payload.data);
                component.setState({
                    [attr]: instances
                });
                break;
            case 'delete':
                index = instances.findIndex((obj)=>{return obj[unique_key] === payload[unique_key];});
                if(index < 0 || index === null){
                    console.warn(`django-television: invalid pk=${payload[unique_key]} on channel ${channel}.`);
                    return;
                }
                component.setState({
                    [attr]: [
                        ...instances.slice(0, index),
                        ...instances.slice(index + 1)
                    ]
                });
                break;
            default:
                throw new Error(`Unhandled Django data binding event on channel=${channel}`);
        }
    });
}

window.Television = emitter;

module.exports = emitter;