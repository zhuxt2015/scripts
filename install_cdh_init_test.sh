#!/bin/bash 
#set -e
###################################################
# Usage: install_init.sh
# 功能:  集群部署入场条件检查  
###################################################

#ntp server ip
ntp_server_ip=10.119.14.67

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
# 修改系统限制参数（最大打开文件数以及最大进程数）
###################################################

function set_limits()
{
	if ! grep "* soft nofile 65535" /etc/security/limits.conf
	then
		echo "* soft nofile 65535" >>/etc/security/limits.conf
	fi
		
	if ! grep "* hard nofile 65535" /etc/security/limits.conf
	then
		echo "* hard nofile 65535" >>/etc/security/limits.conf
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
    SELStatus=$(setenforce 0 2>/dev/null ; getenforce)
    if [ "X"${SELStatus} = "XPermissive" -o "X"${SELStatus} = "XDisabled" ] ;
    then
     echo 'succeed to close SELinux.'
    else
     echo 'fail to close SELinux.'
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
  sysctl net.ipv4.tcp_abort_on_overflow=1
	sysctl net.core.somaxconn=1024
	if ! grep "net.ipv4.tcp_abort_on_overflow=1" /etc/sysctl.conf
	then
		echo "net.ipv4.tcp_abort_on_overflow=1" >> /etc/sysctl.conf
	fi
    if ! grep "net.core.somaxconn=1024" /etc/sysctl.conf
	then
		echo "net.core.somaxconn=1024" >> /etc/sysctl.conf
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
        echo umask 0022 >> /etc/profile
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
    systemctl disable chronyd
    systemctl start ntpd
    systemctl status ntpd
    ntpq -pn
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
	  yum install -y oracle-j2sdk1.8.x86_64

    #set environment
    if ! grep "JAVA_HOME=/usr/java/jdk1.8.0_181-cloudera" /etc/profile 
    then
            echo "export JAVA_HOME=/usr/java/jdk1.8.0_181-cloudera" | sudo tee -a /etc/profile
            echo 'export PATH=$PATH:$JAVA_HOME/bin' | sudo tee -a /etc/profile
    fi

    #update environment
    source /etc/profile
    java -version
    echo "jdk is installed !"
}

###################################################
# 替换snappy包
###################################################

function install_snappy()
{
        yum remove snappy -y
        yum install snappy* -y
        yum -y install openldap-clients nss-pam-ldapd expect
}

###################################################
# 拷贝yum文件
###################################################

function copy_yum()
{
    rm -rf /etc/yum.repos.d/*
		echo '[cm]
name = cm
baseurl = http://10.119.14.66/cm/
enabled = 1
gpgcheck = 0' > /etc/yum.repos.d/cm.repo
		
		echo '[cdh]
name = cdh
baseurl = http://10.119.14.66/cdh/
enabled = 1
gpgcheck = 0' > /etc/yum.repos.d/cdh.repo
		curl -o /etc/yum.repos.d/CentOS-YILI.repo http://10.251.136.11:8080/centos/repo.d/CentOS-YILI.repo
    yum clean all
    yum makecache
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

10.119.14.60 dstest01.yili.com
10.119.14.61 dstest02.yili.com
10.119.14.62 dstest03.yili.com
10.119.14.63 dstest04.yili.com
10.119.14.66 cdhtestcm01.yili.com
10.119.14.67 cdhtestnm01.yili.com
10.119.14.68 cdhtestnm02.yili.com
10.116.1.71 cdhtestdn01.yili.com
10.116.1.72 cdhtestdn02.yili.com
10.116.1.73 cdhtestdn03.yili.com
10.116.1.74 cdhtestdn04.yili.com
10.116.1.75 cdhtestdn05.yili.com
10.116.1.76 cdhtestdn06.yili.com
10.116.1.77 cdhtestdn07.yili.com
10.116.1.78 cdhtestdn08.yili.com
10.119.14.101 cdhtestdn09.yili.com
10.119.14.102 cdhtestdn10.yili.com
10.119.14.103 cdhtestdn11.yili.com
10.119.14.104 cdhtestdn12.yili.com' > /etc/hosts
	
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
    
    #拷贝yum文件
    echo "begin copy yum"
    copy_yum
    if [ $? -ne 0 ]; then
        return 1
    fi   
		
    #安装jdk
	  echo "begin install jdk"
    install_jdk
    if [ $? -ne 0 ]; then
        return 1
    fi   
    
    
    
    #替换snappy包
    echo "begin install snappy"
    install_snappy
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
        
}

main

