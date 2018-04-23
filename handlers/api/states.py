import json
import logging
import tornado.web
from tornado import gen


log = logging.getLogger("request")


class ApiStatesHandler(tornado.web.RequestHandler):
    ORDER_GET_FLAG_KEY = 'flag:get'

    @gen.coroutine
    def post(self):
        self.master = self.application.redis_driver.master
        body = self.request.body.decode()

        args = json.loads(body)

        if_switch = args.get('if_switch', False)

        now_getting = not self.master.exists(self.ORDER_GET_FLAG_KEY)

        if if_switch:
            if not now_getting:
                self.master.delete(self.ORDER_GET_FLAG_KEY)
            else:
                self.master.set(self.ORDER_GET_FLAG_KEY, 'True')

            now_getting = not now_getting

            log.info(">>>flag:get={0}<<< BY {1}".format(now_getting, args.get('user_id')))


        states = json.dumps({'isGetting': now_getting})

        log.debug(states)

        self.finish(states)