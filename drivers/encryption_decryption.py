
#MD5签名
import hashlib

def md5_signature(part,coding='utf-8'):
    m = hashlib.md5()
    m.update(part.encode(coding))
    return m.hexdigest()


#AES加解密
import base64
from Crypto.Cipher import AES

BS = 16
def padding(s):
    return s + (BS - len(s) % BS) * chr(BS - len(s) % BS)

def unpadding(s):
    return s[0:-ord(s[-1])]

def aes_encrypt(code , aes_pass, aes_iv):
    aes = AES.new(aes_pass, AES.MODE_CBC, aes_iv)
    b = aes.encrypt(padding(code))
    encryption_code = base64.b64encode(b).decode('utf8')
    return  encryption_code

def aes_decrypt(code, aes_pass, aes_iv):
    aes = AES.new(aes_pass, AES.MODE_CBC, aes_iv)
    encrypted = aes.decrypt(base64.b64decode(code))
    decryption_code = unpadding(encrypted.decode('utf8'))
    return  decryption_code
