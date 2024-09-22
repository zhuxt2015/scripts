#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
import urllib2
import json
import sys
import requests
import logging
from functools import wraps

# 配置日志
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# 常量定义
PROMETHEUS_URL = 'http://10.119.14.93:9090'
DINKY_BASE_URL = 'https://dlink-clouddp-priv-uat.digitalyili.com/openapi'

def error_handler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error("Error in {0}: {1}".format(func.__name__, str(e)), exc_info=True)
            sys.exit(1)
    return wrapper

@error_handler
def query_prometheus(query):
    url = "{0}/api/v1/query?query={1}".format(PROMETHEUS_URL, urllib2.quote(query))
    response = urllib2.urlopen(url)
    return json.loads(response.read())

@error_handler
def make_dinky_request(endpoint, params=None):
    url = "{0}/{1}".format(DINKY_BASE_URL, endpoint)
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

@error_handler
def restart_job(job_name):
    dinky_job_name = job_name.replace("_", "-")
    result = make_dinky_request("getJobInstanceByTaskName", {"taskName": dinky_job_name})
    
    if not result["success"]:
        raise ValueError("Failed to get job instance for {0}".format(job_name))
    
    job_data = result["data"]
    if job_data["step"] == 1:
        logger.warning("{0} is not online. Please start the task first.".format(job_name))
        sys.exit(1)
    
    logger.info("Status of {0} is {1}. Restarting task...".format(job_name, job_data['status']))
    
    restart_result = make_dinky_request("restartTask", {"id": job_data["taskId"], "savePointPath": ""})
    
    if restart_result["success"]:
        logger.info("{0} restarted successfully: {1}".format(job_name, restart_result))
    else:
        logger.error("Failed to restart {0}: {1}".format(job_name, restart_result))

@error_handler
def check_job_delay(job_name, delay_seconds):
    query = '''sum(delta(flink_taskmanager_job_task_operator_currentFetchEventTimeLag{job_name="%s"}[1m])) by (cluster, job_name) /1000''' % job_name
    results = query_prometheus(query)
    
    if results['status'] != 'success':
        raise ValueError("Query failed: {0}".format(results['status']))
    
    if not results["data"]["result"]:
        logger.error("No metrics found for {0}. Restarting task...".format(job_name))
        restart_job(job_name)
        return
    
    if len(results['data']['result']) > 1:
        logger.warning("Multiple results found for {0}. Using the first one.".format(job_name))
    
    result = results['data']['result'][0]
    value = float(result['value'][1])
    
    logger.info("Cluster: {0}, Job Name: {1}, Value: {2}".format(
        result['metric'].get('cluster', 'N/A'),
        result['metric'].get('job_name', 'N/A'),
        value
    ))
    
    if value >= float(delay_seconds):
        logger.error("Delay for {0} is {1}, which exceeds the threshold of {2}".format(job_name, value, delay_seconds))
        sys.exit(1)

def main():
    if len(sys.argv) != 3:
        logger.error("Usage: python script_name.py <job_name> <delay_seconds>")
        sys.exit(1)
    
    job_name, delay_seconds = sys.argv[1], sys.argv[2]
    check_job_delay(job_name, delay_seconds)

if __name__ == "__main__":
    main()