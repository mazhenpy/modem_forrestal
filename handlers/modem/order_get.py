import json
import logging
import time
import tornado.web
from drivers.encryption_decryption import aes_decrypt, aes_encrypt

log = logging.getLogger("request")

class OrderGetHandler(tornado.web.RequestHandler):
    def __init__(self,application, request, **kwargs):
        super(OrderGetHandler,self).__init__(application, request, **kwargs)

        self.site = None
        self.site_config = None

    def response_result(self, status, msg,data=None):
        code = None
        if data != None:
            #log.info("OrderGetHandler RESP DATA - {0}".format(data))
            data = json.dumps({'data': data,"mask_tsp": int(time.time()*1000)})
            code = aes_encrypt(data,self.site_config['aes_pass'], self.site_config['aes_iv'])

        response = json.dumps({'status':status, 'msg':msg, 'code':code})
        #log.info("OrderGetHandler RESP - " + response)
        return self.finish(response)

    def post(self):
        request_body = self.request.body.decode('utf8')
        #log.info("OrderGetHandler REQU - " + request_body)
        request = json.loads(self.request.body.decode('utf8'))

        #解析请求参数
        product = None
        number = None
        try:
            self.site = request['site']
            self.site_config = self.application.config['up_user'][self.site]

            code = request['code']
            request_code = aes_decrypt(code, self.site_config['aes_pass'], self.site_config['aes_iv'])
            #log.info("OrderGetHandler REQU2" + request_code)

            request_arguments = json.loads(request_code)
            product = request_arguments['product']
            number = int( request_arguments['number'] )

            if product != self.application.product_type:
                return self.response_result('fail', 'invalid product')

        except:
            log.exception("OrderGetHandler PARSE ERROR!!!")

        if not product or not number:
            return self.response_result('fail', 'invalid arguments')

        #获取待处理订单,并回复
        try:
            order_list = self.get_ready_order(product, number)
            return self.response_result('success', 'success', order_list)
        except:
            log.exception("OrderGetHandler PARSE ERROR!!!")
            return self.response_result('fail', 'server exception')

    def get_ready_order(self,product, number):
        master = self.application.redis_driver.master

        count = 0
        order_list = []
        order_ready_key = "list:order:ready:{0}".format(self.site)
        order_processing_key = "set:order:processing:{0}".format(self.site)
        while count < number:
            order_id = None
            try:
                order_id = master.rpop(order_ready_key)
                if not order_id:
                    break
                log.info("ORDER {0} >> SITE {1} START".format(order_id, self.site))

                order_key = "order:{0}".format(order_id)
                master.hmset(order_key,{
                    'status': 'processing',
                    'site': self.site,
                    'site_req_tsp': int(time.time()),
                })
                master.sadd(order_processing_key, order_id)

                order_info = master.hgetall(order_key)
                card_key = 'card:{0}'.format(order_info['card_id'])
                card_password = master.hget(card_key, 'password')
                order_list.append({'order_id': order_info['order_id'],
                                   'account_number': order_info['account_number'],
                                   'product': self.application.product_type,
                                   'card_id': order_info['card_id'],
                                   'password': card_password,
                                   })
                log.info("ORDER {0} >> SITE {1} END".format(order_id, self.site))
                count += 1
            except:
                log.exception("get_ready_order exception ORDER_ID = {0} !!!".format(order_id))
                break

        return  order_list


