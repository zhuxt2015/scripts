# -*- coding: utf-8 -*-
from multiprocessing import Process, Queue, Pool, Manager
import os, time, random, sys, subprocess, commands
from requests import Session
import base64
import datetime

username = "root"
script_path = "/root/container_cpu_mem.sh"

# ssh远程执行脚本，获取服务器container的cpu和内存信息
def get_cpu_mem(q, ip):
    # 构建远程执行命令
    command = [
        'ssh',
        ip.rstrip(),
        '"sh', 
        script_path,
        '"'
    ]
    try:
        # 使用 subprocess 执行远程命令
        cmd = ' '.join([str(x) for x in command])
        status, output = commands.getstatusoutput(cmd)
        for line in output.splitlines():
            q.put(line)
    except Exception as e:
        print("发生错误: {}".format(e))

class LoadSession(Session):
    def rebuild_auth(self, prepared_request, response):
        """
        No code here means requests will always preserve the Authorization
        header when redirected.
        """
def main(payload):
    """
    Stream load Demo with Standard Lib requests
    """
    username, password = 'ds', 'dsSR123!'
    headers={
        "Content-Type":  "text/html; charset=UTF-8",
        #"Content-Type":  "application/octet-stream",  # file upload
        "connection": "keep-alive",
        "max_filter_ratio": "0.2",
        "columns": "ip,pid,application_id,container_id,cpu,memory,dt",
        "column_separator": ',',
        "Expect": "100-continue",
    }
    database = 'ds'
    tablename = 'container_cpu_memory'
    api = 'http://10.150.3.30:8030/api/%s/%s/_stream_load' % (database, tablename)
    session = LoadSession()
    session.auth = (username, password)
    response = session.put(url=api, headers=headers, data=payload)
    #response = session.put(url=api, headers=headers, data= open("a.csv","rb")) # file upload
    print(response.json())

if __name__=='__main__':
    p = Pool(60)
    # 父进程创建Queue，并传给各个子进程：
    manager = Manager()
    q = manager.Queue()
    # 打开hosts文件
    hosts_file_path = '/root/hosts'  # 更改为您的hosts文件路径
    now=datetime.datetime.now()
    minute=now.strftime("%Y-%m-%d %H:%M:00")
    try:
        with open(hosts_file_path, 'r') as file:
            # 逐行读取文件内容
            for line in file:
                #异步启动进程执行远程命令
                #print(line.strip())
                p.apply_async(get_cpu_mem, args=(q,line,))
                #get_cpu_mem(q,line)
    except IOError as e:
        print("无法打开文件: {}".format(e))
        sys.exit(-1)
    #print 'Waiting for all subprocesses done...'
    p.close()
    p.join()
    #print q.qsize()
    if not q.empty():
        payload = ""
        suffix=",%s\n" % (minute)
        #lst = [q.get() for _ in range(q.qsize())]
        #payload = suffix.join([q.get() for _ in range(q.qsize())])
        while not q.empty():
            item = q.get()
            if item.isspace():
                continue
            payload = payload + item + "," + minute + "\n"
        #print payload
        main(payload)
