# -*- coding: utf-8 -*-
import re
import commands
import pymysql
from multiprocessing import Pool, Manager
import requests
from requests.adapters import HTTPAdapter
import traceback
from requests import Session
import sys
import os

#提取tez任务日志中的统计数据
def extract_tez_log(tez_queue,app_id):
    cmd = "yarn logs -applicationId %s |egrep 'Event:TASK_FINISHED|Assigning container to task'" % (app_id)
    #print cmd
    output = commands.getoutput(cmd)
    container_task_map = {}
    for line in output.splitlines():
        #查找task对应的container，以及container的内存和cpu信息
        match = re.search(r'containerId=([^,]+).+task=([^,]+).+memory:(\d+), vCores:(\d+)',line)
        if match:
            containerId = match.group(1)
            attemptId = match.group(2)
            container_memory = match.group(3)
            container_vcores = match.group(4)
            container_info = (containerId,container_memory,container_vcores)
            container_task_map[attemptId] = container_info
            continue
        match = re.search(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}).+DAG:(dag[_\d+]+).+vertexName=(\w+ \d+),.+taskId=(task[_\d+]+).+status=(\w+)', line)
        if match:
            counter_time = match.group(1)
            counter_time = counter_time.replace(",",".")
            dag_id = match.group(2)
            vertex_name = match.group(3)
            task_id = match.group(4)
            status = match.group(5)
            info = [app_id,dag_id,task_id,vertex_name,counter_time,status]
            pattern = r'(\w+)=([^,]+)'
            counters = re.findall(pattern, line)
            dic = {}
            for counter in counters:
                dic[counter[0]] = counter[1]
            try:
                info.append(dic["startTime"])
                info.append(dic["finishTime"])
                info.append(dic["timeTaken"])
                info.append(dic.get("FILE_BYTES_READ",0))
                info.append(dic.get("FILE_BYTES_WRITTEN",0))
                info.append(dic.get("HDFS_BYTES_READ",0))
                info.append(dic.get("HDFS_BYTES_WRITTEN",0))
                info.append(dic.get("GC_TIME_MILLIS",0))
                info.append(dic.get("CPU_MILLISECONDS",0))
                info.append(dic.get("PHYSICAL_MEMORY_BYTES",0))
                info.append(dic.get("VIRTUAL_MEMORY_BYTES",0))
                info.append(dic.get("COMMITTED_HEAP_BYTES",0))
                info.append(dic.get("INPUT_RECORDS_PROCESSED",0))
                info.append(dic.get("SHUFFLE_BYTES",0))
                info.append(dic.get("SHUFFLE_PHASE_TIME",0))
                info.append(dic.get("MERGE_PHASE_TIME",0))
                 
                successfulAttemptID = dic["successfulAttemptID"]
                if successfulAttemptID != 'null' and container_task_map.has_key(successfulAttemptID):
                    task_container_info = container_task_map[successfulAttemptID]
                    info.extend(task_container_info)
                else:
                    info.extend(("",0,0))
                tez_queue.put(info)
            except Exception as e:
                print "Unable to parse application %s:%s" % (app_id,e)
                traceback.print_exc()
                
def get_vertex_name(attempt_id):
    # 使用正则表达式从容器ID中提取任务类型和索引
    match = re.match(r'attempt_\d+_\d+_(m|r)_(\d+)_\d+', attempt_id)
    if match:
        task_type = match.group(1)
        if task_type == 'm':
            task_type = "Map"
        else:
            task_type = "Reducer"
        task_index = int(match.group(2)) + 1
        return task_type + ' ' + str(task_index)
    else:
        return ''
def get_task_id(attempt_id):
    # 使用正则表达式从容器ID中提取任务类型和索引
    match = re.match(r'attempt_(\d+_\d+_[m|r]_\d+)_\d+', attempt_id)
    if match:
        task_id = match.group(1)
        task_id = "task_" + task_id
        return task_id
    else:
        return None
