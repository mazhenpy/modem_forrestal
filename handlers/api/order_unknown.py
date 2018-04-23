import json
import logging

from tornado import gen
import tornado.web

request_log = logging.getLogger("request")


class ApiOrderUnknownHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def get(self):
        slave = self.application.redis_driver.slave

        order_unknown_key = "set:order:unknown"
        order_ids = slave.smembers(order_unknown_key)

        order_list = []
        for order_id in order_ids:
            order_key = "order:{0}".format(order_id)
            order_info = slave.hgetall(order_key)

            card_id = order_info['card_id']
            card_key = "card:{0}".format(card_id)
            card_info = slave.hgetall(card_key)

            order = {
                'order_id': order_id,
                'card_id': card_id,
                'account_number': order_info.get('account_number'),
                'create_tsp': order_info.get('create_tsp'),
                'price': order_info.get('price'),

                'agent': order_info.get('site'),
                'agent_result': order_info.get('site_result'),
                'agent_data': order_info.get('site_msg','未知错误，请联系管理员！！！'),

                'card_package': card_info.get('package'),
                'card_filename': card_info.get('file_name'),
                'card_create_time': card_info.get('create_time')
            }

            order_list.append(order)

        order_list = sorted(order_list, key=lambda k: k['create_tsp'])
        self.finish(json.dumps({'order_list':order_list}))


