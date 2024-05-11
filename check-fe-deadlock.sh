#!/bin/bash

#config
user=root
passwd=yiliSR123!
fe_ip=10.150.4.93
http_port=8030
timeout=30
max_timeout_times=5
fe_bin_path=/opt/starrocks/fe-850651fb-cb2b-4709-aba2-f84870478a5e/bin
jstack_path=/opt/starrocks/jstack


timeout_times=0
interval=60
while true
do
    # call show proc '/statistic' to check db deadlock
    start_time=$(date +%s)
    curl -u ${user}:${passwd} http://${fe_ip}:${http_port}/api/show_proc?path=/statistic --max-time ${timeout}
    succ=$?
    end_time=$(date +%s)

    # check result, if return failed and time used is at least ${timeout}, increase timeout_times
    if [ ${succ} -ne 0 ]; then
	if [ $(($end_time - $start_time)) -ge ${timeout} ]; then
       	    timeout_times=$(($timeout_times + 1))
            # reduce interval, so that we can detect deadlock ASAP
            interval=10
            echo -e "\ntimeout, time used: $(($end_time - $start_time))"
        else
            timeout_times=0
            echo -e "\ncheck failed, time used: $(($end_time - $start_time))"
        fi
    else
        timeout_times=0
        interval=60
        echo -e "\ncheck successfully, time used: $(($end_time - $start_time))"
    fi

    # check ${timeout_times}, if ${timeout_times} >= max_timeout_times print jstack and stop fe
    # we will not start fe, Because the process is hosted by supervisor
    if [ ${timeout_times} -ge ${max_timeout_times} ]; then
        echo "successive timeout times is ${timeout_times}, print jstack and stop fe"
        
        echo "start to print jstack"
        for ((i=0; i<5; i++));
        do
            pid=`cat ${fe_bin_path}/fe.pid`
            jstack_file_name=${jstack_path}/jstack_$(date '+%Y%m%d-%H%M%S').txt
            /opt/starrocks/agent/java-se-8u322-b06/bin/jstack -l ${pid} > ${jstack_file_name}
            sleep 5
        done
    fi

    sleep ${interval}
done