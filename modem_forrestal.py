import os
import logging
import logging.config

from tornado.web import StaticFileHandler
import tornado.web
import tornado.httpserver
import yaml

from core.assemble_order import AssembleOrder
from core.callback_downstream import CallbackDownstream
from drivers.redis_driver import RedisDriver
from handlers.admin.config import ConfigHandler
from handlers.admin.reload import ReloadHandler
from handlers.api.card_inventory import ApiCardInventoryHandler
from handlers.api.inventory import ApiInventoryHandler
from handlers.api.order_finish import ApiOrderFinishHandler, ApiOrderFinishHandler2
from handlers.api.order_unknown import ApiOrderUnknownHandler
from handlers.api.states import ApiStatesHandler
from handlers.modem.order_get import OrderGetHandler
from handlers.modem.order_rollback import OrderRollbackHandler
from handlers.modem.order_set import OrderSetHandler
from handlers.modem.order_sync import OrderSyncHandler
from handlers.order import OrderHandler
from handlers.supply.card import CardInquiryHandler, CardUsedHandler, CardPoolConfig, CardSupplyHandler
from portmanager.sync import PortManager
from tasks.task_check_order import CheckOrderTask

LOGO = r'''
___________                                   __         .__        /\ _____________   ____         .________________
\_   _____/_________________   ____   _______/  |______  |  |      / / \_   ___ \   \ /   /         |   ____/   __   \
 |    __)/  _ \_  __ \_  __ \_/ __ \ /  ___/\   __\__  \ |  |     / /  /    \  \/\   Y   /  ______  |____  \\____    /
 |     \(  <_> )  | \/|  | \/\  ___/ \___ \  |  |  / __ \|  |__  / /   \     \____\     /  /_____/  /       \  /    /
 \___  / \____/|__|   |__|    \___  >____  > |__| (____  /____/ / /     \______  / \___/           /______  / /____/
     \/                           \/     \/            \/       \/             \/                         \/
'''

request_log = logging.getLogger("request")


class Application(tornado.web.Application):
    def __init__(self):
        cfg = yaml.load(open('logging.yaml', 'r'))
        logging.config.dictConfig(cfg)

        self.load_config()

        handlers = [
            # order
            (r"/order.do", OrderHandler),

            # modem
            (r"/api/modem/order.get", OrderGetHandler),
            (r"/api/modem/order.set", OrderSetHandler),
            (r"/api/modem/order.rollback", OrderRollbackHandler),
            (r"/api/modem/order.sync", OrderSyncHandler),

            # card supply
            (r"/card/inquiry", CardInquiryHandler),
            (r"/card/supply", CardSupplyHandler),
            (r"/card/used", CardUsedHandler),
            (r"/card/card_pool_config", CardPoolConfig),

            # api
            (r"/api/order/unknown", ApiOrderUnknownHandler),
            (r"/api/order/finish", ApiOrderFinishHandler),
            (r"/api/order/finish2", ApiOrderFinishHandler2),
            (r"/api/card/inventory", ApiCardInventoryHandler),
            (r"/api/inventory", ApiInventoryHandler),
            (r"/api/states", ApiStatesHandler),

            # admin
            (r"/admin/reload", ReloadHandler),
            (r"/admin/config", ConfigHandler),
        ]

        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            cookie_secret='VoGTaZcHTAKHF7cIL1/ZxFQxfNT/jEPNrE6KtgBQgVg=',
            debug=False)

        tornado.web.Application.__init__(self, handlers, **settings)

        self.assemble_order = AssembleOrder(self)
        self.callback_downstream = CallbackDownstream(self)

        self.port_manager = PortManager(self)


    def load_config(self):
        config = yaml.load(open('config.yaml', 'r', encoding='utf8'))
        up_user = yaml.load(open('up_user.yaml', 'r', encoding='utf8'))

        self.config = config
        self.config['up_user']  = up_user.get('up_user')
        self.redis_driver = RedisDriver(self.config['cache'])
        self.product_type = self.config['config']['product_type']

if __name__ == '__main__':
    application = Application()
    port = application.config['config']['port']
    http_server = tornado.httpserver.HTTPServer(application, xheaders=True)
    http_server.listen(port)

    request_log.info(LOGO)
    request_log.info('Listen on http://localhost:{0}/order.do'.format(port))

    CheckOrderTask(application, 2 * 1000).start()
    tornado.ioloop.IOLoop.instance().start()
