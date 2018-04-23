from redis import sentinel
from redis.sentinel import Sentinel


class RedisDriver:
    def __init__(self, config):
        self.config = config
        sentinels = [(c['ip'], c['port']) for c in self.config['sentinels']]
        self.sentinel = Sentinel(sentinels, socket_timeout=0.1, db=self.config['db'],decode_responses=True)

    @property
    def master(self):
        return self.sentinel.master_for(self.config['name'],password=self.config.get('auth',''))

    @property
    def slave(self):
        return self.sentinel.slave_for(self.config['name'],password=self.config.get('auth',''))
