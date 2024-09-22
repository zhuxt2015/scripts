#!/bin/bash
# 扩展逻辑卷
if [ $# != 1 ];then
  echo "USAGE: $0 /dev/sdc"
  exit 1
fi
devices=$1
lv_name=vg_data
lv=/dev/vg_data/lv_data
echo " 创建新的物理卷"
sudo pvcreate $devices

echo " 将新的物理卷加入到卷组"
sudo vgextend $lv_name $devices

echo " 扩展逻辑卷到最大可用空间"
sudo lvextend -l +100%FREE $lv

echo " 扩展文件系统"
sudo resize2fs $lv

echo " 检查扩展结果"
sudo lvdisplay $lv
df -h