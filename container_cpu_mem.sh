#!/bin/bash
#统计container进程cpu和内存使用情况
container_pids=`/usr/java/jdk1.8.0_181-cloudera/bin/jps -v |grep -v 'process information unavailable'|grep application_`
if [ -z "$container_pids" ];then
  exit 0
fi
#获取本机ip
ip=`ifconfig -a|grep inet|grep -v 127.0.0.1|grep -v inet6|awk '{print $2}'|grep 10.|head -1`
while read line
do
  pid=`echo $line | awk '{print $1}'`
  if [ -z "$pid" ];then
    continue
  fi
  top=`top -p $pid -b -n2 -d0.01 | awk -v pidVar="$pid" '$1==pidVar{i++}i==2'`
  if [ -z "$top" ];then
    continue
  fi
  #echo $line
  application_pattern="application_[0-9]+_[0-9]+"
  container_pattern="container_[0-9]+_[0-9]+_[0-9]+_[0-9]+"
  app_id=`grep -oP "$application_pattern" <<< "$line"|head -1`
  container_id=`grep -oP "$container_pattern" <<< "$line"|head -1`
  cpu=`echo $top|awk '{print $9}'`
  mem=`echo $top|awk '{print $6}'`
  if [[ $mem =~ 'g' ]];then
    mem=${mem%g*}
    mem=`echo "$mem*1024"|bc`
  else
    mem=$(echo "scale=1; $mem/1024"|bc)
  fi
  if [ -z $mem ];then
    mem=0.0
  fi
  echo "$ip,$pid,$app_id,$container_id,$cpu,$mem"
done <<< "$container_pids"
