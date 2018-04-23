import logging
import time

request_log = logging.getLogger("request")

class AssembleOrder:
    def __init__(self,application):
        self.application = application
        self.master = self.application.redis_driver.master

    def assemble_order(self,up_user_id):
        #判断当前组装好的的订单是不是太多了
        if up_user_id not in self.application.config['up_user']:
            order_ready_key = 'list:order:ready:{0}'.format(self.application.config['config']['public_site'])
        else:
            order_ready_key = "list:order:ready:{0}".format(up_user_id)

        ready_order_count = self.master.llen(order_ready_key)
        config_ready_list_len = int( self.application.config['order_pool_limit']['ready'] )
        if ready_order_count >= config_ready_list_len:
            request_log.debug('{0} LIMIT TOUCH READY LIST {1}'.format(up_user_id, config_ready_list_len))
            return

        for price in self.application.config['price_support']:
            #组装该面值的订单
            order_prepare_key = "list:order:prepare:{0}:{1}".format(up_user_id, price)
            if not self.master.llen(order_prepare_key):
                continue

            while True:
                #取订单
                order_id = self.master.rpop(order_prepare_key)
                if not order_id:
                    break

                #取卡 ->应对多个卡库的情况
                card_id = None
                card_pool_config_key_list = self.master.keys("card_pool_config:*")
                for card_pool_config_key in card_pool_config_key_list:
                    site = card_pool_config_key.split(':')[1]

                    card_pool_user_config = self.master.get( 'card_pool:user_config:{0}:{1}'.format(site, up_user_id) )
                    if card_pool_user_config:
                        card_pool_list = eval( card_pool_user_config )
                        for card_pool in card_pool_list:
                            card_list_key = 'list:card:ready:{0}:{1}:{2}'.format(site, card_pool, price)
                            card_id = self.master.rpop(card_list_key)
                            request_log.info(">>>>RPOP %s %s %s"%(card_pool, card_list_key, card_id))
                            if card_id:
                                break
                    else:
                        #没有特殊配置的用户使用公共使用卡池
                        card_pool = self.master.hget(card_pool_config_key, 'pub_use_pool')
                        card_list_key = 'list:card:ready:{0}:{1}:{2}'.format(site, card_pool, price)
                        card_id = self.master.rpop(card_list_key)

                    if card_id:
                            break

                #虚假供卡代码，用于测试
                # card_id = int(time.time()*1000)
                # self.master.hmset('card:{0}'.format(card_id),
                #                   {'password':'32885255902727530199',
                #                    'card_create_time': '32885255902727530199',
                #                    'card_filename': '32885255902727530199',
                #                    'card_package': '32885255902727530199',
                #                    })

                #订单找不到卡就返回
                if not card_id:
                    if order_id:
                        request_log.debug('{0}({1}) ORDER WITHOUT CARD ({2})'.format(order_id,up_user_id, price))
                        self.master.rpush(order_prepare_key,order_id)
                        order_id = None
                    break

                #组装一个订单
                request_log.info('{0} ORDER BIND >> CARD {1}({2})'.format(order_id, card_id,price))
                order_key = "order:{0}".format(order_id)
                self.master.hmset(order_key,
                                  {'status': 'ready',
                                   'ready_tsp': int(time.time()),
                                   'card_id':card_id,
                                   'up_user_id': up_user_id,
                                   })
                self.master.hmset('card:{0}'.format(card_id), {'order_id':order_id, 'user_id':up_user_id})

                self.master.lpush(order_ready_key, order_id)

                ready_order_count += 1
                if ready_order_count >= config_ready_list_len:
                    break
