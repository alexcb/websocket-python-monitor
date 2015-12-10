import time
import json

import tornado.ioloop
import tornado.web
import tornado.websocket


time_series_buffer = []
num_users = 0


def collect_data():
    global time_series_buffer
    time_series_buffer.append({
        'time': int(time.time()),
        'loadavg': get_load_avg(),
        'num_users': num_users,
        })
    time_series_buffer = time_series_buffer[-1000:]


class IndexHandler(tornado.web.RequestHandler):
    def set_extra_headers(self, path):
        self.set_header("Cache-control", "no-cache")
    @tornado.web.asynchronous
    def get(request):
        request.render("index.html")


def get_load_avg():
    with open('/proc/loadavg', 'r') as fp:
        s = fp.readline()
    load_avg, _ = s.split(' ', 1)
    load_avg = float(load_avg)
    return load_avg


class WebSocketMetricsHandler(tornado.websocket.WebSocketHandler):
    def open(self, *args):
        global num_users
        num_users += 1
        print 'Connected'
        self._last_sent_time = 0
        self._callback = tornado.ioloop.PeriodicCallback(self._send_load, 1000)
        self._callback.start()

    def on_message(self, message):        
        print 'Got message: %s' % message

    def on_close(self):
        global num_users
        num_users -= 1
        self._callback.stop()

    def _send_load(self):
        data = [
            x for x in time_series_buffer
            if x['time'] > self._last_sent_time
            ]
        print data, self._last_sent_time
        self.write_message(json.dumps(data))
        try:
            self._last_sent_time = max([x['time'] for x in time_series_buffer])
        except ValueError:
            pass


app = tornado.web.Application([('/metrics', WebSocketMetricsHandler), ('/', IndexHandler)])
app.listen(8080)

sampler_callback = tornado.ioloop.PeriodicCallback(collect_data, 1000)
sampler_callback.start()

tornado.ioloop.IOLoop.instance().start()
