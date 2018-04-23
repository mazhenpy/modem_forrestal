import json
import logging

from handlers import JsonHandler

request_log = logging.getLogger("forrestal.request")

class ApiInventoryHandler(JsonHandler):
    def post(self):
        up_user_id = self.json_args['up_user_id']

        card_inventory_info = []
        card_pool_config_key_list = self.master.keys("card_pool_config:*")
        for card_pool_config_key in card_pool_config_key_list:
            site = card_pool_config_key.split(':')[1]

            card_pool_user_config = self.master.get( 'card_pool:user_config:{0}:{1}'.format(site, up_user_id) )
            if card_pool_user_config:
                card_pool_list = eval( card_pool_user_config )
                for card_pool in card_pool_list:
                    card_pool_inventory_info = self.slave.hgetall('card_inventory_info:{0}:{1}'.format(site, card_pool))
                    card_pool_cache_inventory_info = self.slave.hgetall( 'card_cache_info:{0}:{1}'.format(site, card_pool) )
                    card_inventory_info.append({'site': site,
                                                'card_pool': card_pool,
                                                'info': {'inventory': card_pool_inventory_info,
                                                'cache_inventory': card_pool_cache_inventory_info}
                                                })

        #虚假库存信息
        # card_inventory_info.append({'site':'1', 'card_pool':'1', 'info':{'inventory':{'100':1000}, 'cache_inventory':{'100':1000}}})
        # return  self.finish(json.dumps({'card_inventory_info': card_inventory_info}))

        return  self.finish(json.dumps({'card_inventory_info': card_inventory_info}))