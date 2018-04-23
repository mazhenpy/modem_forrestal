import json
import logging
import time

import tornado.gen
from tornado.httpclient import AsyncHTTPClient
from tornado.ioloop import IOLoop

from core.result_code import RESULT_CODE
from drivers.encryption_decryption import md5_signature

request_log = logging.getLogger("request")

class CallbackDownstream:
    def __init__(self,application):
        self.application = application

    #订单回调处理
    def callback_downstream(self, order_id):
        master = self.application.redis_driver.master

        order_key = "order:{0}".format(order_id)
        order = master.hgetall(order_key)

        #删除
        all_order_set_key = "set:order"
        master.srem(all_order_set_key, order_id)

        #设置
        master.hset(order_key,'status', 'finish')
        finish_order_key = "list:order:finish"  #需要进行订单持久化的订单
        master.lpush(finish_order_key, order_id)

        #增加回调信息

        back_url = order['back_url']
        order_result = [RESULT_CODE.FAIL,RESULT_CODE.SUCCESS][order['result'] == RESULT_CODE.SUCCESS]
        user_id = ''
        key = self.application.config['downstream'][order['user_id']]['md5_key']
        body = 'userid=%s&orderid=%s&sporderid=%s&merchantsubmittime=%s&resultno=%s' % (
            user_id,
            order['order_id'],
            order['order_id'],
            time.strftime("%Y%m%d%H%M%S", time.localtime()),
            order_result)

        sign = md5_signature(body + '&key=' + key).upper()

        body += "&sign=" + sign


        IOLoop.instance().add_callback(self.send_message,back_url,order_id,body, 1)

    @tornado.gen.coroutine
    def send_message(self, url, order_id, body, count):
        #yield tornado.gen.Task(IOLoop.instance().add_timeout, time.time() + 10)
        request_log.info('{0} DOWNSTREAM CALLBACK REQU {1} {2} {3}'.format(order_id,count, url, body))

        try:
            http_client = AsyncHTTPClient()
            response = yield http_client.fetch(url, method='POST', body=body)

            if response and response.code == 200:
                request_log.info('{0} DOWNSTREAM CALLBACK RESP {1}'.format(order_id, response.body.decode()))
            else:
                request_log.exception('{0} DOWNSTREAM CALLBACK FAIL'.format(order_id))
            count = 6
        except Exception as e:
            request_log.exception('{0} DOWNSTREAM CALLBACK ERROR {1}'.format(order_id, count))

        if count < 5:
            IOLoop.instance().call_later(count * 10, self.send_message, url, body, count + 1)