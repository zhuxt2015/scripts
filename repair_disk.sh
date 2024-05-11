#!/bin/bash

# 定义磁盘列表
DISKS=(/dev/sda /dev/sdb /dev/sdc /dev/sdd /dev/sde /dev/sdf /dev/sdg /dev/sdh /dev/sdi /dev/sdj /dev/sdk)  

# 遍历每个磁盘
for DISK in ${DISKS[@]}; do
  
  # 调用gdisk打印分区警告信息 
  echo "Checking $DISK partition table..."
  # 调用 sgdisk 检查磁盘
  sgdisk_output=$(sgdisk -v $DISK)
  if [[ $? -ne 0 && $? -ne 2 ]];then
     exit 1
  fi

  if [[ ! $sgdisk_output =~ "No problems found." ]]; then

    echo "Errors detected on $DISK:"
    echo "$sgdisk_output"

  # sgdisk 检测到问题,修复
    gdisk $DISK <<EOF 
1
Y 
w
Y
EOF
  else
    echo "No issues found on $DISK"
  fi 

done

# 提示重启使修复生效  
echo "GPT repaired successfully, please reboot to apply changes"
