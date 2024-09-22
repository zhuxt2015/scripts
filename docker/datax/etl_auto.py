#!/usr/bin/env python
# -*- coding: utf-8 -*-
################################################
# Author: zhuxuetong
# Created Time: 2022-04-08 11:57:28
################################################
#===============================================
import argparse
import os
import subprocess
import time
import sys
import logging
###################################
parser = argparse.ArgumentParser(description='execute datax job')
parser.add_argument('-d','--database', type=str, default = '')
parser.add_argument('-st','--source_table', type=str, default = '')
parser.add_argument('-tt','--target_table', type=str, default = '')
parser.add_argument('-td','--target_project', type=str, default = '')
parser.add_argument('-sp','--source_partition',type=str, default='')
parser.add_argument('-tp','--target_partition',type=str, default='')
parser.add_argument('-t','--file_type', type=str, default='')
parser.add_argument('-m','--memory', type=int, default=1)
parser.add_argument('-cy','--sync_cycle', type=str, default='')
parser.add_argument('-n','--columnNum', type=int, default=0)
parser.add_argument('-b','--bizdate', type=str, default='')
parser.add_argument('-path','--json_path', type=str, default='')
parser.add_argument('-f','--force', action='store_true', default=False)
args = parser.parse_args()
database=args.database
sourceTable=args.source_table
targetTable=args.target_table
targetProject=args.target_project
targetColumnNum=args.columnNum
memory=args.memory
json_path=args.json_path
home=os.path.split(os.path.realpath(__file__))[0]
jarPath=home+'/datax_json_generator-1.0.jar'
#生成json模板
execute = "java -jar {} -d {} -st {} -tt {}".format(jarPath,database,sourceTable,targetTable)
if targetProject:
    execute = execute + ' -td {}'.format(targetProject)
else:
    targetProject='datagrid_ods'
if targetColumnNum:
    execute = execute + ' -c {}'.format(targetColumnNum)
if args.force:
    execute = execute + ' -force'
if len(json_path) > 0:
    execute = execute + ' -path {}'.format(json_path)
else:
    json_path=home
print execute
p=subprocess.Popen(execute, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
for line in iter(p.stdout.readline, b''):
    print line
p.stdout.close()
p.wait()

sourcePartition=args.source_partition
if sourcePartition:
   sourcePartition = "*=" + sourcePartition + "/*"
else:
   sourcePartition = "*"
targetPartition=args.target_partition
if targetPartition:
    if len(targetPartition) == 12:
        partition='ds=' + targetPartition[0:8] + ',hh=' +  targetPartition[8:10] + ',mm=' + targetPartition[10:12]
    elif len(targetPartition) == 10:
        partition='ds=' + targetPartition[0:8] + ',hh=' +  targetPartition[8:10]
    elif len(targetPartition) <= 8:
        partition='ds=' + targetPartition
else:
    partition=''
threads=memory
if threads > 8:
    threads=8
if threads <= 1:
    threads=2
jobFile=database + '_' + sourceTable + '_' + targetTable + '.json'
script=("python %s/../bin/datax.py --jvm='-Xms%sG -Xmx%sG -XX:ParallelGCThreads=%s -XX:CICompilerCount=%s' -p '-Ddatabase=%s -Dsource_table=%s -Dtarget_table=%s -Dsource_partition=%s -Dtarget_partition=%s -Dfile_type=%s' %s/%s" %(home, memory, memory, threads, threads, args.database, args.source_table, args.target_table,sourcePartition, partition, args.file_type, json_path, jobFile))
print script
records=0
noFile=0
startTime=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
try:
    p=subprocess.Popen(script, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
except Exception:
    logging.exception("执行datax脚本报错", exc_info = True)
    os._exit(-1)
for line in iter(p.stdout.readline, b''):
    print line
    if "读出记录总数" in line:
        records=line.split(":")[1].strip()
    if "您尝试读取的文件目录为空" in line:
        noFile=1
p.stdout.close()
result=p.wait()
if result != 0 and noFile == 0:
    os._exit(-1)
endTime=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
#插入日志表
log_script=("python %s/insert_odps.py -s=%s -t=%s -p=%s -c=%s -b=%s -cnt=%s -td=%s" %(home, sourceTable, targetTable, targetPartition, args.sync_cycle, args.bizdate, records, targetProject))
print log_script
try:
    p=subprocess.Popen(log_script, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
except Exception:
    logging.exception("插入odps日志表log_lake_push_data_info报错", exc_info = True)
    os._exit(-1)
for line in iter(p.stdout.readline, b''):
    print line
p.stdout.close()
result=p.wait()

if result == 0 or noFile == 1:
    sys.exit(0)
else:
    print "datax job failed!"
    sys.exit(0)
