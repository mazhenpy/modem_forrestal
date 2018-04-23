import json
import logging
import time
import tornado.web
from drivers.encryption_decryption import aes_decrypt, aes_encrypt

log = logging.getLogger("request")

class OrderSyncHandler(tornado.web.RequestHandler):
    def __init__(self,application, request, **kwargs):
        super(OrderSyncHandler,self).__init__(application, request, **kwargs)

        self.site = None
        self.site_config = None

    def response_result(self, status, msg,data=None):
        code = None
        if data != None:
            log.info("OrderSyncHandler RESP DATA - {0}".format(data))
            data = json.dumps({'data': data,"mask_tsp": int(time.time()*1000)})
            code = aes_encrypt(data,self.site_config['aes_pass'], self.site_config['aes_iv'])

        response = json.dumps({'status':status, 'msg':msg, 'code':code})
        log.info("OrderSyncHandler RESP - " + response)
        return self.finish(response)

    def post(self):
        request_body = self.request.body.decode('utf8')
        log.info("OrderSyncHandler REQU - " + request_body)
        request = json.loads(self.request.body.decode('utf8'))

        #解析请求参数
        try:
            self.site = request['site']
            self.site_config = self.application.config['up_user'][self.site]

            code = request['code']
            request_code = aes_decrypt(code, self.site_config['aes_pass'], self.site_config['aes_iv'])
            log.info("OrderSyncHandler REQU2" + request_code)

            request_arguments = json.loads(request_code)
            tsp = request_arguments['mask_tsp']
        except:
            log.exception("OrderSyncHandler PARSE ERROR!!!")
            return self.response_result('fail', 'server exception')

        #获取待同步订单
        try:
            order_list = self.get_manual_order()
            return self.response_result('success', 'success', order_list)
        except:
            log.exception("OrderSyncHandler PARSE ERROR!!!")
            return self.response_result('fail', 'server exception')

    def get_manual_order(self):
        master = self.application.redis_driver.master

        order_list = []
        order_manual_key  = "list:order:manual:{0}".format(self.site)
        while True:
            order_id = None
            try:
                order_id = master.rpop(order_manual_key)
                if not order_id:
                    break
                log.debug("ORDER SYNC {0} >> SITE {1}".format(order_id, self.site))
                order_list.append(order_id)
            except:
                log.exception("get_manual_order exception ORDER_ID = {0} !!!".format(order_id))
                break

        return  order_list


