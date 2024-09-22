#!/bin/bash
set -e

# 设置变量
STORAGE_PATH="/data3/storage/data"
SERVER="172.23.21.39"
server_backend_id="10029"

# 获取BE的所有storage路径
get_tablet_ids() {
  curl -s -XGET http://$SERVER:8040/varz|sed -n 's/^storage_root_path=//p'
}

# 获取所有tablet文件的路径和对应的tablet ID
get_tablet_ids() {
    ssh $SERVER "find $STORAGE_PATH -type f -name '*.dat'" | awk -F'/' '{print $(NF-2)}'|uniq
}

# 执行SQL查询获取tablet元数据
get_tablet_metadata() {
    local tablet_id=$1
    # 这里需要替换为实际的StarRocks SQL客户端命令
    mysql -uroot -p'yili@SR~2024' -P9030 -h172.23.21.44 -e "show tablet $tablet_id\G"
}

# 获取tablet的详细信息
get_tablet_details() {
    local detail_cmd=$1
    # 这里需要替换为实际的StarRocks SQL客户端命令
    mysql -uroot -p'yili@SR~2024' -P9030 -h172.23.21.44 -e "$detail_cmd" -N
}

# 计算磁盘上tablet文件的总大小
calculate_disk_size() {
    local tablet_id=$1
    ssh $SERVER "find $STORAGE_PATH -path '*/$tablet_id/*' -name '*.dat' -exec du -b {} + | awk '{total += \$1} END {print total}'"
}

# 主函数
main() {
  for 
    local tablet_info=$(get_tablet_ids)

    for tablet_id in $tablet_info; do
        local metadata=$(get_tablet_metadata $tablet_id)
        DbName=$(echo "$metadata" |sed -n 's/^.*DbName: //p')
        if [ "$DbName" = "NULL" ];then
            continue
        fi
        local detail_cmd=$(echo "$metadata" |sed -n 's/^.*DetailCmd: //p')
        local details=$(get_tablet_details "$detail_cmd")

        local disk_size=$(calculate_disk_size $tablet_id)

        echo "$details" | while  read line; do
            backend_id=$(echo $line | awk '{print $2}')
            data_size=$(echo $line | awk '{print $11}')
            if [[ $backend_id == $server_backend_id ]]; then
                data_size=$(echo $data_size | tr -d ' ')
                if [[ $disk_size != $data_size ]]; then
                    echo "Inconsistent tablet ID: $tablet_id"
                    echo "  Disk size: $disk_size"
                    echo "  Metadata size: $data_size"
                fi
                break
            fi
        done
    done
}

# 执行主函数
main