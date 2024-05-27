# coding:utf-8
# __auth__ = "zhuxt"
# __date__ = "2024/05/01"
import os
import requests
from bs4 import BeautifulSoup
import datetime
import os
# url = input("请输入url：")
url='https://mp.weixin.qq.com/s/NJgtgj2O1y9F9fEjSDN-mw'
curr_time = datetime.datetime.now()#获取系统时间
print(curr_time)#打印时间 测试用
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Cookie': 'pac_uid=0_e1488582cb214; iip=0; _qimei_uuid42=183130b0c2b1001829fba2c8498aaca3ac788fd065; _qimei_fingerprint=b924564895d5ee9987163312af2d389c; _qimei_q36=; _qimei_h38=0403eaa629fba2c8498aaca303000003b18313; rewardsn=; wxtokenkey=777'
}
path = "/Users/zhuxt/Downloads/" + datetime.datetime.strftime(curr_time, '%Y-%m-%d_%H_%M') + "/"#将时间格式化为字符生成时间戳到时候给文件夹命名用
print(path)
if os.path.exists(path):#检查是否存在这个文件夹
    print(u"属于这个时间点的文件夹已经创建好")
else:
    os.mkdir(path)#不存在则创建
    print(u"创建成功！！！！正在保存图片")
req = requests.get(url=url, headers=headers).content#向刚才输入的公众号链接里面发送请求
soup = BeautifulSoup(req, 'lxml')#用BeautifulSoup解析网页
res = soup.select('img')#获取该网页中所有的图片标签
a = 0
for i in res:#遍历所有的图片标签
    if i.get("data-src") == None:#如果这个标签内的data-src等于空的时候直接跳过
        pass
    else:#否则获取data-src里面的内容获取图片链接
        print(u'链接：%s类型为：%s' % (i.get("data-src"),i.get("data-type")))
        try:#尝试去保存图片 如果保存图片错误则抛出异常
            picture_path = path + '%s.%s' % (a,i.get("data-type"))
            with open(picture_path, 'wb') as f:#拼接路径+a.jpg a是等于数字 每添加一个 a自增一 相当于是给图片命名 并且以二进制的形式写入
                f.write(requests.get(url=i.get("data-src"), headers=headers).content)#向这个图片发送请求 并将图片的二进制写入
                a = a + 1#a自增一
        except Exception as e:#抛出异常 增加程序强壮性
            print(u"该链接为空自动跳过！")
print(u"此次一共成功保存图片%s张" % (a))
