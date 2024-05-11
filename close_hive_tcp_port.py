#!/usr/bin/env python
# -*- coding: utf-8 -*- 

import commands
import os
import sys

ip = sys.argv[1]
port = 10000

# 用netstat查找连接,过滤出指定ip和端口
cmd = "netstat -anp | grep %s |grep java|head -1" % port
print cmd
status, output = commands.getstatusoutput(cmd)

# 从netstat输出中提取连接的PID  
parts = output.split()
pid = parts[6].split('/')[0]
if not pid[0].isdigit():
   os.exit(-1) 

print "PID=%s" % pid

# 用lsof确定文件描述符号
cmd = "lsof -p %s" % pid
print cmd
status, output = commands.getstatusoutput(cmd)

for line in output.splitlines():
    if ip in line:
        parts = line.split()
        fd = parts[3].split('u')[0]
        print "FD=%s" % fd
        cmd = "echo 'call close(%s)' >> /tmp/close.gdb" % fd
        print cmd
        commands.getstatusoutput(cmd)
cmd = "echo -e 'detach\nquit' >> /tmp/close.gdb"
commands.getstatusoutput(cmd)
# 用gdb调用close系统调用关闭文件描述符
cmd = "gdb -batch -p %s -x /tmp/close.gdb" % pid
print cmd
status, output = commands.getstatusoutput(cmd)
cmd = "rm -f /tmp/close.gdb"
print cmd
commands.getstatusoutput(cmd)

print "%s connection closed" % ip