# -*- coding: utf-8 -*-
import re
import datetime
import commands
import pymysql
from multiprocessing import Pool, Manager
import requests
from requests.adapters import HTTPAdapter
import traceback
from requests import Session

#提取tez任务日志中的统计数据
def extract_tez_log(map_queue,reducer_queue,app_id):
    cmd = "yarn logs -applicationId %s |grep 'Event:TASK_FINISHED'" % (app_id)
    #print cmd
    output = commands.getoutput(cmd)
    for line in output.splitlines():
        match = re.search(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}).+DAG:(dag[_\d+]+).+vertexName=(\w+ \d+),.+taskId=(task[_\d+]+).+status=(\w+)', line)
        if match:
            counter_time = match.group(1)
            counter_time = counter_time.replace(",",".")
            dag_id = match.group(2)
            vertex_name = match.group(3)
            task_id = match.group(4)
            status = match.group(5)
            info = [app_id,dag_id,task_id,vertex_name,counter_time,status]
            pattern = r'(\w+)=(\d+)'
            counters = re.findall(pattern, line)
            dic = {}
            for counter in counters:
                dic[counter[0]] = counter[1]
            info.append(dic["startTime"])
            info.append(dic["finishTime"])
            info.append(dic["timeTaken"])
            info.append(dic["FILE_BYTES_READ"])
            info.append(dic["FILE_BYTES_WRITTEN"])
            info.append(dic["HDFS_BYTES_READ"])
            info.append(dic["HDFS_BYTES_WRITTEN"])
            info.append(dic["GC_TIME_MILLIS"])
            info.append(dic["CPU_MILLISECONDS"])
            info.append(dic["PHYSICAL_MEMORY_BYTES"])
            info.append(dic["VIRTUAL_MEMORY_BYTES"])
            info.append(dic["COMMITTED_HEAP_BYTES"])
            if 'Map' in vertex_name:
                info.append(dic["INPUT_RECORDS_PROCESSED"])
                info.append(dic["DESERIALIZE_ERRORS"])
                map_queue.put(info)
            elif 'Reducer' in vertex_name:
                info.append(dic["SHUFFLE_BYTES"])
                info.append(dic["SHUFFLE_PHASE_TIME"])
                info.append(dic["MERGE_PHASE_TIME"])
                info.append(dic["BAD_ID"])
                info.append(dic["CONNECTION"])
                info.append(dic["IO_ERROR"])
                info.append(dic["WRONG_LENGTH"])
                info.append(dic["WRONG_MAP"])
                info.append(dic["WRONG_REDUCE"])
                reducer_queue.put(info)
            print info

