#coding=utf-8
import requests
from requests import Session
import datetime
import sys
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup

executor_values = []
task_values = []
executor_columns = "application_id, id, addTime, hostPort, isActive, rddBlocks, memoryUsed, diskUsed, totalCores, maxTasks, activeTasks, failedTasks, completedTasks, totalTasks, totalDuration, totalGCTime, totalInputBytes, totalShuffleRead, totalShuffleWrite, isBlacklisted, maxMemory, executorLogs, usedOnHeapStorageMemory, usedOffHeapStorageMemory, totalOnHeapStorageMemory, totalOffHeapStorageMemory, blacklistedInStages,driver_memory,executor_memory,executor_instances,executor_cores,executor_memoryOverhead"

task_columns = "application_id, stage_stageId, task_taskId, stage_submissionTime, stage_jobId, stage_sqlId, stage_status, stage_attemptId, stage_numTasks, stage_numActiveTasks, stage_numCompleteTasks, stage_numFailedTasks, stage_numKilledTasks, stage_numCompletedIndices, stage_executorRunTime, stage_executorCpuTime, stage_firstTaskLaunchedTime, stage_completionTime, stage_inputBytes, stage_inputRecords, stage_outputBytes, stage_outputRecords, stage_shuffleReadBytes, stage_shuffleReadRecords, stage_shuffleWriteBytes, stage_shuffleWriteRecords, stage_memoryBytesSpilled, stage_diskBytesSpilled, stage_name, stage_schedulingPool, stage_rddIds, stage_accumulatorUpdates, stage_killedTasksSummary, task_index, task_attempt, task_launchTime, task_duration, task_executorId, task_host, task_status, task_taskLocality, task_speculative, task_accumulatorUpdates, task_executorDeserializeTime, task_executorDeserializeCpuTime, task_executorRunTime, task_executorCpuTime, task_resultSize, task_jvmGcTime, task_resultSerializationTime, task_memoryBytesSpilled, task_diskBytesSpilled, task_peakExecutionMemory, task_bytesRead, task_recordsRead, task_bytesWritten, task_recordsWritten, task_shuffle_remoteBlocksFetched, task_shuffle_localBlocksFetched, task_shuffle_fetchWaitTime, task_shuffle_remoteBytesRead, task_shuffle_remoteBytesReadToDisk, task_shuffle_localBytesRead, task_shuffle_recordsRead, task_shuffle_bytesWritten, task_shuffle_writeTime, task_shuffle_recordsWritten"

executor_tablename = 'spark_executor'

task_tablename = 'spark_task'

session = requests.Session()
adapter = HTTPAdapter(max_retries=3)
session.mount('http://', adapter)

def transform_GMT_timezone(cst_time):

    # 计算时区差值
    cst_offset = datetime.timedelta(hours=-8)  # GMT时差为8小时

    # 转换为GMT时间
    gmt_time = cst_time + cst_offset

    # 格式化为所需的字符串格式
    gmt_time_str = gmt_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "GMT"
    return gmt_time_str

def transform_CST_timezone(addTime):

    # 解析原始时间字符串为 datetime 对象
    gmt_time = datetime.datetime.strptime(addTime, "%Y-%m-%dT%H:%M:%S.%fGMT")

    # 计算时区差值
    gmt_offset = datetime.timedelta(hours=8)  # 东八区时差为8小时

    # 转换为东八区时间（中国标准时间）
    cst_time = gmt_time + gmt_offset

    # 格式化为所需的字符串格式
    cst_time_str = cst_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # 去掉微秒的后三位，保留毫秒
    return cst_time_str
    
def get_dict(json_obj,parent_key=''):
    value_dict = {}
    for k, v in json_obj.items():
        if v and isinstance(v, dict) and k != "executorLogs":
            prefix = parent_key
            if k.startswith("shuffle"):
                if parent_key:
                    prefix = parent_key + "_shuffle"
            value_dict.update(get_dict(v, prefix))
        else:
            full_key = "%s_%s" % (parent_key,k) if parent_key else k
            value_dict[full_key] = v
    return value_dict
    
def get_one_row_data(comma_separated_str,dic):
    value = []
    for column in comma_separated_str:
        col_value = dic.get(column.strip(),"")
        value.append(col_value)
    value_str = "\01".join([str(x) for x in value])
    return value_str

def get_executor_values(app_id, data, app_conf):
    global executor_values
    global executor_columns
    comma_separated_str = executor_columns.split(',')
    for app in data:
        dic = get_dict(app)
        #合并app conf字典
        dic.update(app_conf)
        dic["application_id"] = app_id
        if "addTime" in dic:
            dic["addTime"] = transform_CST_timezone(dic["addTime"])
        row = get_one_row_data(comma_separated_str,dic)
        executor_values.append(row)

def get_stage_job_ids(app_id):
    stage_job = {}
    api_url = "http://cdhproddn06.yili.com:18088/api/v1/applications/%s/jobs" % app_id
    print(api_url)
    result = session.get(api_url, timeout=10).json()
    if result:
        for job_info in result:
            job_id = job_info["jobId"]
            stageIds = job_info["stageIds"]
            for stage_id in stageIds:
                stage_job[stage_id] = job_id
    return stage_job

def get_executor_info(data):
    for app in data:
        app_id = app["id"]
        api_url = "http://cdhproddn06.yili.com:18088/api/v1/applications/%s/allexecutors" % app_id
        print(api_url)
        result = session.get(api_url, timeout=10).json()
        if result:
            app_conf = get_app_conf(app_id)
            get_executor_values(app_id, result, app_conf)

