# -*- coding: utf8 -*-
import json
import logging

import tornado.ioloop
import tornado.httpserver
import tornado.web

log = logging.getLogger("request")

class BaseHandler(tornado.web.RequestHandler):
    def __init__(self, application, request, **kwargs):
        super(BaseHandler, self).__init__(application, request)
        self._master = None
        self._slave = None

    @property
    def master(self):
        if self._master is None:
            self._master = self.application.redis_driver.master
        return self._master

    @property
    def slave(self):
        if self._slave is None:
            self._slave = self.application.redis_driver.slave
        return self._slave


class JsonHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        super(JsonHandler, self).__init__(application, request)
        self.json_args = None

    def prepare(self):
        if self.request.method == 'POST':
            b = self.request.body
            # print(b)
            try:
                self.json_args = json.loads(b.decode('utf8'))
            except:
                self.json_args = {}


class FuelCardBaseHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        super(FuelCardBaseHandler, self).__init__(application, request)

class FuelCardJsonHandler(FuelCardBaseHandler):
    def __init__(self, application, request, **kwargs):
        super(FuelCardJsonHandler, self).__init__(application, request)

    def resp_json_result(self, status, msg,data=None):
        resp_data = {'status':status, 'msg':msg, 'data':data}
        log.info("RESP: {0}".format(resp_data))

        resp_data = json.dumps(resp_data)
        return self.finish(resp_data)

    def prepare(self):
        if self.request.method == 'GET':
            log.info("GET: {0} {1}".format(self.request.uri, self.request.arguments))
            self.args = {}
            for argument in self.request.arguments:
                if argument != 'requ_type':
                    self.args[argument] = self.get_argument(argument)

            self.requ_type = self.get_argument('requ_type', None)
            self.argu_list = self.args

        elif self.request.method == 'POST':
            requ_body = self.request.body.decode()
            log.info("POST: {0} {1}".format(self.request.uri, requ_body))
            self.args = json.loads( requ_body )

            self.requ_type = self.args['requ_type']
            self.argu_list = self.args.get('argu_list', {})