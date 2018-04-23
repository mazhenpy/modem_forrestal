import json
import logging
import time
import tornado.web
from drivers.encryption_decryption import aes_decrypt, aes_encrypt

log = logging.getLogger("request")

class OrderRollbackHandler(tornado.web.RequestHandler):
    def __init__(self,application, request, **kwargs):
        super(OrderRollbackHandler,self).__init__(application, request, **kwargs)

        self.site = None
        self.site_config = None

    def response_result(self, status, msg,data=None):
        code = None
        if data != None:
            log.info("OrderRollbackHandler RESP DATA - {0}".format(data))
            data = json.dumps({'data': data,"mask_tsp": int(time.time()*1000)})
            code = aes_encrypt(data,self.site_config['aes_pass'], self.site_config['aes_iv'])

        response = json.dumps({'status':status, 'msg':msg, 'code':code})
        log.info("OrderRollbackHandler RESP - " + response)
        return self.finish(response)

    def post(self):
        request_body = self.request.body.decode('utf8')
        log.info("OrderRollbackHandler REQU - " + request_body)
        request = json.loads(self.request.body.decode('utf8'))

        #解析请求参数
        product = None
        order_id = None
        try:
            self.site = request['site']
            self.site_config = self.application.config['up_user'][self.site]

            code = request['code']
            request_code = aes_decrypt(code, self.site_config['aes_pass'], self.site_config['aes_iv'])
            log.info("OrderRollbackHandler REQU2" + request_code)

            request_arguments = json.loads(request_code)

            product = request_arguments['product']
            order_id = request_arguments['order_id']
        except:
            log.exception("OrderGetHandler PARSE ERROR!!!")

        if order_id:
            order_ready_key = "list:order:ready:{0}".format(self.site)
            order_processing_key = "set:order:processing:{0}".format(self.site)
            master = self.application.redis_driver.master
            if( master.srem(order_processing_key, order_id)  == 1):
                order_key = "order:{0}".format(order_id)
                master.hmset(order_key,{
                    'status': 'ready',
                    'site': None,
                    'site_req_tsp': None,
                })
                master.lpush(order_ready_key, order_id)
                return self.response_result('success','success')
            else:
                return self.response_result('success','invalid order status')
