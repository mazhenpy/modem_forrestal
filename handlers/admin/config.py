# encoding: utf-8
import hashlib
import json
import logging
import yaml
import shutil
import time

from handlers import BaseHandler
import tornado.gen

request_log = logging.getLogger("request")


def signature(*parts):
    m = hashlib.md5()
    for p in parts:
        m.update(p.encode('utf8'))
    return m.hexdigest().upper()


class ConfigHandler(BaseHandler):
    @tornado.gen.coroutine
    def post(self):
        request_log.info('CONFIG START')

        try:
            safety = self.application.config.get('safety')
            if safety is None:
                request_log.error('CONFIG FAIL (NO SAFETY)')
                return self.send_error(500)

            # verify ip in white list
            if self.request.remote_ip not in safety['white_list']:
                request_log.error("CONFIG FAIL ('%s'NOT IN WHITELIST)",
                                  self.request.remote_ip)
                return self.send_error(500)

            # verify key
            tsp0 = self.request.headers['tsp']
            encrypted0 = self.request.headers['v']
            encrypted1 = signature(tsp0 + safety['secret'])

            if encrypted1 != encrypted0:
                request_log.error('CONFIG FAIL (SECRET FAIL)')
                return self.send_error(500)

            # SAFETY NOW :)

            # reload
            body = self.request.body.decode()
            new_cfg = yaml.load(body)

            if new_cfg:
                # basic check
                d1 = len(new_cfg.get('up_user'))
                d0 = len(self.application.config.get('up_user'))
                delta = abs((d1 - d0) * 100 / d0)
                request_log.info('CONFIG DELTA %.3f', delta)

                tsp = time.strftime("%m%d%H%M%S", time.localtime())

                # back config
                shutil.copy('up_user.yaml', 'up_user.yaml.%s' % tsp)

                # write config
                with open('up_user.tmp', 'w', encoding='utf8') as stream:
                    stream.write(body)

                if delta > 10 and abs(d1 - d0) > 10:
                    request_log.error('CONFIG FAIL DELTA %.3f', delta)
                    return self.send_error(500)

                shutil.move('up_user.tmp', 'up_user.yaml')

                self.application.config['up_user'] = new_cfg.get('up_user')

                request_log.info('CONFIG SYNCED')
                self.finish(json.dumps({'status': 'ok'}))

                yield self.application.port_manager.sync_user(new_cfg)

                return

        except Exception as e:
            request_log.exception('CONFIG SYNC FAIL')

        self.send_error(500)
