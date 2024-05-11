#!/bin/bash
#删除所有YARN上作务
echo `date +'%Y-%m-%d %H:%M:%S'`
appList=`yarn application -list | grep -w RUNNING | awk '{print $1}' | grep application_`

echo "Running applications: ${appList}"

for appid in ${appList}
do
    echo "Kill application ${appid}"
    yarn application -kill $appid
done