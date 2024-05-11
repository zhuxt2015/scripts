#!/bin/bash

echo "安装xfsdump"
yum install -y xfsdump
echo "备份/home 挂载点内容"
xfsdump -L home -M home -f /home.xfsdump /home

echo "卸载/home 挂载点"
umount /home

echo "将/dev/mapper/centos-home设置为50G"
lvreduce -y -L 50G /dev/mapper/centos-home

echo "将剩余空间赋予/dev/mapper/centos-root"
lvextend -l +100%FREE /dev/mapper/centos-root

echo "执行扩容生效"
xfs_growfs /dev/mapper/centos-root

echo "格式化 /home 挂载点对应的逻辑卷"
mkfs.xfs -f /dev/mapper/centos-home

echo "重新挂载 /home"
mount /home

echo "恢复备份内容到 /home 挂载点"
xfsrestore -f /home.xfsdump /home

df -h
