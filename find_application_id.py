# -*- coding: utf-8 -*-
import re
import os
import datetime
import pymysql
import sys
import time
from requests import Session
from requests.adapters import HTTPAdapter
import commands

previous_hour = sys.argv[1]
logs_dir = "/home/dolphinscheduler-1.3.8/ds/logs"
#logs_dir = "/home/dolphinscheduler-1.3.8/ds/logs/2131/3330821/"
#logs_dir = "/home/dolphinscheduler-1.3.8/ds/logs/1344/3322565"

task_info_pattern = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}).*?/tmp/dolphinscheduler/exec/process/(\d+)/(\d+)/(\d+)/(\d+)"
connection = pymysql.connect(
    host='10.150.3.30',
    port=9030,
    user='ds',
    password='dsSR123!',
    database='ds'
)

values = []

def parse_application_id_query_id(log_file_path):
    ids = set()
    cmd = "egrep 'application_|Completed executing command\(queryId=hive_' %s" % log_file_path
    output = commands.getoutput(cmd)
    #print output
    app_id_match = re.findall(r"application_\d+_\d+", output)
    if app_id_match:
        ids.update(app_id_match)
    match = re.findall(r'hive_\d+_[a-z0-9-]+',output)
    if match:
        ids.update(match)
    return ids
    

def process_log_file(log_file_path, modify_date):
    first_line = ""
    apps = set()
    global values
    #遍历整个文件
    with open(log_file_path, "r") as file:
        first_line= file.readline().strip()
    match = re.search(task_info_pattern, first_line)
    if match:
        project_id = match.group(2)
        if int(project_id) == 33:
            print "不解析运维监控项目"
            return
    #获取执行脚本
    cmd = "grep 'raw script :' %s" % log_file_path
    output = commands.getoutput(cmd)
    raw_script_match = re.search(r"raw script : (.*)", output)
    raw_script = raw_script_match.group(1) if raw_script_match else None
    
    app_ids = parse_application_id_query_id(log_file_path)
    if app_ids:
        apps.update(app_ids)

        
    cmd = "grep -E '\t.*/DATA.*\.log' %s" % log_file_path
    output = commands.getoutput(cmd)
    match = re.search(r"^\t.*?(/DATA.*\.log)", output) if output else None
    if match:
        log_path = match.group(1)
        print "任务内置的日志路径:%s" % log_path
        app_ids = parse_application_id_query_id(log_path)
        if app_ids:
            apps.update(app_ids)
    
    cmd = "grep -E '日志.*\/datalake\/datalake_log\/.*' %s" % log_file_path
    output = commands.getoutput(cmd)
    match = re.search(r"日志.*\s?(\/datalake\/datalake_log\/.*)", output) if output else None
    if match:
        log_path = match.group(1)
        print "任务内置的日志路径:%s" % log_path
        app_ids = parse_application_id_query_id(log_path)
        if app_ids:
            apps.update(app_ids)
            
    if apps:
        match = re.search(task_info_pattern, first_line)
        if not match:
            return
        task_start_time = match.group(1)
        project_id = match.group(2)
        definition_id = match.group(3)
        instance_id = match.group(4)
        task_id = match.group(5)
        sql = ""
        match = re.search(r".*\s(/.*?\.sql)",raw_script)
        if match:
            sql = match.group(1)

        for app_id in apps:
            hive_query_id = ""
            if app_id.startswith("hive"):
                hive_query_id = app_id
                query_sql = "select application_id from hiveserver2_query_log where query_id = '%s'" % app_id
                with connection.cursor() as cursor:
                    cursor.execute(query_sql)
                    row = cursor.fetchone()
                    if row is not None:
                        app_id = row[0]
                    else:
                        continue
            value = (task_id,modify_date,app_id,project_id,definition_id,instance_id,raw_script, sql,hive_query_id, task_start_time)
            #print value
            values.append(value)
           
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
        "row_delimiter": '\\x02',
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

# 递归地查找目录下的文件
for root, dirs, files in os.walk(logs_dir):
    for filename in files:
        log_file_path = os.path.join(root, filename)
        # 检查文件的修改日期是否是今天
        if os.path.isfile(log_file_path):
            modified_date = datetime.date.fromtimestamp(os.path.getmtime(log_file_path))
            modified_time = time.localtime(os.path.getmtime(log_file_path))
            formatted_time = time.strftime("%Y%m%d%H",modified_time)
            if str(formatted_time) == previous_hour:
                print log_file_path
                process_log_file(log_file_path, modified_date)
connection.close()
                
columns = "task_id,dt,application_id,project_id,process_definition_id,process_instance_id,script,sql,hive_query_id,task_start_time"
tablename = 'task_applications'
payload = ""
if values:
    for value in values:
        payload = payload + "\x01".join([str(x) for x in value]) + "\x02"
    main(payload, tablename, columns)