def put_counters_to_queue(dic,info,tez_queue):
    info.append(dic["startTime"])
    info.append(dic["finishTime"])
    info.append(dic["timeTaken"])
    info.append(dic.get("FILE_BYTES_READ",0))
    info.append(dic.get("FILE_BYTES_WRITTEN",0))
    info.append(dic.get("HDFS_BYTES_READ",0))
    info.append(dic.get("HDFS_BYTES_WRITTEN",0))
    info.append(dic.get("GC_TIME_MILLIS",0))
    info.append(dic.get("CPU_MILLISECONDS",0))
    info.append(dic.get("PHYSICAL_MEMORY_BYTES",0))
    info.append(dic.get("VIRTUAL_MEMORY_BYTES",0))
    info.append(dic.get("COMMITTED_HEAP_BYTES",0))
    info.append(dic.get("MAP_INPUT_RECORDS",0))
    info.append(dic.get("REDUCE_SHUFFLE_BYTES",0))
    info.append(dic.get("SHUFFLE_PHASE_TIME",0))
    info.append(dic.get("MERGE_PHASE_TIME",0))
    info.append(dic.get("assignedContainerId",""))
    info.append(dic.get("memory",0))
    info.append(dic.get("vcores",0))
    tez_queue.put(info)
    
#通过jobhistory api获取mr任务的信息
def mr_attempt_counters(session,job_id,task_id,attempt_id,memory_vcores):
    dic = {}
    timeout = 10
    url = "http://cdhprodnm01.yili.com:19888/ws/v1/history/mapreduce/jobs/%s/tasks/%s/attempts/%s" % (job_id,task_id,attempt_id)
    data = session.get(url, timeout=timeout).json()
    dic["startTime"] = data['taskAttempt']['startTime']
    dic["finishTime"] = data['taskAttempt']['finishTime']
    dic["timeTaken"] = data['taskAttempt']['elapsedTime']
    dic["assignedContainerId"] = data['taskAttempt']['assignedContainerId']
    if 'r' in attempt_id:
        dic["memory"] = memory_vcores["mapreduce.reduce.memory.mb"]
        dic["vcores"] = memory_vcores["mapreduce.reduce.cpu.vcores"]
        dic["SHUFFLE_PHASE_TIME"] = data['taskAttempt']['elapsedShuffleTime']
        dic["MERGE_PHASE_TIME"] = data['taskAttempt']['elapsedMergeTime']
    else:
        dic["memory"] = memory_vcores["mapreduce.map.memory.mb"]
        dic["vcores"] = memory_vcores["mapreduce.map.cpu.vcores"]
    
    url = "http://cdhprodnm01.yili.com:19888/ws/v1/history/mapreduce/jobs/%s/tasks/%s/attempts/%s/counters" % (job_id,task_id,attempt_id)
    data = session.get(url, timeout=timeout).json()
    counter_groups = data["jobTaskAttemptCounters"]["taskAttemptCounterGroup"]
    # 遍历每个counter group
    for group in counter_groups:
        # 遍历该组中的每个counter
        for counter in group["counter"]:
            counter_name = counter["name"]
            counter_value = counter["value"]
            dic[counter_name] = counter_value
    return dic
#提取mr任务日志中的统计数据
def extract_mr_log(tez_queue,app_id):
    
    job_id = app_id.replace("application","job")
    url = "http://cdhprodnm01.yili.com:19888/ws/v1/history/mapreduce/jobs/%s/conf" % job_id
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=3)
    session.mount('http://', adapter)
    data = session.get(url, timeout=10).json()
    
    memory_vcores = {}
    # 提取 mapreduce map和reduce的memory和vcores信息
    for property in data['conf']['property']:
        if property['name'] == 'mapreduce.map.cpu.vcores':
            memory_vcores[property['name']] = property['value']
            continue
        if property['name'] == 'mapreduce.reduce.cpu.vcores':
            memory_vcores[property['name']] = property['value']
            continue
        if property['name'] == 'mapreduce.map.memory.mb':
            memory_vcores[property['name']] = property['value']
            continue
        if property['name'] == 'mapreduce.reduce.memory.mb':
            memory_vcores[property['name']] = property['value']
            continue
    cmd = "yarn logs -applicationId %s |grep 'Final Counters for'" % (app_id)
    output = commands.getoutput(cmd)
    for line in output.splitlines():
        match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}).+(attempt_\d+_\d+_\w+_\d+_\d+)', line)
        if match:
            counter_time = match.group(1)
            counter_time = counter_time.replace(",",".")
            attempt_id = match.group(2)
            task_id = get_task_id(attempt_id)
            vertex_name = get_vertex_name(attempt_id)
            info = [app_id,task_id,task_id,vertex_name,counter_time,"SUCCEEDED"]
            try:
                dic = mr_attempt_counters(session,job_id,task_id,attempt_id,memory_vcores)
                put_counters_to_queue(dic,info,tez_queue)
            except Exception as e:
                print "Unable to parse application %s:%s" % (app_id,e)
                traceback.print_exc()

