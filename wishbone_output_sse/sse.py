#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  sse.py
#
#  Copyright 2016 Jelle Smet <development@smetj.net>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#

from wishbone import Actor
from gevent import pool
from gevent.wsgi import WSGIServer
from flask import Flask, Response, render_template_string
from gevent.queue import Queue
from uuid import uuid4
from wishbone.event import Bulk
import os


class ServerSentEvent(object):

    def __init__(self, data):
        self.data = data
        self.event = None
        self.id = None
        self.desc_map = {
            self.data: "data",
            self.event: "event",
            self.id: "id"
        }

    def encode(self):
        if not self.data:
            return ""
        lines = ["%s: %s" % (v, k) for k, v in self.desc_map.iteritems() if k]
        return "%s\n\n" % "\n".join(lines)


class ServerSentEvents(Actor):

    '''**Serve event data as server sent events.**

    Serve event data as server sent events.

    When the event header contains:

    If nobody is consuming events then they're lost.
    If <show_last> is set to True, then the last known value
    can be consumed by the client.

    Parameters:

        - selection(str)("@data")
           |  The part of the event to submit externally.
           |  Use an empty string to refer to the complete event.

        - bind(string)("0.0.0.0")
           |  The address to bind to.

        - port(int)(19283)
           |  The port to bind to.

        - show_last(bool)(False)
           |  If true submits the last known value to
           |  a new connection.

        - keepalive(bool)(False)
           |  If true sends a keepalive message at
           |  <keepalive_interval> seconds.

        - keepalive_interval(int)(False)
           |  The time in seconds to send keep-alive
           |  messages to the client.

        - destination(str)("")*
           |  The endpoint from which the event can be consumed.


    Queues:

        - inbox
           |  Incoming events submitted to the outside.

    '''

    def __init__(self, actor_config, selection="@data", bind="0.0.0.0", port=19283, show_last=False, keepalive=False, keepalive_interval=5, destination=""):

        Actor.__init__(self, actor_config)
        self.pool.createQueue("inbox")
        self.registerConsumer(self.consume, "inbox")
        self.session_queues = {}
        self.template = self.__getTemplate()

    def preHook(self):
        self.app = Flask(__name__)
        self.app.debug = False
        self.app.add_url_rule('/<destination>', 'target', self.target)
        self.app.add_url_rule('/', 'target', self.target)
        self.app.add_url_rule('/subscribe/<destination>', 'subscribe', self.subscribe)
        self.app.add_url_rule('/subscribe/', 'subscribe', self.subscribe)

        p = pool.Pool(1000)
        self.server = WSGIServer((self.kwargs.bind, self.kwargs.port), self.app, spawn=p, log=None)
        self.sendToBackground(self.server.serve_forever)
        self.logging.info("Listening on http://%s:%s" % (self.kwargs.bind, self.kwargs.port))

    def target(self, destination=""):
        return render_template_string(self.template, destination=destination)

    def subscribe(self, destination=""):

        def consume():
            try:
                while self.loop():
                    try:
                        result = self.session_queues[destination][queue_id].get(timeout=self.kwargs.keepalive_interval)
                    except:
                        if self.kwargs.keepalive:
                            ev = ServerSentEvent(":keep-alive")
                            yield ev.encode()
                    else:
                        ev = ServerSentEvent(str(result))
                        yield ev.encode()
            except GeneratorExit:
                self.__deleteSessionQueue(destination, queue_id)
            except Exception:
                self.__deleteSessionQueue(destination, queue_id)

        def close():
            self.__deleteSessionQueue(destination, queue_id)

        queue_id = self.__addSessionQueue(destination)
        r = Response(consume(), mimetype="text/event-stream")
        r.call_on_close(close)
        return r

    def consume(self, event):

        if isinstance(event, Bulk):
            data = event.dumpFieldAsString(self.kwargs.selection)
        else:
            data = str(event.get(self.kwargs.selection))

        try:
            for q in self.session_queues[self.kwargs.destination]:
                self.session_queues[self.kwargs.destination][q].put(data)
        except KeyError:
            if self.kwargs.destination == '':
                self.logging.warning("No clients are listening on /")
            else:
                self.logging.warning("No clients are listening on %s" % self.kwargs.destination)

    def __deleteSessionQueue(self, name, i):
        try:
            del(self.session_queues[name][i])
            if len(self.session_queues[name]) == 0:
                del(self.session_queues[name])
        except:
            pass

    def __addSessionQueue(self, name):
        if name not in self.session_queues:
            self.session_queues[name] = {}
        q = Queue()
        i = str(uuid4())
        self.session_queues[name][i] = q
        return i

    def __getTemplate(self):

        return '''
        <html>
            <body>
                <div id="event"></div>
                <script type="text/javascript">
                    var eventOutputContainer = document.getElementById("event");
                    var evtSrc = new EventSource("/subscribe/{{ destination }}");
                    evtSrc.onmessage = function(e) {
                        console.log(e.data);
                        eventOutputContainer.innerHTML = e.data;
                    };
                </script>
            </body>
        </html>
        '''
