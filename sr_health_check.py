#!/usr/bin/env python
# -*- coding: utf-8 -*-


import pymysql
import datetime
import json
import requests
import argparse
import sys

reload(sys)
sys.setdefaultencoding('utf8')

print('执行开始时间{0}--------------------------------------------------------'.format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))))

parser = argparse.ArgumentParser(description='execute job')
parser.add_argument('-skey', '--serious_key', type=str, default='')

args = parser.parse_args()
serious_key = args.serious_key

# 数据库连接参数
fe_nodes = ["172.23.21.37","172.23.21.43","172.23.21.44"]
port = 9030
user = "ds"
password = "h*3SvRQyan"
# 查询语句，可以是一个简单的查询
comment = ""
max_retries = 3
for fe_node in fe_nodes:
    for retry in range(max_retries):
        try:
            db_config = {
                'host': fe_node,
                'port': port,
                'user': user,
                'password': password,
                'db': 'ds'
            }
            # 创建数据库连接
            conn = pymysql.connect(**db_config)
            cursor = conn.cursor()
            querysql = 'SELECT /*+ SET_VAR(query_timeout = {0}) */ 2;'.format(1+retry)
            print('querysql is : {0}'.format(str(querysql)))
            cursor.execute(querysql)
            # 如果查询成功，数据库正常运行
            print('节点: {0} 正常'.format(db_config["host"]))
            # 关闭游标和连接
            cursor.close()
            conn.close()
            break
        except pymysql.MySQLError as e:
            retry = retry + 1
            # 如果出现错误，数据库可能存在问题
            print("第" + str(retry) + "次重试,节点地址:" + db_config["host"] + ",错误消息: " + str(e))
            if retry == max_retries:
                comment = comment + "host:{0}\n时间:{1}\n错误日志:{2}\n---------------------------------------\n".format(
                str(db_config["host"]), str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")), str(e))
# 异常拨打电话
if(len(comment) > 0):
    webhook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={0}".format(serious_key)
    print("webhook is :", webhook)
    headers = {'content-type': 'application/json'}
    content = "## 生产环境SR异常节点推送\n"
    content = content + "> 推送时间: **" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "**\n"
    content = content + comment
    print(content)
    data = {"msgtype": "markdown", "markdown": {"content": content}}
    r = requests.post(webhook, headers=headers, data=json.dumps(data))
    r.encoding = 'utf-8'
    print(r.text)

print('执行完成时间{0}--------------------------------------------------------'.format(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))))