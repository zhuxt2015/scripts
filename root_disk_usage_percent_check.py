#coding=utf-8
import commands
import datetime

# 检查磁盘剩余空间百分比
def check_disk_usage(path):
    cmd = "df -h|grep %s|awk '{print $5}'|tr -d '%%'" % path
    disk_usage = commands.getoutput(cmd)
    return disk_usage

# 获取磁盘使用率较高的前N个进程
def get_top_processes(n):
    cmd = "iotop -o -b|head -%s" % n
    output = commands.getoutput(cmd)
    return output

if __name__ == "__main__":
    # 检查磁盘空间
    disk_path = "/dev/mapper/centos-root"
    log_file = "/tmp/root_usage_check.log"
    percent = 50
    disk_usage = check_disk_usage(disk_path)
    info = "磁盘 %s 的剩余空间：%s" % (disk_path,disk_usage)

    # 如果使用空间大于80%，获取磁盘使用率较高的前10个进程信息
    if int(disk_usage) > percent:
        output = get_top_processes(20)
        # 将输出写入到文件
        with open(log_file, "a") as f:
            now = datetime.datetime.now()
            f.write(str(now) + "\n")
            f.write(info + "\n")
            f.write(output + "\n")