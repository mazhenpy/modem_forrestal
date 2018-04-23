from sqlalchemy import Column, Integer, String, DateTime, Date
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


'''
DROP TABLE IF EXISTS  `sinopec_forrestal_order`;
CREATE TABLE `sinopec_forrestal_order` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` varchar(20) DEFAULT NULL COMMENT '订单用户id',
  `order_id` varchar(30) NOT NULL COMMENT '订单号',
  `account_number` varchar(30) NOT NULL COMMENT '充值账号',
  `result` varchar(10) NOT NULL COMMENT '最终的充值结果',
  `status` enum('prepare','ready','processing','finish','unknown') NOT NULL DEFAULT 'unknown',
  `price` int(11) NOT NULL,
  `account_price` int(11) DEFAULT NULL COMMENT '实际到账金额',
  `create_tsp` datetime NOT NULL,
  `card_id` varchar(30) DEFAULT NULL,
  `ready_tsp` datetime DEFAULT NULL,
  `site` varchar(20) DEFAULT NULL,
  `bot_account` varchar(20) DEFAULT NULL COMMENT '外挂账号用户名',
  `site_req_tsp` datetime DEFAULT NULL,
  `site_result_tsp` datetime DEFAULT NULL,
  `site_data` varchar(400) DEFAULT NULL,
  `site_result` varchar(10) DEFAULT NULL,
  `site_msg` varchar(100) DEFAULT NULL,
  `manual_user` varchar(20) DEFAULT NULL,
  `manual_result` varchar(10) DEFAULT NULL,
  `manual_result_tsp` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=20162 DEFAULT CHARSET=utf8;
'''
class SinopecForrestalOrder(Base):
    __tablename__ = 'sinopec_forrestal_order'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String)
    order_id = Column(String)
    account_number = Column(String)
    result = Column(String)
    status = Column(String)
    price = Column(Integer)
    account_price = Column(Integer)
    create_tsp = Column(DateTime)
    card_id = Column(String)
    ready_tsp = Column(DateTime)
    site = Column(String)
    bot_account = Column(String)
    site_req_tsp = Column(DateTime)
    site_result_tsp = Column(DateTime)
    site_data = Column(String)
    site_result = Column(String)
    site_msg = Column(String)
    manual_user = Column(String)
    manual_result = Column(String)
    manual_result_tsp = Column(DateTime)