import json
import logging
import time

import tornado.web
from tornado import gen
from core.result_code import RESULT_CODE
from handlers import FuelCardJsonHandler

log = logging.getLogger("request")


class ApiOrderFinishHandler(tornado.web.RequestHandler):
    @gen.coroutine
    def post(self):
        body = self.request.body.decode()
        args = json.loads(body)
        log.info("MANUAL INFO {0}".format(args))

        user_id = args.get('user_id', 'unknown')
        order_id = args['order_id']
        result = args['result']
        release = args.get('release', None)

        self.master = self.application.redis_driver.master

        # check for operated twice
        order_unknown_key = "set:order:unknown"
        if not self.master.sismember(order_unknown_key, order_id):
            return self.send_error(500)


        if result == RESULT_CODE.SUCCESS:
            self.do_success_order(order_id,user_id)
        else:
            self.do_fail_order(order_id, user_id, release)

        order_key = "order:{0}".format(order_id)
        order_info = self.master.hgetall(order_key)
        self.application.callback_downstream.callback_downstream(order_id)

        site = order_info.get('site')
        if site:
            order_manual_key  = "list:order:manual:{0}".format(site)
            self.master.lpush(order_manual_key, order_id)

        self.master.srem(order_unknown_key, order_id)
        self.finish(json.dumps({'status': 'ok'}))

    def do_success_order(self, order_id, user_id):
        order_key = "order:{0}".format(order_id)
        card_id = self.master.hget(order_key, 'card_id')
        self.master.hmset(order_key, {
            'result': RESULT_CODE.SUCCESS,
            'manual_user': user_id,
            'manual_result': RESULT_CODE.SUCCESS,
            'manual_result_tsp': int(time.time()),
        })

        log.info("MANUAL ORDER CHARGE SUCCESS >> {0}  CARD {1}".format(order_id,card_id))
        card_key = 'card:{0}'.format(card_id)
        card_site = self.master.hget(card_key, 'site')

        card_used_key = 'list:card:used:{0}'.format(card_site)
        self.master.lpush(card_used_key,card_id)

    def do_fail_order(self, order_id,user_id,release):
        order_key = "order:{0}".format(order_id)
        card_id = self.master.hget(order_key, 'card_id')
        log.info("MANUAL ORDER CHARGE FAIL >> {0}  CARD {1}".format(order_id,card_id))
        card_key = 'card:{0}'.format(card_id)
        card_site,card_pool, price= self.master.hmget(card_key, 'site', 'card_pool', 'price')

        if release == 'error':
            self.master.hmset(order_key, {
                'result': RESULT_CODE.FAIL_CARD_INVALID,
                'manual_user': user_id,
                'manual_result': RESULT_CODE.FAIL_CARD_INVALID,
                'manual_result_tsp': int(time.time()),
            })

            card_error_key = 'list:card:error:{0}'.format(card_site)
            self.master.lpush(card_error_key,card_id)
        else:
            self.master.hmset(order_key, {
                'result': RESULT_CODE.FAIL_CARD_VALID,
                'manual_user': user_id,
                'manual_result': RESULT_CODE.FAIL_CARD_VALID,
                'manual_result_tsp': int(time.time()),
            })
            card_ready_key = 'list:card:ready:{0}:{1}:{2}'.format(card_site, card_pool, price)
            self.master.lpush(card_ready_key,card_id)


class ApiOrderFinishHandler2(FuelCardJsonHandler):
    @gen.coroutine
    def post(self):
        order_id = self.argu_list['order_id']
        user_id = self.args['user_id']

        #检查订单状态是否正确
        order_unknown_key = "set:order:unknown"
        if not self.master.sismember(order_unknown_key, order_id):
            return self.resp_json_result('fail', '订单不存在或已被处理')

        order_key = "order:{0}".format(order_id)
        card_id, port_site= self.master.hmget(order_key, 'card_id','site')

        card_key = 'card:{0}'.format(card_id)
        card_site,card_pool, price= self.master.hmget(card_key, 'site', 'card_pool', 'price')

        #处理成功订单
        if self.requ_type == 'order_success':
            account_price = str(self.argu_list['account_price'])
            if account_price not in self.application.config['price_support']:
                return self.resp_json_result('fail','金额非法')

            #设置订单状态数据
            self.master.hmset(order_key, {
                'result': RESULT_CODE.SUCCESS,
                'manual_user': user_id,
                'manual_result': RESULT_CODE.SUCCESS,
                'manual_result_tsp': int(time.time()),
                'account_price': account_price,
            })

            #设置卡状态数据
            card_used_key = 'list:card:used:{0}'.format(card_site)
            self.master.lpush(card_used_key,card_id)

            log.info("MANUAL ORDER CHARGE SUCCESS >> {0}  CARD {1}".format(order_id,card_id))

        #处理订单失败 卡有效
        elif self.requ_type == 'order_fail_card_valid':
            #设置订单状态数据
            self.master.hmset(order_key, {
                'result': RESULT_CODE.FAIL_CARD_VALID,
                'manual_user': user_id,
                'manual_result': RESULT_CODE.FAIL_CARD_VALID,
                'manual_result_tsp': int(time.time()),
            })

            #设置卡状态数据
            card_ready_key = 'list:card:ready:{0}:{1}:{2}'.format(card_site, card_pool, price)
            self.master.lpush(card_ready_key,card_id)

            log.info("MANUAL ORDER FAIL CARD VALID >> {0}  CARD {1}".format(order_id,card_id))

        #处理订单失败 卡异常
        elif self.requ_type == 'order_fail_card_invalid':
            self.master.hmset(order_key, {
                'result': RESULT_CODE.FAIL_CARD_INVALID,
                'manual_user': user_id,
                'manual_result': RESULT_CODE.FAIL_CARD_VALID,
                'manual_result_tsp': int(time.time()),
            })

            card_error_key = 'list:card:error:{0}'.format(card_site)
            self.master.lpush(card_error_key,card_id)

            log.info("MANUAL ORDER FAIL CARD INVALID >> {0}  CARD {1}".format(order_id,card_id))
        else:
            return self.resp_json_result('fail','未知请求')

        #同步异常订单结果
        if port_site:
            order_manual_key  = "list:order:manual:{0}".format(port_site)
            self.master.lpush(order_manual_key, order_id)

        #将订单结果发给下游
        self.application.callback_downstream.callback_downstream(order_id)

        self.master.srem(order_unknown_key, order_id)

        return self.resp_json_result('ok','成功')