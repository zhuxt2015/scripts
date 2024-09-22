#!/bin/bash 
set -eu
###################################################
# Usage: install_init.sh
# 功能:  集群部署入场条件检查  
###################################################

#ntp server ip
ntp_server_ip=10.101.1.151 

###################################################
# 设置字符集为en_US.UTF8
###################################################
function set_utf8()
{
    current_lang=$(echo $LANG)

    if [ "$current_lang" != "en_US.UTF-8" ]; then
        echo "Current LANG is $current_lang, not en_US.UTF-8, updating..."
    
        # 根据不同的 Linux 发行版,修改语言设置的方式可能不同
        # 以下是针对 CentOS/RHEL 7 的修改方式
        export LANG=en_US.UTF8
        sed -i 's/^LANG=.*/LANG="en_US.UTF-8"/' /etc/locale.conf
    
        echo "LANG has been updated to en_US.UTF-8"
        echo "Please restart your server for the changes to take effect."
    else
        echo "Current LANG is already en_US.UTF-8"
    fi
}

###################################################
# 安装yum源
###################################################
function install_yum()
{
    curl -o /etc/yum.repos.d/CentOS-YILI.repo http://10.251.136.11:8080/centos/repo.d/CentOS-YILI.repo
}

###################################################
# 修改系统限制参数（最大打开文件数以及最大进程数）
###################################################

function set_limits()
{
	if ! grep "^* soft nofile" /etc/security/limits.conf
	then
		echo "* soft nofile 655350" >>/etc/security/limits.conf
	fi
		
	if ! grep "^* hard nofile" /etc/security/limits.conf
	then
		echo "* hard nofile 655350" >>/etc/security/limits.conf
	fi
	if ! grep "^* hard nproc" /etc/security/limits.conf
	then
		echo "* hard nproc 65535" >>/etc/security/limits.conf
	fi
	if ! grep "^* soft nproc" /etc/security/limits.conf
	then
		echo "* soft nproc 65535" >>/etc/security/limits.conf
	fi
	if ! grep "^* soft stack" /etc/security/limits.conf
	then
		echo "* soft stack unlimited" >>/etc/security/limits.conf
	fi
	if ! grep "^* hard stack" /etc/security/limits.conf
	then
		echo "* hard stack unlimited" >>/etc/security/limits.conf
	fi
	if ! grep "^* soft memlock" /etc/security/limits.conf
	then
		echo "* soft memlock unlimited" >>/etc/security/limits.conf
	fi
	if ! grep "^* hard memlock" /etc/security/limits.conf
	then
		echo "* hard memlock unlimited" >>/etc/security/limits.conf
	fi
		
	sed -i "s/4096/65535/g" /etc/security/limits.d/20-nproc.conf
}

###################################################
# 关闭SELinux
###################################################

function off_selinux()
{
    sed -i "s/^SELINUX=.*/SELINUX=disabled/g" /etc/sysconfig/selinux
	  sed -i 's/SELINUXTYPE/#SELINUXTYPE/' /etc/selinux/config
    sed -i "s/^SELINUX=.*/SELINUX=disabled/g" /etc/selinux/config
    SELStatus=$(getenforce)
    if [ "X"${SELStatus} = "XPermissive" -o "X"${SELStatus} = "XDisabled" ] ;
    then
      echo 'succeed to close SELinux.'
    else
      setenforce 0
    fi
}


###################################################
# 禁用透明大页(THP)
###################################################

function off_THP()
{
    if test -f /sys/kernel/mm/transparent_hugepage/enabled; 
    then
        echo never > /sys/kernel/mm/transparent_hugepage/enabled
        echo 'echo never > /sys/kernel/mm/transparent_hugepage/enabled' >> /etc/rc.local

    fi
    if test -f /sys/kernel/mm/transparent_hugepage/defrag; 
    then
        echo never > /sys/kernel/mm/transparent_hugepage/defrag
        echo 'echo never > /sys/kernel/mm/transparent_hugepage/defrag' >> /etc/rc.local

    fi
}

###################################################
# 禁用交换分区(root用户)
###################################################

