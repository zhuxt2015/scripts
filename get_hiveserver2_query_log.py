# -*- coding: utf-8 -*-
import os
import re
import datetime
import sys
import commands
import time
from requests import Session
from requests.adapters import HTTPAdapter

log_directory = "/var/log/hive"
previous_hour = sys.argv[1]
ip_cmd = "ifconfig -a|grep inet|grep -v 127.0.0.1|grep -v inet6|awk '{print $2}'|grep 10.|head -1"
hive_server_ip = commands.getoutput(ip_cmd)


values = []

def extract_info_from_log(log_file):
    global values
    app_caller_ids = []
    cmd = "egrep -B 1 'callerId' %s" % log_file
    log_data = commands.getoutput(cmd)
    pattern = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?applicationId=(application_\d+_\d+).*?callerId=(hive_\d+_[a-z0-9-]+)"
    matches = re.findall(pattern, log_data, re.DOTALL)
            
    for match in matches:
        query_time, app_id, caller_id = match
        app_caller_ids.append((query_time, app_id, caller_id))

    for query_time, app_id, query_id in app_caller_ids:
        dt = query_time[:10]
        value = (query_id, app_id,dt,query_time,hive_server_ip)
        values.append(value)
        #print ("log_time:%s, query_id:%s, application_id:%s,time_taken:%f, sql:%s" % (info["log_time"], query_id, info["application_id"], time_taken, sql))

for file in os.listdir(log_directory):
    log_file_path = os.path.join(log_directory, file)
    # 检查文件的修改日期是否是今天
    if os.path.isfile(log_file_path):
        modified_date = datetime.date.fromtimestamp(os.path.getmtime(log_file_path))
        modified_time = time.localtime(os.path.getmtime(log_file_path))
        formatted_time = time.strftime("%Y%m%d%H",modified_time)
        if os.path.isfile(log_file_path) and "HIVESERVER2" in file and str(formatted_time) >= previous_hour:
            print (log_file_path)
            extract_info_from_log(log_file_path)
class LoadSession(Session):
    def rebuild_auth(self, prepared_request, response):
        """
        No code here means requests will always preserve the Authorization
        header when redirected.
        """
def main(payload,tablename,columns):
    """
    Stream load Demo with Standard Lib requests
    """
    username, password = 'ds', 'dsSR123!'
    headers={
        "Content-Type":  "text/html; charset=UTF-8",
        #"Content-Type":  "application/octet-stream",  # file upload
        "connection": "keep-alive",
        "columns": columns,
        "column_separator": '\\x01',
        "Expect": "100-continue",
    }
    database = 'ds'
    api = 'http://10.150.3.30:8030/api/%s/%s/_stream_load' % (database, tablename)
    session = LoadSession()
    adapter = HTTPAdapter(max_retries=3)
    session.mount('http://', adapter)
    session.auth = (username, password)
    response = session.put(url=api, headers=headers, data=payload)
    #response = session.put(url=api, headers=headers, data= open("a.csv","rb")) # file upload
    res_json = response.json()
    print(res_json)
    if res_json["Status"] == "Fail":
        print "导入失败"
        sys.exit(1)
columns = "query_id,application_id,dt,query_time,hive_server_ip"
tablename = 'hiveserver2_query_log'
payload = ""
if values:
    for value in values:
        payload = payload + "\x01".join([str(x) for x in value]) + "\n"
    main(payload, tablename, columns) 