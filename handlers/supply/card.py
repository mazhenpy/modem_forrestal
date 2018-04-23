import base64
import json
import logging

import tornado.web
from drivers.encryption_decryption import aes_decrypt
from handlers import JsonHandler

request_log = logging.getLogger("request")

#卡池列表的配置信息同步
class CardPoolConfig(JsonHandler):
    @tornado.gen.coroutine
    def post(self):
        request_log.debug('CardPoolConfig REQU: {0}'.format(self.json_args))

        card_pool_config = self.json_args

        site = card_pool_config['site']
        pool_name_list = card_pool_config['pool_name_list']
        user_list = card_pool_config['user_list']

        #更新配置
        card_pool_config_key = "card_pool_config:{0}".format(site)
        self.master.delete(card_pool_config_key)
        self.master.hmset(card_pool_config_key, card_pool_config)

        #检查本地卡池列表，如果卡池被删除，将卡挪到退卡卡池
        local_pool_card_list_key_list = self.master.keys( 'list:card:ready:{0}:*'.format(site) )
        for local_pool_card_list_key in local_pool_card_list_key_list:
            #'list:card:ready:{site}:{card_pool}:{price}'
            name_list = local_pool_card_list_key.split(':')
            if len(name_list) != 6:
                continue

            card_pool = name_list[4]
            if card_pool not in pool_name_list:
                price = name_list[5]
                rollback_pool_card_list_key = 'list:card:rollback:{0}'.format(site)

                #将卡挪动到另外一个卡池里面
                while True:
                    try:
                        card_id = None
                        card_id = self.master.lpop(local_pool_card_list_key)
                        if  card_id:
                            request_log.info("CARD_POOL MOVE CARD {0} FROM {1} TO {2}".format(card_id, card_pool, rollback_pool_card_list_key) )
                            card_key = 'card:' + card_id
                            if self.master.exists(card_key):
                                self.master.hset(card_key, 'card_pool', 'rollback')  #客服界面点击卡释放时会用到这个属性
                                self.master.rpush(rollback_pool_card_list_key, card_id)
                        else:
                            break
                        card_id = None
                    except:
                        request_log.exception("CARD_POOL MOVE CARD {0} FROM {1} TO {2} EXCEPTION".format(card_id, local_pool_card_list_key, rollback_pool_card_list_key) )

                #删除该卡池的库存信息
                card_inventory_key = 'card_inventory_info:{0}:{1}'.format(site,card_pool)
                card_cache_inventory_key = 'card_cache_info:{0}:{1}'.format(site,card_pool)
                self.master.delete(card_inventory_key)
                self.master.delete( card_cache_inventory_key )

        #库存表清理
        card_inventory_key_list = self.master.keys('card_inventory_info:{0}:*'.format(site))
        for card_inventory_key in card_inventory_key_list:
            name_list = card_inventory_key.split(':')
            if len(name_list) != 3:
                continue

            card_pool = name_list[2]
            if card_pool not in pool_name_list:
                #删除该卡池的库存信息
                card_inventory_key = 'card_inventory_info:{0}:{1}'.format(site,card_pool)
                card_cache_inventory_key = 'card_cache_info:{0}:{1}'.format(site,card_pool)
                self.master.delete(card_inventory_key)
                self.master.delete( card_cache_inventory_key )

        #用户列表配置更新, 先清空所有， 然后再配置新的用户列表
        user_config_key_list = self.master.keys('card_pool:user_config:{0}:*'.format(site) )
        for user_config_key in user_config_key_list:
            self.master.delete(user_config_key)

        for user_config in user_list:
            self.master.set('card_pool:user_config:{0}:{1}'.format(site, user_config['user_id']), user_config['card_pool_list'])

        self.finish(json.dumps({'status': 'ok'}))
        request_log.debug('CardPoolConfig RESP')