function off_swappiness()
{
	swapoff -a
  sysctl vm.swappiness=0
	if ! grep "vm.swappiness=" /etc/sysctl.conf
	then
		echo "vm.swappiness=0" >> /etc/sysctl.conf
	else
        sed -i "s/^vm.swappiness=.*/vm.swappiness=0/g" /etc/sysctl.conf
	fi
}

###################################################
# 网络参数
###################################################

function net_config()
{
  #如果系统当前因后台进程无法处理的新连接而溢出，则允许系统重置新连接
	if ! grep "net.ipv4.tcp_abort_on_overflow=1" /etc/sysctl.conf
	then
		echo "net.ipv4.tcp_abort_on_overflow=1" >> /etc/sysctl.conf
	fi
  #设置监听 Socket 队列的最大连接请求数为 1024
  if ! grep "net.core.somaxconn=1024" /etc/sysctl.conf
	then
		echo "net.core.somaxconn=1024" >> /etc/sysctl.conf
	fi
  #Memory Overcommit 允许操作系统将额外的内存资源分配给进程
  if ! grep "^vm.overcommit_memory" /etc/sysctl.conf
	then
		echo "vm.overcommit_memory=1" >> /etc/sysctl.conf
	fi
  #设置网卡ring buffer，避免丢包
  if ! grep 'ethtool.*rx' /etc/rc.d/rc.local;then
    for i in `cat /proc/net/bonding/bond0 |grep 'Slave Interface:' |awk '{print $3}'`; do ethtool -G $i rx $(ethtool -g $i|sed -n '3p'|awk '{print $2}');echo "/usr/sbin/ethtool -G $i rx $(ethtool -g $i|sed -n '3p'|awk '{print $2}')" >> /etc/rc.d/rc.local;done
  fi
	
}

###################################################
# 关闭packagekit
###################################################

function off_packagekit()
{
    if [ -f /etc/yum/pluginconf.d/refresh-packagekit.conf ] ;
    then
     echo 'yes'
     pkill -9 packagekitd
     sed -i 's/enabled=.*/enabled=0/g' /etc/yum/pluginconf.d/refresh-packagekit.conf
    fi
}

###################################################
# 设置umask
###################################################

function set_umask()
{
	if ! grep "umask 0022" /etc/profile
	then
    echo "umask 0022" >> /etc/profile
	fi
}

###################################################
# 配置正反向域名解析
###################################################

function set_networking()
{
	if ! grep "NETWORKING=yes" /etc/sysconfig/network
	then
        echo NETWORKING=yes >> /etc/sysconfig/network
	fi
    hostname=`hostname`
	if ! grep "HOSTNAME=${hostname}" /etc/sysconfig/network
	then
        echo HOSTNAME=$hostname >> /etc/sysconfig/network
	fi
}

###################################################
# 设置主机时间同步
###################################################

function set_ntpd()
{   
    yum install ntp -y 
    
		sed -i 's/^server 0.centos.pool.ntp.org iburst/#server 0.centos.pool.ntp.org iburst/' /etc/ntp.conf
		sed -i 's/^server 1.centos.pool.ntp.org iburst/#server 1.centos.pool.ntp.org iburst/' /etc/ntp.conf
		sed -i 's/^server 2.centos.pool.ntp.org iburst/#server 2.centos.pool.ntp.org iburst/' /etc/ntp.conf
		sed -i 's/^server 3.centos.pool.ntp.org iburst/#server 3.centos.pool.ntp.org iburst/' /etc/ntp.conf
		if ! grep "server ${ntp_server_ip} prefer" /etc/ntp.conf
		then
		    echo "server ${ntp_server_ip} prefer" >> /etc/ntp.conf
		fi
		systemctl enable ntpd
    if command -v chronyd &> /dev/null;then
      echo "chrony 已安装,执行关闭命令"
      systemctl stop chronyd
      systemctl disable chronyd
    fi
    systemctl start ntpd
    systemctl status ntpd
}

###################################################
# 关闭防火墙
###################################################

function off_firewall()
{
    systemctl stop firewalld
    systemctl disable firewalld
    systemctl status firewalld | grep inactive
}

