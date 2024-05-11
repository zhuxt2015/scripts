#!/bin/bash
today=$1
current=$(date "+%Y%m%d%H%M%S")
tmp_file="/tmp/hive-staging_${current}.log"
echo "临时文件: ${tmp_file}"
sql="use storage_analyze;select p4 as path from dwd_fsimage where split(p4,'/')[3]='.staging' and partition_key='${today}' group by p4 union all select p6 as path from dwd_fsimage where split(p6,'/')[6] like '.hive-staging%'  and partition_key='${today}' group by p6 union all select p5 as path from dwd_fsimage where split(p5,'/')[5] like '.hive-staging%'  and partition_key='${today}' group by p5"
echo "hive sql: ${sql}"
hive -e "${sql}" >> ${tmp_file}
if [ $? -ne 0 ];then
  exit 1
fi
total=$(wc -l <  ${tmp_file})
echo "hive-staging总目录数: $total"
# 每次删除的目录数量
batch=100
dirs=""
count=0
deleted=0
remained=0
# 遍历test.log文件中的每个目录
while read -r dir; do
  dirs="$dirs $dir"
  # 检查是否已经删除足够的目录
  ((count++))
  if [ "$count" -ge "$batch" ]; then
    deleted=$(($deleted + $count))
    remained=$(($total - $deleted))
    echo "Deleted ${deleted} directories, remained ${remained}"
    hdfs dfs -rm -r -f $dirs
    count=0
    dirs=""
  fi
done < ${tmp_file}
if [ ! -z "$dirs" ]; then
  hdfs dfs -rm -r -f $dirs
fi

echo "Finished deleting all directories."
rm -f ${tmp_file}
