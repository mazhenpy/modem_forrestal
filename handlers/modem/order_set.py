import json
import logging
import time
from tornado import gen
from tornado.httpclient import HTTPRequest
from tornado.httpclient import AsyncHTTPClient
import tornado.web
from core.result_code import RESULT_CODE, RESULT_CODE2
from drivers.encryption_decryption import aes_decrypt, aes_encrypt

log = logging.getLogger("request")

class OrderSetHandler(tornado.web.RequestHandler):
    def __init__(self,application, request, **kwargs):
        super(OrderSetHandler,self).__init__(application, request, **kwargs)

        self.site = None
        self.site_config = None

        self.master = self.application.redis_driver.master

    def response_result(self, status, msg,data=None):
        code = None
        if data != None:
            #log.info("OrderSetHandler RESP DATA - {0}".format(data))
            data = json.dumps({'data': data,"mask_tsp": int(time.time()*1000)})
            code = aes_encrypt(data,self.site_config['aes_pass'], self.site_config['aes_iv'])

        response = json.dumps({'status':status, 'msg':msg, 'code':code})
        #log.info("OrderSetHandler RESP - " + response)
        return self.finish(response)

    @gen.coroutine
    def post(self):
        request_body = self.request.body.decode('utf8')
        #log.info("OrderSetHandler REQU - " + request_body)
        request = json.loads(self.request.body.decode('utf8'))

        #解析请求参数
        product = None
        order_id = None
        site_result = None
        site_data = None
        try:
            self.site = request['site']
            self.site_config = self.application.config['up_user'][self.site]

            code = request['code']
            request_code = aes_decrypt(code, self.site_config['aes_pass'], self.site_config['aes_iv'])
            log.info("OrderSetHandler REQU2" + request_code)

            request_arguments = json.loads(request_code)
            product = request_arguments['product']
            order_id = request_arguments['order_id']
            site_result = request_arguments['site_result']
            site_data = request_arguments.get('site_data')
        except:
            log.exception("OrderSetHandler PARSE ERROR!!!")

        if not product or not order_id or not site_result:
            return self.response_result('fail', 'invalid arguments')

        #合法性检查
        if product != self.application.product_type:
            return self.response_result('fail', 'unsupport product type')

        order_processing_key = "set:order:processing:{0}".format(self.site)
        order_unknown_key = "set:order:unknown"
        if self.master.sismember(order_processing_key, order_id) == 1:
            self.master.srem(order_processing_key, order_id)
        elif  self.master.sismember(order_unknown_key, order_id) == 1:
            self.master.srem(order_unknown_key, order_id)
        else:
            return self.response_result('fail', 'order_id miss')

        order_key = "order:{0}".format(order_id)
        order_site = self.master.hget(order_key, 'site')
        if self.site != order_site:
            return self.response_result('fail', 'order not match this site')

        self.response_result('success', 'success')
        if not site_data:
            site_data = {}

        #设置订单状态
        order_key = "order:{0}".format(order_id)
        card_id = self.master.hget(order_key, 'card_id')
        account_price = site_data.get('price','0')
        price = self.master.hget(order_key, 'price')

        self.master.hmset(order_key, {
            'site_result': site_result,
            'site_result_tsp': int(time.time()),
            'site_msg': site_data.get('msg',''),
            'account_price': account_price,
            'bot_account':  site_data.get('user'),
            'site_data': site_data,
        })

        if site_result == RESULT_CODE.SUCCESS:
            #判断充值金额是否一致
            if account_price != price:
                self.master.hset(order_key, 'site_result', RESULT_CODE2.WRONG_ACCOUNT_PRICE)
                yield self.do_unknown_order(order_id,card_id,site_data)
            else:
                self.master.hset(order_key, 'result', RESULT_CODE.SUCCESS)
                self.do_success_order(order_id, card_id)
        else:
            yield self.do_unknown_order(order_id,card_id,site_data)

    def do_success_order(self, order_id,card_id):
        log.info("ORDER CHARGE SUCCESS >> {0}  CARD {1}".format(order_id,card_id))
        card_key = 'card:{0}'.format(card_id)
        card_site = self.master.hget(card_key, 'site')

        card_used_key = 'list:card:used:{0}'.format(card_site)
        self.master.lpush(card_used_key,card_id)

        self.application.callback_downstream.callback_downstream(order_id)

    @gen.coroutine
    def do_unknown_order(self, order_id,card_id,site_data):
        order_unknown_key = "set:order:unknown"
        order_key = "order:{0}".format(order_id)
        self.master.hset(order_key, 'status', 'unknown')
        self.master.sadd(order_unknown_key, order_id)
        log.info("ORDER CHARGE UNKNOWN >> {0}  CARD {1}".format(order_id,card_id))

        #判断是否需要通知purus
        if not ('connection' in self.application.config and 'purus' in self.application.config['connection']):
            return

        site_msg = site_data.get('msg', '')
        #判断是何种异常原因
        site_result = self.master.hget(order_key, 'site_result')
        if site_result == RESULT_CODE2.WRONG_ACCOUNT_PRICE:
            account_price = site_data.get('price')
            price = self.master.hget(order_key, 'price')
            site_msg +=  '实际到账金额({0}元)与充值金额({1}元)不匹配'.format(account_price, price)
            yield self.call_purus('order_exception',order_id, site_msg)
        elif  site_result == RESULT_CODE2.FAIL_SEND_FAIL:
            site_msg += '连接中石化失败'
            yield self.call_purus('order_exception',order_id, site_msg)
        else:
            yield self.call_purus('order_unknown',order_id,site_msg)

    @gen.coroutine
    def call_purus(self, requ_type, order_id, site_msg):
        order_key = "order:{0}".format(order_id)
        self.master.hmset(order_key, {
            'site_msg': site_msg,
        })

        url = self.application.config['connection']['purus'] + '/fuel_card/modem_forrestal_call'
        try:
            requ_body = {
                'requ_type':requ_type,
                'order_id': order_id,
                'site_msg': site_msg,
            }
            requ_body = json.dumps(requ_body)

            http_client = AsyncHTTPClient()
            request = HTTPRequest(url=url, method='POST', body=requ_body)
            yield http_client.fetch(request)
        except:
            log.exception('call purus exception')
