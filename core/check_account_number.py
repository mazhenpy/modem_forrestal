def sinopec_get_card_area(card_num):
    province_map = {
        '11':'北京市',
        '12':'天津市',
        '13':'河北省',
        '14':'山西省',
        '15':'内蒙古自治区',
        '21':'辽宁省',
        '22':'吉林省',
        '23':'黑龙江省',
        '31':'上海市',
        '32':'江苏省',
        '33':'浙江省',
        '34':'安徽省',
        '35':'福建省',
        '36':'江西省',
        '37':'山东省',
        '41':'河南省',
        '42':'湖北省',
        '43':'湖南省',
        '44':'广东省',
        '45':'广西省',
        '46':'海南省',
        '50':'重庆市',
        '51':'四川省',
        '52':'贵州省',
        '53':'云南省',
        '54':'西藏自治区',
        '61':'陕西省',
        '62':'甘肃省',
        '63':'青海省',
        '64':'宁夏自治区',
        '65':'新疆自治区',
        '90':'深圳市',
        '91':'北京龙禹',
    }

    province_key = card_num[6:8]
    if province_key == '86':
        province_key = card_num[8:10]

    return province_map.get(province_key)


def check_account_number(product_type, account_number):
    if product_type == 'sinopec':
        if not account_number.isdigit():
            return False

        if len(account_number) != 19:
            return False

        if not sinopec_get_card_area(account_number):
            return False

        return True
    else:
        return False

if __name__ == "__main__":
    print( check_account_number('SINOPEC', '1000113200012159007') )