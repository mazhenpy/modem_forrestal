from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class MysqlDriver:
    def __init__(self, config):
        engine = create_engine(
            config['url'],
            pool_size=2, echo=True, echo_pool=True, pool_recycle=3600)
        self.session_maker = sessionmaker(bind=engine)

    @property
    def session(self):
        return self.session_maker()