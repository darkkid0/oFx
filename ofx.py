# coding: utf-8

import os
import sys
import argparse
import logging 
import time
import threading
import queue
import configparser
import requests

try:
    os.path.dirname(os.path.realpath(__file__))
except Exception:
    err_msg = "your system does not properly handdle non-Ascii path"
    err_msg += "please move this ofx's directory to other location"
    exit(err_msg)

root_path = os.path.dirname(os.path.realpath(__file__))


sys.path.append(root_path)#os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from lib.htmloutput import output_html
from lib.common import get_title
from lib.fofa import fofa_login,ukey_save,get_ukey,fofa_search

author = "jijue"
version = "2.1.3"

logo = """
                .-'''-.                          
            '   _    \                        
            /   /` '.   \                       
            .   |     \  '  _.._                 
            |   '      |  .' .._|                
            \    \     / /| '  ____     _____    
            `.   ` ..' __| |_`.   \  .'    /    
                '-...-'|__   __|`.  `'    .'     
                        | |     '.    .'       
                        | |     .'     `.      
                        | |   .'  .'`.   `.    
                        | | .'   /    `.   `.  
                        |_|'----'       '----' 
    #################################################
    * & @ !         author : %s             * * 耶**
    -+_+__==_     version : %s       --__--__
    #################################################
"""%(author,version)



print "\033[1;30;43m"
print logo
# 启动，路径检查
output_path = root_path+"/output/"
if not os.path.exists(output_path):
    os.makedirs(output_path)
log_path = root_path+"/log/"
if not os.path.exists(log_path):
    os.makedirs(log_path)

lock=threading.Lock()



######
# 下面代码不要动
######
now=str(int(time.time()))
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s: %(message)s")


# 使用FileHandler输出到文件
fh = logging.FileHandler("%s.log" % (root_path + "/log/" + now))
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)

# 使用StreamHandler输出到屏幕
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)

# 添加两个Handler
logger.addHandler(ch)
logger.addHandler(fh)

def loglogo(message):
    print "\033[1;30;43m"
    logger.info(message)

def logvuln(message):
    print "\033[1;32;40m" # 黑底绿字
    logger.info(message)

def logunvuln(message):
    print "\033[1;34;40m" # 黑底蓝字
    logger.info(message)

def logverifyerror(message):
    print "\033[1;36;40m" # 黑底青字
    logger.info(message)

def logwarning(message):
    print "\033[1;37;41m"
    logger.warning(message)

def logcritical(message):
    print "\033[1;31;40m"
    logger.critical(message)

######
# 上面代码不要动
######

def get_module():
    return os.path.dirname(os.path.realpath(__file__))

def check_environment():
    
    PYVERSION = sys.version.split()[0]

    if PYVERSION.split(".")[0] != "2":
        err_msg = "incompatible Python version detected ('%s'). To successfully run sqlmap you'll have to use version 2.x"%(PYVERSION)
        logcritical(err_msg)
        exit()
    



vulnoutput=list()
unvulnoutput=[]
unreachoutput=[]
vulnn=0
target_list=[]

def run(scan_func,target,proxy=False,output=True):
    """
    调用扫描插件对url进行检测  
    直接打印到控制台和记录到日志中  

    Use: 
    run(verify,"121.121.121.121:9001","127.0.0.1:8080")

    Return:
    None
    """
    global vulnoutput,unvulnoutput,unreachoutput,vulnn
    while not target.empty():

        try:
            target_url = target.get()
            vuln = scan_func(target_url,proxy)
            if vuln[0] == True:
                # print vuln[1]
                vulntitle=get_title(vuln[1])
                lock.acquire()
                vulnn+=1
                logvuln("[+ %d +]存在漏洞 %s 网站Title：%s "%(target.qsize(),target_url,vulntitle))
                vulnoutput.append(target_url+" || 网站Title： "+vulntitle)
                lock.release()
            else:
                lock.acquire()
                logunvuln("[_ %d _]不存在漏洞 %s "%(target.qsize(),target_url))
                unvulnoutput.append(target_url)
                lock.release()
                
        except Exception as e:
            lock.acquire()
            logverifyerror("[! %d !]目标不可达 %s 错误详情：%s "%(target.qsize(),target,str(e)))
            unreachoutput.append(target_url+" || 错误详情"+str(e))
            lock.release()



