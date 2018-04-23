import logging
import time
import tornado.gen
from core.result_code import RESULT_CODE

request_log = logging.getLogger("request")

class CheckOrderTask(tornado.ioloop.PeriodicCallback):
    def __init__(self, application, callback_time):
        super(CheckOrderTask, self).__init__(self.tick, callback_time)
        self.application = application
        self.master = None

    @tornado.gen.coroutine
    def tick(self):
        self.master = self.application.redis_driver.master
        self.check_prepare_order_list()
        self.check_ready_order_list()
        self.check_processing_order_list()

    def check_prepare_order_list(self):
        tsp_now = int( time.time() )
        timeout = int( self.application.config['order_timeout']['prepare'] )

        order_prepare_key_list = self.master.keys( "list:order:prepare:*" )

        #检查待处理订单列表是否超时
        for order_prepare_key in order_prepare_key_list:
            timeout_order_list = []
            index = 0
            while True:
                order_id = self.master.lindex(order_prepare_key, index)
                if not order_id:
                    break
                index += 1

                order_key = "order:{0}".format(order_id)
                create_tsp = int( self.master.hget(order_key, 'create_tsp') )
                if (tsp_now - create_tsp) > timeout:
                    request_log.info("CHECK ORDER {0} PREPARE TIMEOUT".format(order_id))
                    timeout_order_list.append(order_id)

                    self.master.hset(order_key, 'result', RESULT_CODE.FAIL)

            #删除list中的订单号
            for order_id in timeout_order_list:
                self.master.lrem(order_prepare_key, 0, order_id)
                self.application.callback_downstream.callback_downstream(order_id)

    #检查已组装的订单, 特殊处理收卡系统的订单
    def check_ready_order_list(self):
        order_ready_key_list = self.master.keys( "list:order:ready:*" )

        tsp_now = int( time.time() )
        timeout = int( self.application.config['order_timeout']['ready'] )
        for order_ready_key in order_ready_key_list:
            index = 0
            timeout_order_list = []
            while True:
                order_id = self.master.lindex(order_ready_key, index)
                if not order_id:
                    break
                index += 1

                order_key = "order:{0}".format(order_id)
                ready_tsp = int( self.master.hget(order_key, 'ready_tsp') )
                if (tsp_now - ready_tsp) > timeout:
                    card_id = self.master.hget(order_key, 'card_id')
                    request_log.info("{0} CHECK ORDER  CARD {1} READY TIMEOUT".format(order_id, card_id))

                    card_site,card_pool, price= self.master.hmget('card:{0}'.format(card_id), 'site', 'card_pool', 'price')
                    card_ready_key = 'list:card:ready:{0}:{1}:{2}'.format(card_site,card_pool, price)
                    timeout_order_list.append(order_id)
                    self.master.rpush(card_ready_key, card_id)

                    self.master.hset(order_key, 'result', RESULT_CODE.FAIL_CARD_VALID)
                    self.master.hset(order_key, 'old_card_id', card_id)
                    self.master.hdel(order_key, 'card_id')
                    self.master.lrem(order_ready_key, 0, order_id)
                    self.application.callback_downstream.callback_downstream(order_id)

    #检查已被猫池取走的订单是否超时
    def check_processing_order_list(self):
        order_unknown_key = "set:order:unknown"
        order_processing_key_list = self.master.keys( "set:order:processing:*" )

        tsp_now = int( time.time() )
        timeout = int( self.application.config['order_timeout']['processing'] )
        for order_processing_key in order_processing_key_list:
            order_list = self.master.smembers(order_processing_key)
            for order_id in order_list:
                order_key = "order:{0}".format(order_id)
                site_req_tsp = int( self.master.hget(order_key, 'site_req_tsp') )
                if (tsp_now - site_req_tsp) > timeout:
                    card_id = self.master.hget(order_key, 'card_id')
                    request_log.info("CHECK ORDER {0} CARD {1} PROCESSING TIMEOUT".format(order_id, card_id))

                    self.master.sadd(order_unknown_key, order_id)
                    self.master.srem(order_processing_key, order_id)

                    self.master.hset(order_key, 'site_result', RESULT_CODE.FAIL_PREPARE_TIMEOUT)
                    self.master.hset(order_key, 'site_msg', '充值超时,结果未知,请登录中石化网站查询')
                    self.master.hset(order_key, 'site_tsp', tsp_now)
                    self.master.hset(order_key, 'status', 'unknown')