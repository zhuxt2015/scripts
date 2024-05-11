#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import requests
from datetime import datetime

import sys
reload(sys)
sys.setdefaultencoding('utf8')


def get_neo4j_info():
    neo4j_url = "http://10.150.4.48:7474/db/neo4j/tx/commit"
    username = "wanghe"
    password = "wanghe123"

    # 构建Cypher查询语句
    cypher_query = """
    MATCH data=(p:process{process_name:'cache_pc'}) - [*1..13] ->(t:task) return t
    """

    # 构建HTTP请求头
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # 构建HTTP基本认证信息
    auth = (username, password)

    # 构建包含 Cypher 查询的 'statements' 字段的请求体
    request_body = {
        "statements": [
            {
                "statement": cypher_query
            }
        ]
    }

    # 发送POST请求
    response = requests.post(neo4j_url, data=json.dumps(request_body), headers=headers, auth=auth)
    result_list = []

    # 检查响应状态码
    if response.status_code == 200:
        # 解析JSON响应
        result = response.json()
        dumps = json.dumps(result)
        dt = datetime.now().strftime("%Y-%m-%d")
        # 处理结果
        for record in result["results"]:
            nodes_data = record["data"]
            total_num = len(nodes_data)
            print("节点总数:"+ str(total_num))
            for nodes in nodes_data:
                row = nodes["row"][0]
                data_dict = {
                    "dt": str(dt),
                    "project_id": row["project_id"],
                    "process_id": row["process_id"],
                    "task_id": row["task_id"],
                    "project_name": row["project_name"],
                    "process_name": row["process_name"],
                    "task_name": row["task_name"],
                    "insert_time": str(datetime.now())
                }
                result_list.append(data_dict)
        json_result = json.dumps(result_list)
        return json_result

    else:
        print("Failed to retrieve data. Status code:", response.status_code)
        print("Response content:", response.text)


def stream_load_to_sr(data_json, partitions, dbname, tablename):
    from requests import Session
    class LoadSession(Session):
        def rebuild_auth(self, prepared_request, response):
            """
            No code here means requests will always preserve the Authorization
            header when redirected.
            """

    username, password = 'ds', 'dsSR123!'
    headers = {
        "Content-Type": "text/html; charset=UTF-8",
        "partitions": partitions,
        "Expect": "100-continue",
        "format": "JSON",
        "strip_outer_array": "True",
        "ignore_json_size": "True"
    }
    streamload_url = 'http://10.150.3.30:8030/api/%s/%s/_stream_load' % (dbname, tablename)
    session = LoadSession()
    session.auth = (username, password)
    response = session.put(url=streamload_url, headers=headers, data=data_json)
    print(response.json())
    print("结束")


if __name__ == '__main__':
    print("运行开始时间:{0}********************************************".format(
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    json_data = get_neo4j_info()
    current_datetime = datetime.now()
    # 使用strftime方法生成格式化字符串
    dt = current_datetime.strftime("p%Y%m")
    print("1111111111111111111111111")
    stream_load_to_sr(json_data, partitions=dt, dbname='ds', tablename='mon_cachepc_full_task')
    print("运行结束时间:{0}********************************************".format(
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
