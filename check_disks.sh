#!/bin/bash

# 服务器列表文件
servers_file="servers.txt"

# 用户名
user="root"

unclean_partitions=()

# 检查单台服务器上的磁盘
check_disks() {
    local server=$1
    local partitions=$(ssh "$user@$server" "df|grep DATA|awk '{print \$1}'")

    for partition in $partitions; do
        fs_state=$(ssh "$user@$server" "dumpe2fs -h $partition 2>/dev/null | grep 'Filesystem state' | awk -F':         ' '{print \$3}'")
        
        if [[ "$fs_state" != "clean" ]]; then
            unclean_partitions+=("$server $partition")
        fi
    done
}

# 遍历所有服务器
for server in `cat $servers_file`;do
    echo "检查服务器 $server ..."
    check_disks "$server"
done

if [ ${#unclean_partitions[@]} -gt 0 ]; then
  content=`printf '%s\n磁盘存在故障' "${unclean_partitions[@]}"`
  echo $content
  datetime=`date +"%F %T"`
  content="磁盘故障告警"+"\n"+datetime+"\n"+content

  key="a13d8e82-6129-484b-8c97-82acd6c6ca94"
  url="https://ycsb-ct-gw.digitalyili.com/qyapi/cgi-bin/webhook/send?key=${key}"
  headers="Content-Type: application/json"
  data=$(cat <<EOF
  {
      "msgtype": "text",
      "text": {
          "content": "$content"
      }
  }
EOF
  )
  
  # 使用 curl 发送 POST 请求
  response=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$url" -H "$headers" -d "$data")
  
  # 检查 HTTP 响应码
  if [ "$response" -eq 200 ]; then
      echo "企微消息发送成功"
  else
      echo "发送失败，HTTP 响应码: $response"
      exit 1
  fi
fi