def extract_tez_log(app_id):
    cmd = "yarn logs -applicationId %s |grep 'Event:TASK_FINISHED'" % (app_id)
    #print cmd
    output = commands.getoutput(cmd)
    for line in output.splitlines():
        match = re.search(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}).+DAG:(dag[_\d+]+).+vertexName=(\w+ \d+),.+taskId=(task[_\d+]+).+status=(\w+)', line)
        if match:
            counter_time = match.group(1)
            counter_time = counter_time.replace(",",".")
            dag_id = match.group(2)
            vertex_name = match.group(3)
            task_id = match.group(4)
            status = match.group(5)
            info = [app_id,dag_id,task_id,vertex_name,counter_time,status]
            pattern = r'(\w+)=(\d+)'
            counters = re.findall(pattern, line)
            dic = {}
            for counter in counters:
                dic[counter[0]] = counter[1]
                print counter[0],counter[1]
            info.append(dic["startTime"])
            info.append(dic["finishTime"])
            info.append(dic["timeTaken"])
            info.append(dic["FILE_BYTES_READ"])
            info.append(dic["FILE_BYTES_WRITTEN"])
            info.append(dic["HDFS_BYTES_READ"])
            info.append(dic["HDFS_BYTES_WRITTEN"])
            info.append(dic["GC_TIME_MILLIS"])
            info.append(dic["CPU_MILLISECONDS"])
            info.append(dic["PHYSICAL_MEMORY_BYTES"])
            info.append(dic["VIRTUAL_MEMORY_BYTES"])
            info.append(dic["COMMITTED_HEAP_BYTES"])
            if 'Map' in vertex_name:
                info.append(dic["INPUT_RECORDS_PROCESSED"])
                info.append(dic["DESERIALIZE_ERRORS"])
            elif 'Reducer' in vertex_name:
                info.append(dic["SHUFFLE_BYTES"])
                info.append(dic["SHUFFLE_PHASE_TIME"])
                info.append(dic["MERGE_PHASE_TIME"])
                info.append(dic["BAD_ID"])
                info.append(dic["CONNECTION"])
                info.append(dic["IO_ERROR"])
                info.append(dic["WRONG_LENGTH"])
                info.append(dic["WRONG_MAP"])
                info.append(dic["WRONG_REDUCE"])
            print info
                
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
def put_counters_to_queue(dic,info,map_queue,reducer_queue):
    vertex_name = info[3]
    info.append(dic["startTime"])
    info.append(dic["finishTime"])
    info.append(dic["timeTaken"])
    info.append(dic["FILE_BYTES_WRITTEN"])
    info.append(dic["FILE_BYTES_READ"])
    info.append(dic["HDFS_BYTES_READ"])
    info.append(dic["HDFS_BYTES_WRITTEN"])
    info.append(dic["GC_TIME_MILLIS"])
    info.append(dic["CPU_MILLISECONDS"])
    info.append(dic["PHYSICAL_MEMORY_BYTES"])
    info.append(dic["VIRTUAL_MEMORY_BYTES"])
    info.append(dic["COMMITTED_HEAP_BYTES"])
    if 'Map' in vertex_name:
        info.append(dic["MAP_INPUT_RECORDS"])
        if not dic.has_key('DESERIALIZE_ERRORS'):
            dic["DESERIALIZE_ERRORS"] = 0
        info.append(dic["DESERIALIZE_ERRORS"])
        map_queue.put(info)
    elif 'Reducer' in vertex_name:
        info.append(dic["REDUCE_SHUFFLE_BYTES"])
        info.append(dic["SHUFFLE_PHASE_TIME"])
        info.append(dic["MERGE_PHASE_TIME"])
        info.append(dic["BAD_ID"])
        info.append(dic["CONNECTION"])
        info.append(dic["IO_ERROR"])
        info.append(dic["WRONG_LENGTH"])
        info.append(dic["WRONG_MAP"])
        info.append(dic["WRONG_REDUCE"])
        reducer_queue.put(info)
#通过jobhistory api获取mr任务的信息
def mr_attempt_counters(dic,job_id,task_id,attempt_id):
    url = "http://cdhproddn02.yili.com:19888/ws/v1/history/mapreduce/jobs/%s/tasks/%s/attempts/%s" % (job_id,task_id,attempt_id)
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=3)
    session.mount('http://', adapter)
    data = session.get(url, timeout=5).json()
    dic["startTime"] = data['taskAttempt']['startTime']
    dic["finishTime"] = data['taskAttempt']['finishTime']
    dic["timeTaken"] = data['taskAttempt']['elapsedTime']
    if 'r' in attempt_id:
        dic["SHUFFLE_PHASE_TIME"] = data['taskAttempt']['elapsedShuffleTime']
        dic["MERGE_PHASE_TIME"] = data['taskAttempt']['elapsedMergeTime']
    
    url = "http://cdhproddn02.yili.com:19888/ws/v1/history/mapreduce/jobs/%s/tasks/%s/attempts/%s/counters" % (job_id,task_id,attempt_id)
    data = session.get(url, timeout=5).json()
    counter_groups = data["jobTaskAttemptCounters"]["taskAttemptCounterGroup"]
    # 遍历每个counter group
    for group in counter_groups:
        # 遍历该组中的每个counter
        for counter in group["counter"]:
            counter_name = counter["name"]
            counter_value = counter["value"]
            dic[counter_name] = counter_value