def main():
    check_environment()
    parser = argparse.ArgumentParser(description="ofx v2.0.2",
    usage="python ofx.py -f scan.txt -s poc/jellyfin/jellyfin_fileread_scan/poc.py ")

    searchengine = parser.add_argument_group("SearchEngine")
    searchengine.add_argument("--fofa-search",type=str,help="fofa搜索语句")
    searchengine.add_argument("--fofa-output",type=str,help="fofa搜索结果保存，默认scan目录，改不了")

    # target = parser.add_argument_group("TARGET")
    target = parser.add_mutually_exclusive_group()
    target.add_argument("-u","--url",type=str,help="scan a single target url (e.g. www.baidu.com)")
    target.add_argument("-f","--file",type=str,help="load target from file (e.g. /root/urllist.txt)")

    script = parser.add_argument_group("Script")
    script.add_argument("-s","--script",type=str,help="load script by name (e.g. -s poc/jellyfin/jellyfin_fileread_scan/poc.py)")
    
    system = parser.add_argument_group("System")
    system.add_argument("--thread",default=10,type=int,help="线程数，默认10")
    system.add_argument("--proxy",default=False,help="http代理，例：127.0.0.1:8080")
    system.add_argument("--output",default=True,help="扫描报告，默认以当前时间戳命名，目前只有html格式")
    if len(sys.argv) == 1:
        sys.argv.append("-h")
    args=parser.parse_args()

    if args.url or args.file:
        # 扫描模式校验
        if args.url:
            scan_mode=1
        elif args.file:
            scan_mode=2
        else:
            print "请输入检测目标"
            exit()


        # 插件校验
        args.script = args.script[:-6] if args.script.endswith("poc.py") else args.script
        if os.path.exists(root_path+"/"+args.script):
            sys.path.append(str(root_path+"/"+args.script))
            from poc import verify,_info
            print "POC - %s 加载完毕"%(_info["name"])

        else:
            print "脚本文件不存在，请确认后重新指定"
            exit()

        # 该模式用于检验POC插件本身的可用性  
        if scan_mode == 1:
            # 扫描
            # print args.url
            if verify(args.url,args.proxy):
                print "URL: %s  || POC: %s 漏洞存在"%(args.url,args.script)
            else:
                print "URL: %s  || POC: %s 漏洞不存在"%(args.url,args.script)

        # 批量检测模式
        elif scan_mode == 2:
            start_time = time.time()
            with open(args.file,"r") as f:
                target_list = [i.strip() for i in f.readlines()]
            qu = queue.Queue()
            for i in target_list:
                qu.put(i) 
            # run(verify,qu)
            for i in range(args.thread):
                t=threading.Thread(target=run,args=(verify,qu,))
                t.start()
            t.join()

            time.sleep(_info["timeout"]+0.1)
            if args.output != False:
                html_output = now+".html" if args.output == True else args.output+".html"
                # args.output = args.output+".html"
                output_html(html_output,vulnoutput,unvulnoutput,unreachoutput)
                loglogo("报告已输出至：%s"%(html_output))

                # print vulnoutput
                txt_output = now + ".txt" if args.output == True else args.output+".txt"
                with open(root_path+"/output/"+txt_output,"w") as f:
                    for i in vulnoutput:
                        f.write(i.split("||")[0].strip()+"\n")
                loglogo("报告已输出至：%s"%(txt_output))
            
            loglogo("共计url %d 条， %d 条存在漏洞"%(len(target_list),vulnn))
            end_time = time.time()
            loglogo("本次扫描耗时:  %d秒"%(end_time-start_time))


    if args.fofa_search:
        # 检查并获取user和key的配置
        fofa_user,fofa_key = get_ukey(root_path+"/lib/fofa.ini")

        # 登陆校验
        FofaLogin = fofa_login(fofa_user,fofa_key)
        if FofaLogin[0]:
            log_msg = "User : {user} | Key : {key}".format(user = FofaLogin[1],key = FofaLogin[2])
            log_msg += " | 登陆成功"
            logvuln(log_msg)
            ukey_save(FofaLogin[1],FofaLogin[2],root_path+"/lib/fofa.ini")
        # 无或登陆失败，raw_input函数获取用户输入，
            # 再次登陆校验，循环
        # 登陆成功，
            fofa_save_path = root_path + "/scan/" + raw_input("请输入结果保存文件名(不必加文件后缀)： ") + ".txt"
            FofaDork = args.fofa_search#.replace("_"," ")
            loglogo("Fofa搜索语句为：{fofadork}，开始与Fofa Api对接".format(fofadork = FofaDork))
            FofaResultNum = fofa_search(FofaLogin[1],FofaLogin[2],FofaDork,fofa_save_path)
            if type(FofaResultNum) == int:
                log_msg = "搜索完毕，结果保存至{path}，共计{FofaResultNum}条".format(path = fofa_save_path,FofaResultNum = FofaResultNum)
                logvuln(log_msg)
            # 获取搜索结果并保存到scan
        pass

    
if __name__ == "__main__":
    main()