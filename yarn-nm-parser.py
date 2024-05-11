# -*- coding: utf-8 -*-
import re
import os
import datetime
import time
import commands
from requests import Session
from requests.adapters import HTTPAdapter

log_directory = "/var/log/hadoop-yarn"

now=datetime.datetime.now()
#one_hour_time=(now+datetime.timedelta(hours=-1)).strftime("%Y-%m-%d %H:00:00")
one_hour_str = (now+datetime.timedelta(hours=-1)).strftime("%Y-%m-%d %H")

ip_cmd = "ifconfig -a|grep inet|grep -v 127.0.0.1|grep -v inet6|awk '{print $2}'|grep 10.|head -1"
server_ip = commands.getoutput(ip_cmd)

#print one_hour_time
container_states = []

def extract_application_id(container_id):
    match = re.search(r"container_(\d+_\d+)_\d+_\d+", container_id)
    if match:
        id = match.group(1)
        app_id = "application_%s" % (id)
        return app_id

def extract_info_from_log(file_path):
    global container_states
    cmd = "grep -h '^%s' %s" % (one_hour_str, file_path)
    output = commands.getoutput(cmd)
    for line in output.splitlines():
        state = re.search(r'^(\d+-\d+-\d+\s\d+:\d+:\d+,\d+).*Container (container_\d+_\d+_\d+_\d+) transitioned from (\w+) to (\w+)', line)
        if state:
            cur_time = state.group(1)
            cur_time = cur_time.replace(",",".")
            datetime_obj = datetime.datetime.strptime(cur_time, "%Y-%m-%d %H:%M:%S.%f")
            timestamp_ms = int(time.mktime(datetime_obj.timetuple()) * 1000.0 + datetime_obj.microsecond / 1000.0)
            container_id = state.group(2)
            app_id = extract_application_id(container_id)
            from_state = state.group(3)
            to_state = state.group(4)
            info = ','.join(str(x) for x in (app_id, container_id,from_state,to_state,cur_time,timestamp_ms,server_ip))
            container_states.append(info)
            #print "%s\t%s\t%s\t%s" % (container_id,from_state,to_state,cur_time)
    
for file in os.listdir(log_directory):
    file_path = os.path.join(log_directory, file)
    modify_time = os.path.getmtime(file_path)
    modify_time_tuple= time.localtime(modify_time)
    modify_time_str = time.strftime('%Y-%m-%d %H:%M:%S', modify_time_tuple)
    # print file_path,modify_time_str
    if os.path.isfile(file_path) and "yarn-NODEMANAGER" in file and modify_time_str >= one_hour_str:
        #print (file_path)
        extract_info_from_log(file_path)
class LoadSession(Session):
    def rebuild_auth(self, prepared_request, response):
        """
        No code here means requests will always preserve the Authorization
        header when redirected.
        """
def main(payload,columns):
    """
    Stream load Demo with Standard Lib requests
    """
    username, password = 'ds', 'dsSR123!'
    headers={
        "Content-Type":  "text/html; charset=UTF-8",
        #"Content-Type":  "application/octet-stream",  # file upload
        "connection": "keep-alive",
        "columns": columns,
        "column_separator": ',',
        "Expect": "100-continue",
    }
    database = 'ds'
    tablename = 'yarn_container_state_time'
    api = 'http://10.150.3.30:8030/api/%s/%s/_stream_load' % (database, tablename)
    session = LoadSession()
    adapter = HTTPAdapter(max_retries=3)
    session.mount('http://', adapter)
    session.auth = (username, password)
    response = session.put(url=api, headers=headers, data=payload)
    #response = session.put(url=api, headers=headers, data= open("a.csv","rb")) # file upload
    print(response.json())

if container_states:
    columns = "application_id, container_id,from_state,to_state, change_time, timestamp_ms,server_ip"
    payload = "\n".join(container_states) 
    main(payload, columns)