import time
import xml.etree.ElementTree as ET
from datetime import datetime
import logging

import tornado.gen
import tornado

from core.check_account_number import check_account_number
from core.result_code import RESULT_CODE
from drivers.encryption_decryption import md5_signature
from handlers import BaseHandler
from handlers.api.states import ApiStatesHandler

request_log = logging.getLogger("request")

class Order():
    def __init__(self):
        self.create_tsp = int( time.time() )
        self.account_number = None
        self.user_id = None
        self.price = None
        self.sp_order_id = None
        self.back_url = None

        self.product_id = None

class OrderHandler(BaseHandler):
    @tornado.gen.coroutine
    def post(self):
        request_log.info('DOWNSTREAM REQU {0}'.format(self.request.body.decode()))

        master = self.master

        self.order = Order()
        try:
            order = self.order
            order.product = self.get_body_argument('product')
            if not len( order.product.strip() ):
                request_log.debug('product not exists')
                return self.finish_with_err(self.order, RESULT_CODE.WRONG_ARGUS)

            if order.product != self.application.product_type:
                request_log.debug('unsupport product {0}, only support {1}'.format(order.product, self.application.product_type))
                return self.finish_with_err(self.order, RESULT_CODE.UNSUPPORT_PRODUCT_TYPE)

            #加油卡网站在22:50-0:50是维护状态
            if self.application.product_type == 'sinopec':
                time_now = int( datetime.now().strftime("%H%M") )
                if  time_now > 2240 or time_now < 100:
                    request_log.debug('IN STOP SERVICE TIME!!!')
                    return self.finish_with_err(self.order, RESULT_CODE.WEB_SYS_MAINTANCE)

            order.price = self.get_body_argument('price')
            #查看是否是支持的面值
            if order.price not in self.application.config['price_support']:
                request_log.debug('price {0} not in {1}'.format(order.price, self.application.config['price_support']))
                return self.finish_with_err(self.order, RESULT_CODE.PRODUCT_NOT_EXISTS)

            order.account_number = self.get_body_argument('account_number')
            #检测账号是否合法
            if not check_account_number(order.product, order.account_number):
                request_log.debug('account_numer invalid')
                return self.finish_with_err(self.order, RESULT_CODE.WRONG_ACCOUNT_NUMBER)

            order.sp_order_id = self.get_body_argument('sporderid')
            order.back_url = self.get_body_argument('back_url')
            order.req_time = time.localtime()

            order.product_id = self.get_body_argument('productid')

            order.user_id = self.get_body_argument('userid')
            order.up_user_id = self.get_body_argument('upuserid', default=order.user_id)

            tsp = self.get_body_argument('spordertime')
            sign = self.get_body_argument('sign').upper()

            downstream = self.application.config['downstream'][order.user_id]

            q = 'product=%s&userid=%s&productid=%s&price=%s&num=1&account_number=%s&spordertime=%s&sporderid=%s&key=%s' % (
                order.product,
                order.user_id,
                order.product_id,
                order.price,
                order.account_number,
                tsp,
                order.sp_order_id,
                downstream['md5_key'],
            )

            sign2 = md5_signature(q).upper()

            if sign != sign2:
                request_log.debug('sign check fail!!!')
                return self.finish_with_err(self.order, RESULT_CODE.DOWNSTREAM_AUTH_FAIL)

            if not order.account_number or not order.sp_order_id:
                request_log.debug('account_number or sp_order_id is null.')
                return self.finish_with_err(self.order, RESULT_CODE.PRODUCT_NOT_EXISTS)

            if master.exists(ApiStatesHandler.ORDER_GET_FLAG_KEY):
                request_log.debug('STOP FLAG EXISTS!!!')
                return self.finish_with_err(self.order, RESULT_CODE.PRODUCT_NOT_EXISTS)

            #判断当前未知的订单是不是太多了
            order_unknown_key = "list:order:unknown"
            config_unknown_list_len = int( self.application.config['order_pool_limit']['unknown'] )
            order_unknown_list_len = master.llen(order_unknown_key)
            if order_unknown_list_len >= config_unknown_list_len:
                request_log.debug('LIMIT TOUCH UNKNOWN LIST {0}'.format(config_unknown_list_len))
                return self.finish_with_err(self.order, RESULT_CODE.SERVICE_BUSY)

            #判断当前待处理的订单是不是太多了
            all_order_set_key = "set:order"
            order_prepare_key = "list:order:prepare:{0}:{1}".format(order.up_user_id, order.price)
            config_prepare_list_len = int( self.application.config['order_pool_limit']['prepare'] )
            order_prepare_list_len = master.llen(order_prepare_key)
            if order_prepare_list_len >= config_prepare_list_len:
                request_log.debug('LIMIT TOUCH PREPARE LIST {0}'.format(config_prepare_list_len))
                return self.finish_with_err(self.order, RESULT_CODE.SERVICE_BUSY)

        except Exception as e:
            request_log.exception('ERROR PARSING ORDER %s', e)
            return self.finish_with_err(self.order, RESULT_CODE.DOWNSTREAM_NOT_EXISTS)

        #存储订单
        try:
            order_key = "order:{0}".format(order.sp_order_id)
            master.hmset(order_key, {
                'order_id': order.sp_order_id,
                'user_id': order.user_id,
                'status': 'prepare',
                'account_number': order.account_number,
                'price': order.price,
                'back_url': order.back_url,
                'create_tsp': order.create_tsp,
                'up_user_id': order.up_user_id,
                'result': RESULT_CODE.WAIT_CHARGE,
            })

            master.lpush(order_prepare_key, order.sp_order_id)
            master.sadd(all_order_set_key, order.sp_order_id)
        except Exception as e:
            request_log.exception('ERROR SAVE ORDER %s', e)
            return self.finish_with_err(self.order, RESULT_CODE.UNKNOWN_ERROR)

        self.finish_with_success(self.order, RESULT_CODE.WAIT_CHARGE)

        #尝试组装订单
        self.application.assemble_order.assemble_order(order.up_user_id)


    def finish_with_success(self, order, result):
        root = ET.Element('order')
        ET.SubElement(root, 'resultno').text = result
        ET.SubElement(root, 'orderid').text = order.sp_order_id
        ET.SubElement(root, 'ordercash').text = str(order.price)
        ET.SubElement(root, 'sporderid').text = order.sp_order_id
        ET.SubElement(root, 'mobile').text = order.account_number
        ET.SubElement(root, 'merchantsubmittime').text = time.strftime("%Y%m%d%H%M%S", time.localtime(order.create_tsp))

        self.set_header('Access-Control-Allow-Origin', '*')  # for web-based debugger
        body = ET.tostring(root, encoding='gbk')
        self.finish(body)

        request_log.info('{0} DOWNSTREAM RESP SUCCESS - {1}'.format(order.sp_order_id, body))

    def finish_with_err(self, order, code):
        root = ET.Element('order')
        ET.SubElement(root, 'orderid').text = order.sp_order_id
        ET.SubElement(root, 'sporderid').text = order.sp_order_id
        ET.SubElement(root, 'ordercash').text = ''
        ET.SubElement(root, 'resultno').text = str(code)
        self.set_header('Access-Control-Allow-Origin', '*')  # for web-based debugger
        body = ET.tostring(root, encoding='gbk')
        self.finish(body)

        request_log.info('{0} DOWNSTREAM RESP FAIL - {1}'.format(order.sp_order_id, body))


if __name__ == "__main__":
    print(datetime.now().strftime("%H%M"))