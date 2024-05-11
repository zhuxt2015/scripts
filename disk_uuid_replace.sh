#!/bin/bash
#将虚拟盘符替换成UUID


# 临时备份
cp /etc/fstab /etc/fstab.bak


devices=$(lsblk -d -o NAME,TYPE | grep 'disk' | awk '{print $1}')

# 遍历所有磁盘设备
for device in $devices
do
  # 获取分区名
  partition=/dev/${device}1
  echo $partition
  
  # 获取分区UUID
  uuid=$(blkid -s UUID -o value ${partition})
  
  #替换
  sed -i "s|^$partition|UUID=$uuid|g" /etc/fstab

done

# 测试挂载  
mount -a  
# 备份原fstab删除
[ $? -eq 0 ] && rm -f /etc/fstab.bak || mv /etc/fstab.bak /etc/fstab

echo "fstab updated with UUID identifiers"
