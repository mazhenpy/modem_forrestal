

class RESULT_CODE2:
    UNKNOWN_ERROR = '9999'    #未知错误,需进入平台查询核实
    WAIT_CHARGE = '0'         #等待充值
    SUCCESS = '1'             #充值成功
    PROCESSING = '2'          #充值中
    FAIL = '9'                #充值失败已退款
    FAIL_CARD_VALID = '9001'  #充值失败卡有效
    FAIL_CARD_INVALID = '9002'  #充值失败卡失效
    DOWNSTREAM_NOT_EXISTS = '5001'   #代理商不存在
    DOWNSTREAM_INSUFFICIENT_BALANCE = '5002'  #代理商余额不足
    PRODUCT_NOT_EXISTS = '5003'  #此商品暂时不可购买
    PRODUCT_ARGUS_ERROR = '5004'  #充值号码与所选商品不符
    DOWNSTREAM_AUTH_FAIL = '5005' #充值请求验证错误
    DOWNSTREAM_DUAL_ORDER_ID = '5006' #代理商订单号重复
    ODER_ID_NOT_EXISTS = '5007'   #所查询的订单不存在
    DOWNSTREAM_INSUFFICIENT_BALANCE2 = '5008'  #交易亏损不能充值
    DOWNSTREAM_IP_FAIL = '5009'  #IP不符
    WRONG_ACCOUNT_PRICE = '5010'	#商品编号与充值金额不符
    WRONG_BUY_NUM = '5011'	#商品数量不支持
    WRONG_ARGUS = '5012'	#缺少必要参数或参数值不合法
    SERVICE_BUSY = '5013'	#系统繁忙
    UNSUPPORT_PRODUCT_TYPE = '5014' #不支持的产品类型
    DUAL_ACCOUNT_NUMBER = '5015'  #该账号存在在途工单
    FAIL_PREPARE_TIMEOUT = '5016'
    FAIL_READY_TIMEOUT = '5017'
    WRONG_ACCOUNT_NUMBER = '5018'  #账号非法
    WEB_SYS_MAINTANCE = '50019'  #充值卡网站维护
    PASS_ERROR = '50020'   #充值卡密码有误

    FAIL_SEND_FAIL = '902'  #订单发送失败， 登录失败， 卡号错误

class RESULT_CODE:
    UNKNOWN_ERROR = '9999'  #未知错误,需进入平台查询核实
    WAIT_CHARGE = '0'      #等待充值
    SUCCESS = '1'          #充值成功
    PROCESSING = '2'       #充值中
    FAIL = '9'             #充值失败已退款
    FAIL_CARD_VALID = '9001'  #充值失败卡有效
    FAIL_CARD_INVALID = '9002'  #充值失败卡失效
    DOWNSTREAM_NOT_EXISTS = '5003'   #代理商不存在
    DOWNSTREAM_INSUFFICIENT_BALANCE = '5002'  #代理商余额不足
    PRODUCT_NOT_EXISTS = '5003'  #此商品暂时不可购买
    PRODUCT_ARGUS_ERROR = '5003'  #充值号码与所选商品不符
    DOWNSTREAM_AUTH_FAIL = '5003' #充值请求验证错误
    DOWNSTREAM_DUAL_ORDER_ID = '5003' #代理商订单号重复
    ODER_ID_NOT_EXISTS = '5003'   #所查询的订单不存在
    DOWNSTREAM_INSUFFICIENT_BALANCE2 = '5003'  #交易亏损不能充值
    DOWNSTREAM_IP_FAIL = '5003'  #IP不符
    WRONG_ACCOUNT_PRICE = '5003'	#商品编号与充值金额不符
    WRONG_BUY_NUM = '5003'	#商品数量不支持
    WRONG_ARGUS = '5003'	#缺少必要参数或参数值不合法
    SERVICE_BUSY = '5003'	#系统繁忙
    UNSUPPORT_PRODUCT_TYPE = '5003' #不支持的产品类型
    DUAL_ACCOUNT_NUMBER = '5003'  #该账号存在在途工单
    FAIL_PREPARE_TIMEOUT = '5003'
    FAIL_READY_TIMEOUT = '5003'
    WRONG_ACCOUNT_NUMBER = '5003'  #账号非法
    WEB_SYS_MAINTANCE = '5003'  #充值卡网站维护