def get_job_sql_ids(app_id):
    job_sql_ids = {}
    # URL for the web page
    api_url = 'http://cdhproddn06.yili.com:18088/history/%s/SQL/' % app_id
    print(api_url)
    response = session.get(api_url, timeout=10)

    # Check if the request was successful
    if response.status_code == 200 and response.content:
        # Parse the content of the web page
        soup = BeautifulSoup(response.content, 'html.parser')
    
        # Find the table with the specified id
        table = soup.find('table', {'id': 'completed-execution-table'})
    
        if table:
            # Find the table body
            tbody = table.find('tbody')
        
            # Initialize an empty list to store the data
            job_id_array = []
        
            # Iterate over the table rows in tbody
            rows = tbody.find_all('tr')
        
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 4:  # Ensure there are enough columns
                    job_ids = cols[4].text.strip()  # Fifth column is Job IDs
                    if job_ids:
                        job_id_array.append(job_ids)
            sql_index = 1
            for job_ids in job_id_array[::-1]:
                id_array = job_ids.split('][')
                for id in id_array:
                    job_id = id.replace('[', '').replace(']', '')
                    job_sql_ids[int(job_id)] = sql_index
                sql_index = sql_index + 1
        else:
            print('No table found with id "completed-execution-table".')
    else:
        print('Failed to retrieve the web page. Status code:', response.status_code)
    return job_sql_ids
    
#采集task信息
def get_task_info(data):
    global task_values
    comma_separated_str = task_columns.split(',')
    for app in data:
        app_id = app["id"]
        stage_job_ids = get_stage_job_ids(app_id)
        job_sql_ids = get_job_sql_ids(app_id)
        app_status = app["attempts"][0]["completed"]
        if app_status == "false":
            continue
        api_url = "http://cdhproddn06.yili.com:18088/api/v1/applications/%s/stages" % app_id
        print(api_url)
        stage_response = session.get(api_url, timeout=10).json()
        #print stage_response
        if stage_response:
            for stage in stage_response:
                stage_id = stage["stageId"]
                stage_dict = get_dict(stage,"stage")
                job_id = stage_job_ids[stage_id]
                sql_id = -1
                if job_id in job_sql_ids:
                    sql_id = job_sql_ids[job_id]
                
                stage_dict["stage_jobId"] = job_id
                stage_dict["stage_sqlId"] = sql_id
                if "stage_submissionTime" in stage_dict:
                    stage_dict["stage_submissionTime"] = transform_CST_timezone(stage_dict["stage_submissionTime"])
                if "stage_firstTaskLaunchedTime" in stage_dict:
                    stage_dict["stage_firstTaskLaunchedTime"] = transform_CST_timezone(stage_dict["stage_firstTaskLaunchedTime"])
                if "stage_completionTime" in stage_dict:
                    stage_dict["stage_completionTime"] = transform_CST_timezone(stage_dict["stage_completionTime"])
                api_url = "http://cdhproddn06.yili.com:18088/api/v1/applications/%s/stages/%s" % (app_id,stage_id)
                print(api_url)
                stage_detail_response = session.get(api_url, timeout=10).json()
                if stage_detail_response:
                    for stage_detail in stage_detail_response:
                        task = stage_detail["tasks"]
                        for k,v in task.items():
                            task_dict = get_dict(v,"task")
                            task_dict["task_launchTime"] = transform_CST_timezone(task_dict["task_launchTime"])
                            task_dict.update(stage_dict)
                            task_dict["application_id"] = app_id
                            row = get_one_row_data(comma_separated_str,task_dict)
                            task_values.append(row)
#采集app的配置信息
def get_app_conf(app_id):
    app_conf = {}
    dic = {}
    conf_key = {"spark.driver.memory" : "driver_memory", "spark.executor.memory": "executor_memory", "spark.executor.instances" : "executor_instances", "spark.executor.cores" : "executor_cores", "spark.executor.memoryOverhead" : "executor_memoryOverhead"}
    api_url = "http://cdhproddn06.yili.com:18088/api/v1/applications/%s/environment" % app_id
    print(api_url)
    env_response = session.get(api_url, timeout=10).json()
    if env_response:
        for properties in env_response["sparkProperties"]:
            for k, v in conf_key.items():
                if properties[0] == k:
                    dic[v] = properties[1]
                    break
    for v in conf_key.values():
        app_conf[v] = dic.get(v,0)
    return app_conf

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
        sys.exit(1)
        
def insert_data(values,tablename, columns):
    if values:
        payload = "\x02".join(values)
        main(payload, tablename, columns)
        
if __name__=='__main__':
    # 计算上一个小时的时间
    previous_hour = sys.argv[1]
    previous_hour = datetime.datetime.strptime(previous_hour, "%Y%m%d%H")

    # 设置上一个小时的开始时间（0分0秒0毫秒）
    start_of_previous_hour = previous_hour.replace(minute=0, second=0, microsecond=0)

    # 设置上一个小时的结束时间（59分59秒999毫秒）
    end_of_previous_hour = start_of_previous_hour + datetime.timedelta(hours=1) - datetime.timedelta(milliseconds=1)

    minEndDate = transform_GMT_timezone(start_of_previous_hour)
    maxEndDate = transform_GMT_timezone(end_of_previous_hour)

    api_url = "http://cdhproddn06.yili.com:18088/api/v1/applications?minEndDate=%s&maxEndDate=%s" % (minEndDate,maxEndDate)
    print(api_url)
    data = session.get(api_url, timeout=10).json()
    if data:
        #采集executor数据
        get_executor_info(data)
        #采集stage下的task数据
        get_task_info(data)
    
    insert_data(executor_values, executor_tablename,executor_columns)
    insert_data(task_values,task_tablename, task_columns)