def insert_results(q,previous_hour):
    payload = ""
    file_path = "/tmp/yarn_app_logs_parser_%s.csv" % previous_hour
    print file_path
    if(os.path.isfile(file_path)):
        os.remove(file_path)
    with open(file_path,'w') as file:
        while not q.empty():
            item = q.get()
            payload = ",".join([str(x) for x in item]) + "\n"
            file.write(payload)
        
    main(file_path)

class LoadSession(Session):
    def rebuild_auth(self, prepared_request, response):
        """
        No code here means requests will always preserve the Authorization
        header when redirected.
        """
def main(file_path):
    """
    Stream load Demo with Standard Lib requests
    """
    username, password = 'ds', 'dsSR123!'
    
    database = 'ds'
    tablename = 'yarn_container_counters'
    columns = "application_id,dag_id,task_id,vertex_name,counter_time,status,startTime,finishTime,timeTaken,file_bytes_read,file_bytes_written,hdfs_bytes_read,hdfs_bytes_written,gc_time_millis,cpu_milliseconds,physical_memory_bytes,virtual_memory_bytes,committed_heap_bytes,input_records_processed,shuffle_bytes,shuffle_phase_time,merge_phase_time,container_id,container_memory_mb,container_vcores"
    api = 'http://10.150.3.30:8030/api/%s/%s/_stream_load' % (database, tablename)
    headers={
        #"Content-Type":  "text/html; charset=UTF-8",
        "Content-Type":  "application/octet-stream",  # file upload
        "connection": "keep-alive",
        "columns": columns,
        "column_separator": ',',
        "Expect": "100-continue",
    }
    session = LoadSession()
    session.auth = (username, password)
    #response = session.put(url=api, headers=headers, data=payload)
    try: 
        response = session.put(url=api, headers=headers, data= open(file_path,"rb")) # file upload
        res_json = response.json()
        print(res_json)
        if res_json["Status"] == "Fail":
            print "导入失败"
            sys.exit(1)
    finally:
        print "删除临时文件%s" % file_path
        os.remove(file_path)
    


if __name__=='__main__':
    #获取上一个小时完成的application
    connection = pymysql.connect(
            host='10.150.3.30',
            port=9030,
            user='ds',
            password='dsSR123!',
            database='ds'
        )
    #格式2024010112    
    previous_hour = sys.argv[1]
    with connection.cursor() as cursor:
        sql = "select ya.id,ya.applicationType from task_applications ta join yarn_applications ya on ta.application_id = ya.id where FROM_UNIXTIME(ya.finishedTime / 1000,'%%Y%%m%%d%%H') = '%s' and ya.state != 'RUNNING' " % (previous_hour)
        print sql
        cursor.execute(sql)
        results = cursor.fetchall()
        print "app任务数量%s" % len(results)
    connection.close()
    p = Pool(50)
    # 父进程创建Queue，并传给各个子进程：
    tez_queue = Manager().Queue()
    spark_queue = Manager().Queue()
    for row in results:
        app_id = row[0]
        app_type = row[1]
        if app_type == 'TEZ':
            p.apply_async(extract_tez_log,args=(tez_queue,app_id,))
        if app_type == 'MAPREDUCE':
            p.apply_async(extract_mr_log,args=(tez_queue,app_id,))
    # 关闭进程池，表示不能再往进程池中添加进程，需要在join之前调用
    p.close()
    # 等待进程池中的所有进程执行完毕
    p.join()
    if not tez_queue.empty():
        print "总记录数%s" % tez_queue.qsize()
        insert_results(tez_queue,previous_hour)