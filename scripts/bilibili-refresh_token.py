# -*- coding: utf-8 -*-
import requests
import redis
import pymongo
import certifi
import hashlib
import time
from datetime import datetime
import os
import urllib.parse


def appSign(params, appkey, appsec):  # https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/other/API_sign.md
    params.update({'appkey': appkey})
    params = dict(sorted(params.items()))  # 重排序参数 key
    query = urllib.parse.urlencode(params)  # 序列化参数
    sign = hashlib.md5((query+appsec).encode()).hexdigest()  # 计算 api 签名
    params.update({'sign': sign})
    return params


# redis_client = redis.Redis.from_url('')
redis_client = redis.Redis.from_url(os.getenv('REDIS_URL'))
# mongo_client = pymongo.MongoClient('', tlsCAFile=certifi.where())
mongo_client = pymongo.MongoClient(os.getenv('MONGO_URL'), tlsCAFile=certifi.where())


access_key, refresh_token = redis_client.hmget('token', 'bili-access_key', 'bili-refresh_token')
access_key, refresh_token = str(access_key, 'utf-8'), str(refresh_token, 'utf-8')
# print(access_key, refresh_token)

headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
           'User-Agent': 'Mozilla/5.0 BiliDroid/3.11.0 (bbcallen@gmail.com) os/android model/Mi 10 mobi_app/android_i build/6750200 channel/master innerVer/6750200 osVer/12 network/2',
           'Accept-Encoding': 'gzip, deflate',
           'App-Key': 'android_i'}
data = {'access_key': access_key, 'refresh_token': refresh_token, 'build': '6750200', 'channel': 'master', 'mobi_app': 'android_i', 'ts': int(time.time())}
data_sign = appSign(data, 'ae57252b0c09105d', 'c75875c596a69eb55bd119e74b07cfe3')
# print(data_sign)
response = requests.post('https://passport.bilibili.com/x/passport-login/oauth2/refresh_token', headers=headers, data=data_sign)
mongo_client['log']['bili'].insert_one({'date': datetime.utcnow(), 'response': response.text})


res = response.json()
access_key_new, refresh_token_new, expires_at = res['data']['token_info']['access_token'], res['data']['token_info']['refresh_token'], int(time.time())+res['data']['token_info']['expires_in']
# 目前看6个月有效，那么1个月刷新一次
# print(access_key_new, refresh_token_new, expires_at)
redis_client.hset('token', mapping={'bili-access_key': access_key_new, 'bili-refresh_token': refresh_token_new, 'bili-expires_at': expires_at})