###################################################
# 关闭Centos的tuned服务
###################################################

function off_tuned()
{
    systemctl start tuned
    tuned-adm off
    tuned-adm list|tail -n 1
    systemctl stop tuned
    systemctl disable tuned
    systemctl status tuned | grep inactive
}


###################################################
# 安装jdk
###################################################

function install_jdk()
{
    #yum install jdk
	  yum install -y java-1.8.0-openjdk.x86_64

    #set environment
    if ! grep "^export JAVA_HOME=" /etc/profile 
    then
            echo "export JAVA_HOME=/etc/alternatives/jre" | sudo tee -a /etc/profile
            echo 'export PATH=$PATH:$JAVA_HOME/bin' | sudo tee -a /etc/profile
    fi

    #update environment
    #source /etc/profile
    java -version
    echo "jdk is installed !"
}


###################################################
# 修改主机名
###################################################

function change_hostname()
{
    host_ip=`/sbin/ifconfig -a|grep -o -e 'inet [0-9]\{1,3\}.[0-9]\{1,3\}.[0-9]\{1,3\}.[0-9]\{1,3\}'|grep -v "127.0.0"|awk '{print $2}'`
    sn=`echo ${host_ip} | awk -F '.' '{print $4}'`
    hname="bjdx-yzbd-dn`expr ${sn} - 12`"
    echo $hname > /etc/hostname
    hostnamectl set-hostname $hname --static
}

###################################################
# 修改hosts
###################################################

function cp_hosts()
{
	echo '127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4
::1         localhost localhost.localdomain localhost6 localhost6.localdomain6

#外网
172.17.24.12    dd9300.localdomain
172.17.24.11    IP0991003

10.139.0.34     cp0950011.ylcmp.com
10.139.0.40     cp0950017.ylcmp.com
10.150.4.47 cdhprodcm01.yili.com
10.150.4.48 cdhprodcm02.yili.com
10.150.4.49 cdhprodcm03.yili.com
10.150.4.50 cdhprodnm01.yili.com
10.150.4.51 cdhprodnm02.yili.com
10.150.5.10 cdhproddn01.yili.com
10.150.5.11 cdhproddn02.yili.com
10.150.5.12 cdhproddn03.yili.com
10.150.5.13 cdhproddn04.yili.com
10.150.5.14 cdhproddn05.yili.com
10.150.5.15 cdhproddn06.yili.com
10.150.5.16 cdhproddn07.yili.com
10.150.5.17 cdhproddn08.yili.com
10.150.5.18 cdhproddn09.yili.com
10.150.5.19 cdhproddn10.yili.com
10.150.5.20 cdhproddn11.yili.com
10.150.5.21 cdhproddn12.yili.com
10.150.5.22 cdhproddn13.yili.com
10.150.5.23 cdhproddn14.yili.com
10.150.5.24 cdhproddn15.yili.com
10.150.5.25 cdhproddn16.yili.com
10.150.5.26 cdhproddn17.yili.com
10.150.5.27 cdhproddn18.yili.com
10.150.5.28 cdhproddn19.yili.com
10.150.5.29 cdhproddn20.yili.com
10.150.5.30 cdhproddn21.yili.com
10.150.5.31 cdhproddn22.yili.com
10.150.5.32 cdhproddn23.yili.com
10.150.5.33 cdhproddn24.yili.com
10.150.5.34 cdhproddn25.yili.com
10.150.5.35 cdhproddn26.yili.com
10.150.5.36 cdhproddn27.yili.com
10.150.5.37 cdhproddn28.yili.com
10.150.5.38 cdhproddn29.yili.com
10.150.5.39 cdhproddn30.yili.com
10.150.5.40 cdhproddn31.yili.com
10.150.5.41 cdhproddn32.yili.com
10.150.4.26 etlds1.yili.com
10.150.4.27 etlds2.yili.com
10.150.4.28 etlds3.yili.com
10.150.4.29 etlds4.yili.com
10.101.1.151    ntp.yili.com
10.150.4.25 YILIGKS01
10.150.5.42 cdhproddn33.yili.com
10.150.5.43 cdhproddn34.yili.com
10.150.5.44 cdhproddn35.yili.com
10.150.5.45 cdhproddn36.yili.com
10.150.5.46 cdhproddn37.yili.com
10.150.5.47 cdhproddn38.yili.com
10.150.5.48 cdhproddn39.yili.com
10.150.5.49 cdhproddn40.yili.com
10.150.5.50 cdhproddn41.yili.com
10.150.5.51 cdhproddn42.yili.com
10.150.5.52 cdhproddn43.yili.com
10.150.5.53 cdhproddn44.yili.com
10.150.5.54 cdhproddn45.yili.com
10.150.5.55 cdhproddn46.yili.com
10.150.5.56 cdhproddn47.yili.com
10.150.5.57 cdhproddn48.yili.com
10.150.5.58 cdhproddn49.yili.com
10.150.5.59 cdhproddn50.yili.com
10.150.5.60 cdhproddn51.yili.com
10.150.5.61 cdhproddn52.yili.com
10.150.5.62 cdhproddn53.yili.com
10.150.5.63 cdhproddn54.yili.com
10.150.5.64 cdhproddn55.yili.com
10.150.5.65 cdhproddn56.yili.com
10.150.5.66 cdhproddn57.yili.com
10.150.5.67 cdhproddn58.yili.com
10.150.5.68 cdhproddn59.yili.com
10.150.5.69 cdhproddn60.yili.com
10.150.5.70 cdhproddn61.yili.com
10.150.5.71 cdhproddn62.yili.com
10.150.5.72 cdhproddn63.yili.com
10.150.5.73 cdhproddn64.yili.com' > /etc/hosts
	
}

