import logging
import os
import tornado.web
import yaml


request_log = logging.getLogger("forrestal.request")


class ReloadHandler(tornado.web.RequestHandler):
    def get(self):
        request_log.info('ACCESS RELOAD (%s)', self.request.remote_ip)

        if self.request.remote_ip not in ['127.0.0.1', '::1']:
            return self.send_error(403)

        try:
            self.application.load_config()
        except Exception as e:
            request_log.exception('RELOAD FAIL')
            return self.finish('RELOAD FAIL %s' % repr(e))

        self.finish('RELOAD SUCCESS')
