#!/bin/bash

# 从命令行参数中获取数据库名称列表
database_names=("cma_tmp" "acquisition_ods" "tmp" "sdata" "microbatch_full" "datamining_test_ds" "acquisition_ods_inc" "rtm_lake" "microbatch" "bigdata_ld" "bigdata_bak")

# 循环遍历每个数据库
for db_name in "${database_names[@]}"; do
  # 获取指定数据库中的所有表名
  tables=$(hive -S -e "use $db_name; show tables;")

  # 循环遍历每个表并清空数据
  for table in $tables; do
    echo "truncate table ${db_name}.${table}" >> /tmp/$db_name.sql
  done

  echo "All tables in database $db_name have been truncated."
done