###################################################
#
# 入口函数
#
###################################################
function main()
{
    
    #设置字符集
    echo "begin set utf8"
    set_utf8
    if [ $? -ne 0 ]; then
        return 1
    fi
    
    #安装yum源
    echo "begin install yum repo"
    install_yum
    if [ $? -ne 0 ]; then
        return 1
    fi
    
    #修改系统限制参数
    echo "begin set limits"
    set_limits
    if [ $? -ne 0 ]; then
        return 1
    fi
    
    #关闭SELinux
    echo "begin off selinux"
    off_selinux
    if [ $? -ne 0 ]; then
        return 1
    fi
    
    #禁用透明大页
    echo "begin off THP"
    off_THP
    if [ $? -ne 0 ]; then
        return 1
    fi    

    #禁用交换分区(root用户)
    echo "begin off swap"
    off_swappiness
    if [ $? -ne 0 ]; then
        return 1
    fi
	
    #修改网络配置
    echo "begin net config"
    net_config
    if [ $? -ne 0 ]; then
        return 1
    fi
    
    #关闭packagekit
    echo "begin off packagekit"
    off_packagekit
    if [ $? -ne 0 ]; then
        return 1
    fi    
   
    #设置umask
    echo "begin set umask"
    set_umask
    if [ $? -ne 0 ]; then
        return 1
    fi    
    
    #修改主机名
    #echo "begin change hostname"
    #change_hostname
    #if [ $? -ne 0 ]; then
    #    return 1
    #fi

    #配置正反向域名解析
    echo "begin set networking"
    set_networking
    if [ $? -ne 0 ]; then
        return 1
    fi    
    
    #关闭防火墙
    echo "begin off firewall"
    off_firewall
    if [ $? -ne 0 ]; then
        return 1
    fi   
    
    #关闭Centos的tuned服务
    echo "begin off tuned"
    off_tuned
    if [ $? -ne 0 ]; then
        return 1
    fi   
		
    #安装jdk
	  echo "begin install jdk"
    install_jdk
    if [ $? -ne 0 ]; then
        return 1
    fi   
    
	
    #设置主机时间同步
    echo "begin set ntpd"
    set_ntpd
    if [ $? -ne 0 ]; then
        return 1
    fi  
	 
    #拷贝hosts文件
    echo "begin cp hosts"
    cp_hosts
    if [ $? -ne 0 ]; then
        return 1
    fi   
    
    sysctl -p
}

main

