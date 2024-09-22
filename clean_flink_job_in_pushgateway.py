#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup

# Flink REST API和Pushgateway的URL

pushgateway_url = "http://10.119.10.147:31500/"

clusters = {"dev":31745,"tms":32410}

# 获取Flink所有Job的ID
def get_flink_job_ids(port):
    flink_rest_api_url = "http://10.119.10.147:%d/jobs/overview" % port
    print flink_rest_api_url
    response = requests.get(flink_rest_api_url)
    if response.status_code == 200:
        jobs = response.json().get("jobs", [])
        job_ids = ["flink-app{}".format(job["jid"]) for job in jobs]
        print job_ids
        return job_ids
    else:
        print("Failed to retrieve jobs from Flink. Status code: %s" % response.status_code)
        return []

# 解析 Pushgateway 返回的 HTML 并提取 cluster="dev" 对应的所有 Job 名
def get_pushgateway_jobs(cluster):
    print pushgateway_url
    response = requests.get(pushgateway_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        jobs = set()

        # 找到所有包含 cluster="dev" 的 <span> 标签
        for cluster_span in soup.find_all('span', class_='badge badge-info'):
            if 'cluster="%s"' % cluster in cluster_span.text:
                # 查找父元素，假设job和cluster在同一个父元素内
                parent_div = cluster_span.find_parent('div', class_='card-header')

                if parent_div:
                    # 在同一个父元素内查找包含job名的<span>标签
                    job_span = parent_div.find('span', class_='badge badge-warning')
                    if job_span:
                        # 提取 job 名，例如 'job="flink-app21ca0d29ba100915b3a0ed5a63f84d49"'
                        job_name = job_span.text.strip().split('=')[1].strip('"')
                        jobs.add(job_name)
        
        return jobs
    else:
        print("Failed to retrieve metrics from Pushgateway. Status code: %s" % response.status_code)
        return set()

# 删除Pushgateway中不存在于Flink的Job
def delete_nonexistent_jobs_from_pushgateway():
    for cluster,port in clusters.items():
        print cluster,port
        flink_job_ids = set(get_flink_job_ids(port))
        pushgateway_jobs = get_pushgateway_jobs(cluster)
        
        # 需要删除的Job
        jobs_to_delete = pushgateway_jobs - flink_job_ids
        
        for job in jobs_to_delete:
            delete_url = "{}/metrics/job/{}/cluster/{}".format(pushgateway_url, job,cluster)
            print delete_url
            response = requests.delete(delete_url)
            if response.status_code == 202:
                print "Successfully deleted job {} from Pushgateway.".format(job)
            else:
                print "Failed to delete job {} from Pushgateway. Status code: {}".format(job, response.status_code)

if __name__ == "__main__":
    delete_nonexistent_jobs_from_pushgateway()