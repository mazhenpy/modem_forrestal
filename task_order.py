from datetime import datetime
import json
import logging
import logging.config
import time

import yaml

from db.model import SinopecForrestalOrder
from drivers.mysql_driver import MysqlDriver
from drivers.redis_driver import RedisDriver

task_log = logging.getLogger("madeira.task")

def get_s(obj, binary):
    if binary not in obj:
        return None
    return obj[binary]


def get_i(obj, binary):
    if binary not in obj:
        return None
    try:
        return int(obj[binary])
    except:
        return None


def get_t(obj, binary):
    if binary not in obj:
        return None
    try:
        t = float(obj[binary])
        return datetime.fromtimestamp(t)
    except:
        return None

class OrderTask():
    def __init__(self):
        config = yaml.load(open('config.yaml', 'r', encoding='utf8'))

        self.redis_driver = RedisDriver(config['cache'])
        self.mysql_driver = MysqlDriver(config['database'])

    def persist(self):
        self.master = self.redis_driver.master
        self.session = self.mysql_driver.session

        try:
            all_order_set_key = "set:order"
            all_order_set = self.master.smembers(all_order_set_key)
            for order_id in all_order_set:
                self.save_order(order_id)

            order_finish_key = 'list:order:finish'
            while True:
                order_id = self.master.rpop(order_finish_key)
                if order_id:
                    self.save_order(order_id, True)
                else:
                    break
        finally:
            self.session.close()

    def save_order(self, order_id, is_finish=False):
        try:
            order_key = 'order:{0}'.format(order_id)
            order_info = self.master.hgetall(order_key)

            order = None
            db_key_id = order_info.get('db_key_id')
            if db_key_id:
                order = self.session.query(SinopecForrestalOrder).filter(SinopecForrestalOrder.id == db_key_id).one()

            if not db_key_id and not order:
                order = SinopecForrestalOrder()

            if not order:
                return

            task_log.debug( 'order_info: {0}   {1}'.format(order_key, order_info) )
            task_log.info('@@@{0} PROCESSING START@@@'.format(order_id))

            order.order_id = get_s(order_info,'order_id')
            order.user_id = get_s(order_info, 'up_user_id')
            order.account_number = get_s(order_info, 'account_number')
            order.result = get_s(order_info, 'result')
            order.status = get_s(order_info, 'status')
            order.price = get_i(order_info, 'price')
            order.account_price = get_i(order_info, 'account_price')
            order.create_tsp = get_t(order_info, 'create_tsp')
            order.card_id = get_s(order_info, 'card_id')
            order.ready_tsp = get_t(order_info, 'ready_tsp')
            order.site = get_s(order_info, 'site')
            order.bot_account = get_s(order_info, 'bot_account')
            order.site_req_tsp = get_t(order_info, 'site_req_tsp')
            order.site_result_tsp = get_t(order_info, 'site_result_tsp')
            order.site_data = get_s(order_info, 'site_data')
            order.site_result = get_s(order_info, 'site_result')
            order.site_msg = get_s(order_info, 'site_msg')
            order.manual_user = get_s(order_info, 'manual_user')
            order.manual_result = get_s(order_info, 'manual_result')
            order.manual_result_tsp = get_t(order_info, 'manual_result_tsp')

            self.session.add(order)
            self.session.commit()

            if is_finish:
                self.master.expire(order_key, 8 * 3600)
            else:
                self.master.hset(order_key, 'db_key_id', order.id)

            task_log.info('>>>{0} PROCESSING FINISH<<<'.format(order_id))
        except:
            task_log.exception('persist exception')

if __name__ == "__main__":
    import os

    print(os.getenv('PYTHONPATH'))

    cfg = yaml.load(open('logging_task_order.yaml', 'r'))
    logging.config.dictConfig(cfg)

    task = OrderTask()
    while True:
        task.persist()
        time.sleep(10)
        task_log.info('TASK KEEP RUNNING')