#提取mr任务日志中的统计数据
def extract_mr_log(map_queue,reducer_queue,app_id):
    cmd = "yarn logs -applicationId %s |grep 'Final Counters for'" % (app_id)
    output = commands.getoutput(cmd)
    dic = {}
    for line in output.splitlines():
        match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}).+(attempt_\d+_\d+_\w+_\d+_\d+)', line)
        if match:
            counter_time = match.group(1)
            counter_time = counter_time.replace(",",".")
            attempt_id = match.group(2)
            task_id = get_task_id(attempt_id)
            vertex_name = get_vertex_name(attempt_id)
            info = [app_id,task_id,task_id,vertex_name,counter_time,"SUCCEEDED"]
            break
    job_id = app_id.replace("application","job")
    try:
        mr_attempt_counters(dic,job_id,task_id,attempt_id)
        put_counters_to_queue(dic,info,map_queue,reducer_queue)
    except Exception as e:
        print "Unable to parse application %s:%s" % (app_id,e)
        traceback.print_exc()
            

def insert_results(q,columns):
    payload = ""
    while not q.empty():
        item = q.get()
        payload = payload + ",".join([str(x) for x in item]) + "\n"
    main(payload, columns)

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
    tablename = 'yarn_container_counters'
    api = 'http://10.150.3.30:8030/api/%s/%s/_stream_load' % (database, tablename)
    session = LoadSession()
    session.auth = (username, password)
    response = session.put(url=api, headers=headers, data=payload)
    #response = session.put(url=api, headers=headers, data= open("a.csv","rb")) # file upload
    print(response.json())


if __name__=='__main__':
    #获取上一个小时完成的application
    connection = pymysql.connect(
            host='10.150.3.30',
            port=9030,
            user='ds',
            password='dsSR123!',
            database='ds'
        )
    now=datetime.datetime.now()
    hour_ago = -1
    one_hour_time=(now+datetime.timedelta(hours=hour_ago)).strftime("%Y-%m-%d %H:00:00")
    with connection.cursor() as cursor:
        sql = "select ya.id,ya.applicationType from task_applications ta join yarn_applications ya on ta.application_id = ya.id where ya.finishedTime/1000 >= unix_timestamp('%s')" % (one_hour_time)
        print sql
        cursor.execute(sql)
        results = cursor.fetchall()
        print "app任务数量%s" % len(results)
    connection.close()
    p = Pool(100)
    # 父进程创建Queue，并传给各个子进程：
    tez_map_queue = Manager().Queue()
    tez_reducer_queue = Manager().Queue()
    app_id = 'application_1706782697500_780098'
    extract_tez_log(app_id)
    # 关闭进程池，表示不能再往进程池中添加进程，需要在join之前调用
    p.close()
    # 等待进程池中的所有进程执行完毕
    p.join()
    if not tez_map_queue.empty():
        print "tez map任务数%s" % tez_map_queue.qsize()
        columns = "application_id,dag_id,task_id,vertex_name,counter_time,status,startTime,finishTime,timeTaken,file_bytes_read,file_bytes_written,hdfs_bytes_read,hdfs_bytes_written,gc_time_millis,cpu_milliseconds,physical_memory_bytes,virtual_memory_bytes,committed_heap_bytes,input_records_processed,deserialize_errors"
        insert_results(tez_map_queue,columns)
    if not tez_reducer_queue.empty():
        print "tez reducer任务数%s" % tez_reducer_queue.qsize()
        columns = "application_id,dag_id,task_id,vertex_name,counter_time,status,startTime,finishTime,timeTaken,file_bytes_read,file_bytes_written,hdfs_bytes_read,hdfs_bytes_written,gc_time_millis,cpu_milliseconds,physical_memory_bytes,virtual_memory_bytes,committed_heap_bytes,shuffle_bytes,shuffle_phase_time,merge_phase_time,bad_id,connection,io_error,wrong_length,wrong_map,wrong_reduce"
        insert_results(tez_reducer_queue,columns)