#将所有用过的卡传回卡库
class CardUsedHandler(JsonHandler):
    @tornado.gen.coroutine
    def post(self):
        site = self.json_args['site']

        card_list = {
            'error': [],
            'used': [],
            'rollback': [],
        }

        error_list = []
        while True:
            card_id = self.master.rpop('list:card:error:%s' % site)
            if card_id is None:
                break
            request_log.info('[SITE %s] [CARD-%s] \033[1;31mREPORT ERROR\033[0m', site, card_id)
            error_list.append(card_id)
            self.master.delete('card:' + card_id)

        card_list['error'] = error_list

        used_list = []

        while True:
            card_id = self.master.rpop('list:card:used:%s' % site)
            if card_id is None:
                break
            request_log.info('[SITE %s] [CARD-%s] REPORT FINISH', site, card_id)
            order_id, user_id =self.master.hmget('card:{0}'.format(card_id), 'order_id', 'user_id')
            used_list.append( {'id': card_id, 'order_id': order_id, 'user_id': user_id} )
            self.master.delete('card:' + card_id)

        card_list['used'] = used_list

        rollback_list = []
        while True:
            card_id = self.master.rpop('list:card:rollback:%s' % site)
            if card_id is None:
                break
            request_log.info('[SITE %s] [CARD-%s] REPORT ROLLBACK', site, card_id)
            rollback_list.append(card_id)
            self.master.delete('card:' + card_id)

        card_list['rollback'] = rollback_list

        request_log.debug('CardUsedHandler RESP: {0}'.format(card_list))
        return self.finish(json.dumps(card_list))


#库存信息同步
class CardInquiryHandler(JsonHandler):
    @tornado.gen.coroutine
    def post(self):
        request_log.debug('CardInquiry REQU: {0}'.format(self.json_args))

        site = self.json_args['site']
        pool_list = self.json_args['pool_list']

        card_cache_inventory_list = {}
        for card_pool in pool_list:
            inventory_info = pool_list[card_pool]
            card_inventory_key = 'card_inventory_info:{0}:{1}'.format(site,card_pool)
            card_cache_inventory_key = 'card_cache_info:{0}:{1}'.format(site,card_pool)

            #更新本地记录的库存信息
            self.master.delete( card_inventory_key )
            self.master.delete( card_cache_inventory_key )

            #获取本地的库存信息
            card_cache_inventory_list[card_pool] = {}
            for price in self.application.config['price_support']:
                card_list_key = 'list:card:ready:{0}:{1}:{2}'.format(site, card_pool, price)

                order_count = 0
                card_count = self.master.llen(card_list_key)

                if price not in inventory_info:
                    inventory_info[price] = 0

                card_cache_inventory_list[card_pool][price] = int(card_count) - int(order_count)

            self.master.hmset( card_inventory_key, inventory_info )
            self.master.hmset( card_cache_inventory_key, card_cache_inventory_list[card_pool] )

        request_log.debug('CardInquiry RESP: {0}'.format(card_cache_inventory_list))
        return self.finish(json.dumps(card_cache_inventory_list))


#接收供卡
class CardSupplyHandler(JsonHandler):
    @tornado.gen.coroutine
    def post(self):
        request_log.debug('CardSupplyHandler REQU: {0}'.format(self.json_args))

        up_user_list = set()
        site = self.json_args['site']
        card_list = self.json_args['card_list']
        for card_info in card_list:
            card_id = card_info['id']
            up_user_id = card_info['user_id']
            card_pool = card_info['card_pool']
            price = card_info['price']

            downstream_config = self.application.config['up_user'].get(up_user_id, {})
            aes_pass = downstream_config.get('aes_pass')
            aes_iv = downstream_config.get('aes_iv')
            if not aes_pass or not aes_iv:
                request_log.error('[SITE %s] [USER %s] [CARDPOOL %s] [CARD-%s] [PRICE-%s] ADD ERROR', site, up_user_id, card_pool, card_id, price)
                self.master.lpush('list:card:rollback:%s' % site, card_id)
                continue

            up_user_list.add(up_user_id)

            card_info['password'] = aes_decrypt(card_info['password'],aes_pass,aes_iv)
            card_info['site'] = site
            self.master.hmset('card:' + card_id, card_info)

            request_log.info('[SITE %s] [USER %s] [CARDPOOL %s] [CARD-%s] [PRICE-%s] ADD SUCCESS', site, up_user_id, card_pool, card_id, price)
            self.master.lpush('list:card:ready:{0}:{1}:{2}'.format(site, card_pool, price), card_id)

        self.finish(json.dumps({'status': 'ok'}))
        request_log.debug('CardSupplyHandler RESP')

        #每次从卡库得到卡之后就立刻进行订单组装工作
        for up_user_id in up_user_list:
            self.application.assemble_order.assemble_order(up_user_id)