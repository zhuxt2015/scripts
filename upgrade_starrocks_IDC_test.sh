#!/bin/bash
if [ $# != 1 ];then
  echo "USAGE: $0 2.5.18"
  exit 1
fi
version=$1
echo "升级集群到$version"
# 定义进程名称
fe_proc_name="starrocks_fe"
be_proc_name="starrocks_be"
fe_ip="10.119.14.93"
password="yiliSR123!"

base_dir=$(cd $(dirname $0); pwd)
cd $base_dir
upgrade_file="StarRocks-${version}-centos-amd64.tar.gz"
starrocks_dir="StarRocks-${version}-centos-amd64"
if [ ! -f $upgrade_file ]; then
  wget https://releases.mirrorship.cn/starrocks/${upgrade_file}
fi

be_ips=()

result=$(mysql -uroot -h$fe_ip -P9030 -p${password} -sse "show backends")
be_version=""
while read line; do
  arr=($line)

  ip=${arr[1]}
  be_version=${arr[24]}
  be_ips+=($ip)
done <<< "$result"

all_ips=$(IFS=,; echo "${be_ips[*]}")

echo "所有BE IP:$all_ips"

# 最多检测10次
max_checks=10

checks=1
proc_running=0
#升级be前，禁用 Tablet 调度功能
mysql -uroot -h$fe_ip -P9030 -p${password} -v -e 'ADMIN SET FRONTEND CONFIG ("max_balancing_tablets" = "0");admin set frontend config ("max_scheduling_tablets"="0");admin set frontend config ("disable_balance"="true");admin set frontend config ("disable_colocate_balance"="true");'
for be in ${be_ips[@]}; do
  echo "升级$be的BE, $be_version -> $version"
  if [ $be = $fe_ip ]; then
    ssh $be "echo 'decompressing file'&&tar xf ${upgrade_file} ${starrocks_dir}/be&& echo 'upgrade starting'&&source /etc/profile&&cd ~/be/ &&sudo systemctl stop starrocks-be&& rm -rf lib_* && mv lib{,_bak} && rm -rf bin_* && mv bin{,_bak}&&cp -r ~/${starrocks_dir}/be/lib .&&cp -r ~/${starrocks_dir}/be/bin .&&sudo systemctl start starrocks-be"
  else
    scp $upgrade_file ${be}:~/ && ssh $be "echo 'decompressing file'&&source /etc/profile&& tar xf ${upgrade_file} ${starrocks_dir}/be&&echo 'upgrade starting'&&cd ~/be/ &&sudo systemctl stop starrocks-be && rm -rf lib_* && mv lib{,_bak} && rm -rf bin_* && mv bin{,_bak}&&cp -r ~/${starrocks_dir}/be/lib .&&cp -r ~/${starrocks_dir}/be/bin .&&sudo systemctl start starrocks-be&& rm -rf ~/${starrocks_dir}*"
  fi
  while [ $checks -le $max_checks ]; do
    if ssh $be "sudo systemctl status starrocks-be" | grep "active (running)"; then
      proc_running=1
      break
    fi

    let checks=checks+1
    sleep 2
  done
  if [ $proc_running -eq 1 ]; then
    echo "$be 进程 $be_proc_name 已经启动"
  else
    echo "$be 进程 $be_proc_name 启动失败"
    exit 1
  fi
  proc_running=0
done
mysql -uroot -h${fe_ip} -P9030 -p$password -v -e 'ADMIN SET FRONTEND CONFIG ("max_balancing_tablets" = "500");admin set frontend config ("max_scheduling_tablets"="10000");admin set frontend config ("disable_balance"="false");admin set frontend config ("disable_colocate_balance"="false");'


#升级FE
leader_ip=
fe_ips=()
# 获取所有FE节点
result=$(mysql -uroot -h$fe_ip -P9030 -p$password -sse "show frontends")

fe_current_version=""
while read line; do
  arr=($line)

  ip=${arr[1]}
  role=${arr[7]}
  fe_current_version=${arr[15]}
  #将leader节点放到最后重启
  if [ "$role" = "LEADER" ]; then
    leader_ip=$ip
  else
    fe_ips+=($ip)
  fi

done <<< "$result"
fe_ips+=($leader_ip)

all_ips=$(IFS=,; echo "${fe_ips[*]}")

echo "所有FE IP:$all_ips"

# 最多检测10次
max_checks=10

checks=1
proc_running=0
for fe in ${fe_ips[@]}; do
  echo "升级$fe的FE, $fe_current_version -> $version"
  if [ $fe = $fe_ip ]; then
    ssh $fe "echo 'decompressing file'&&source /etc/profile&& tar xf ${upgrade_file} ${starrocks_dir}/fe&&echo 'upgrade starting'&&cd /opt/starrocks/fe/ &&sudo systemctl stop starrocks-fe&& rm -rf lib_* && mv lib{,_bak} &&rm -rf bin_* && mv bin{,_bak} && rm -rf spark-dpp_* && mv spark-dpp{,_bak}&&cp -r ~/${starrocks_dir}/fe/lib .&&cp -r ~/${starrocks_dir}/fe/bin .&& cp -r ~/${starrocks_dir}/fe/spark-dpp .&&sudo systemctl start starrocks-fe"
  else
    scp $upgrade_file $fe:~/ &&ssh $fe "echo 'decompressing file'&&source /etc/profile&& tar xf ${upgrade_file} ${starrocks_dir}/fe&&echo 'upgrade starting'&&cd /opt/starrocks/fe/ &&sudo systemctl stop starrocks-fe&& && rm -rf lib_* && mv lib{,_bak} && rm -rf bin_* &&mv bin{,_bak} && rm -rf spark-dpp_* && mv spark-dpp{,_bak}&&cp -r ~/${starrocks_dir}/fe/lib .&&cp -r ~/${starrocks_dir}/fe/bin .&& cp -r ~/${starrocks_dir}/fe/spark-dpp .&&sudo systemctl start starrocks-fe&& rm -rf ~/${starrocks_dir}*"
  fi
  
  while [ $checks -le $max_checks ]; do
    if ssh $fe "sudo systemctl status starrocks-fe" | grep "active (running)"; then
      proc_running=1
      break
    fi

    let checks=checks+1
    sleep 2
  done
  if [ $proc_running -eq 1 ]; then
    echo "$fe 进程 $fe_proc_name 已经启动"
  else
    echo "$fe 进程 $fe_proc_name 启动失败"
    exit 1
  fi
  proc_running=0
done