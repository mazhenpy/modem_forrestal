import json
import logging

from handlers import BaseHandler

request_log = logging.getLogger("forrestal.request")

class ApiCardInventoryHandler(BaseHandler):
    def get(self):
        card_inventory_info = []
        card_inventory_key_list = self.slave.keys('card_inventory_info:*')
        for card_inventory_key in card_inventory_key_list:
            temp_list = card_inventory_key.split(':')
            site = temp_list[1]
            card_pool = temp_list[2]

            card_pool_inventory_info = self.slave.hgetall(card_inventory_key)
            card_pool_cache_inventory_info = self.slave.hgetall( 'card_cache_info:{0}:{1}'.format(site, card_pool) )

            card_inventory_info.append({'site': site, 
                                        'card_pool': card_pool, 
                                        'info': {'inventory': card_pool_inventory_info,
                                        'cache_inventory': card_pool_cache_inventory_info}
                                        })

        return  self.finish(json.dumps({'card_inventory_info': card_inventory_info}))