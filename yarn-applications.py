#coding=utf-8
import requests
from requests import Session
import time
import datetime
import sys
from requests.adapters import HTTPAdapter

# 计算上一个小时的时间
previous_hour = sys.argv[1]
previous_hour = datetime.datetime.strptime(previous_hour, "%Y%m%d%H")

# 设置上一个小时的开始时间（0分0秒0毫秒）
start_of_previous_hour = previous_hour.replace(minute=0, second=0, microsecond=0)

# 设置上一个小时的结束时间（59分59秒999毫秒）
end_of_previous_hour = start_of_previous_hour + datetime.timedelta(hours=1) - datetime.timedelta(milliseconds=1)

# 将时间转换为时间戳（单位：秒）
start_timestamp = int(time.mktime(start_of_previous_hour.timetuple()))
end_timestamp = int(time.mktime(end_of_previous_hour.timetuple()))

# 将时间戳转换为13位时间戳
start_timestamp_13 = start_timestamp * 1000
# 加1秒，再转换成毫秒，减1毫秒确保毫秒部分为999
end_timestamp_13 = (end_timestamp + 1) * 1000 - 1


values = []

def get_app_info(data):
    global values
    for app in data['apps']['app']:
        app_id = app['id']
        user = app['user']
        name = app['name']
        queue = app['queue']
        state = app['state']
        final_status = app['finalStatus']
        progress = app['progress']
        tracking_ui = app['trackingUI']
        tracking_url = app['trackingUrl']
        diagnostics = app['diagnostics'].replace("\n","").replace(","," ")
        cluster_id = app['clusterId']
        application_type = app['applicationType']
        application_tags = app['applicationTags']
        priority = app['priority']
        started_time = app['startedTime']
        finished_time = app['finishedTime']
        elapsed_time = app['elapsedTime']
        am_container_logs = app.get('amContainerLogs','')
        am_host_http_address = app.get('amHostHttpAddress','')
        allocated_mb = app['allocatedMB']
        allocated_vcores = app['allocatedVCores']
        running_containers = app['runningContainers']
        memory_seconds = app['memorySeconds']
        vcore_seconds = app['vcoreSeconds']
        queue_usage_percentage = app['queueUsagePercentage']
        cluster_usage_percentage = app['clusterUsagePercentage']
        preempted_resource_mb = app['preemptedResourceMB']
        preempted_resource_vcores = app['preemptedResourceVCores']
        num_non_am_container_preempted = app['numNonAMContainerPreempted']
        num_am_container_preempted = app['numAMContainerPreempted']
        log_aggregation_status = app['logAggregationStatus']
        unmanaged_application = app['unmanagedApplication']
        am_node_label_expression = app['amNodeLabelExpression']
        timestamp=datetime.datetime.utcfromtimestamp(started_time/1000)
        dt=timestamp.strftime("%Y-%m-%d")
    
        value = (
            app_id, dt, user, name, queue, state, final_status, progress, tracking_ui, tracking_url, diagnostics,
            cluster_id, application_type, application_tags, priority, started_time, finished_time, elapsed_time,
            am_container_logs, am_host_http_address, allocated_mb, allocated_vcores, running_containers,
            memory_seconds, vcore_seconds, queue_usage_percentage, cluster_usage_percentage,
            preempted_resource_mb, preempted_resource_vcores, num_non_am_container_preempted,
            num_am_container_preempted, log_aggregation_status, unmanaged_application,
            am_node_label_expression
        )
        value_str = "\01".join([str(x) for x in value])
        values.append(value_str)

session = requests.Session()
adapter = HTTPAdapter(max_retries=3)
session.mount('http://', adapter)

api_url = "http://cdhproddn01.yili.com:8088/ws/v1/cluster/apps?finishedTimeBegin={0}&finishedTimeEnd={1}".format(start_timestamp_13, end_timestamp_13)
print(api_url)

data = requests.get(api_url, timeout=10).json()
if data:
    get_app_info(data)

api_url = "http://cdhproddn01.yili.com:8088/ws/v1/cluster/apps?state=RUNNING"
print(api_url)

data = requests.get(api_url, timeout=10).json()
if data:
    get_app_info(data)

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

columns = "id, dt, user, name, queue, state, finalStatus, progress, trackingUI, trackingUrl, diagnostics,clusterId, applicationType, applicationTags, priority, startedTime, finishedTime, elapsedTime,amContainerLogs, amHostHttpAddress, allocatedMB, allocatedVCores, runningContainers,memorySeconds, vcoreSeconds, queueUsagePercentage, clusterUsagePercentage,preemptedResourceMB, preemptedResourceVCores, numNonAMContainerPreempted,numAMContainerPreempted, logAggregationStatus, unmanagedApplication,amNodeLabelExpression"
tablename = 'yarn_applications'

if values:
    payload = ""
    for value in values:
        payload = "\x02".join(values)
    main(payload, tablename, columns)