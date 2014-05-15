#! /usr/bin/env python
#coding=utf-8
#author = yang.y@sim.com
#v=20140416

import sys,os,re,subprocess,time,platform,socket

#============================================================================================
#配置在这里----------------在这里修改配置平台基板本路径和单列目录路径
#============================================================================================
#svn单列目录路径，自己配置，有多少层就写多少个，url请务必以/结束.url按单拉的顺序写好，参考如下
svn_urls = ['http://192.167.100.151:8443/svn/MT6572_JB3.MP.V1/branches/ZXL/MR_AP_BASE/alps/',\
            'http://192.167.100.151:8443/svn/MT6572_JB3.MP.V1/branches/ZXL/LA_GEN1/alps',\
            ]

#============================================================================================
#下面的代码请不要修改！！！！！！！！！！！！！！！！！！
#============================================================================================
'''
#用法：运行python checkupate.py rev，比如python checkupate.py 100
#      其中rev指的是上一次发正式版本时的svn revision。
#      如果是第一次发版本，rev填-1
#
#      生成update.log，查看更新变化，以此为依据看是否需要同步Patch。此文件是要必看的。
#      生成update.diff，修改文件和上一版本的diff差异
'''

lastverstr = r'revision="(\d+)">\r*\n<author>(.*?)<\/author>\r*\n<date>(\d.*?)Z<\/date>.*?<msg>(.*?)<\/msg>'
lastverobj = re.compile(lastverstr, re.DOTALL)
changefirestr = r'kind="file".*?>(.*?)<\/path>'
changefireobj = re.compile(changefirestr, re.DOTALL)

def getsvnlog(file_url,level = 1):
    if level == -1:
        args = ('svn log --stop-on-copy -l1 -r0:HEAD --xml %s' % (file_url)).split(' ')
    else:
        args = ('svn log -l1 --xml %s' % (file_url)).split(' ')
    proc = subprocess.Popen(args,stdout=subprocess.PIPE)
    info = proc.stdout.read()
    objs = lastverobj.findall(info)
    if objs:
        rev = int(objs[0][0])
        author  = objs[0][1]
        changedate = objs[0][2].replace('T',' ')
        commitlog = objs[0][3]
        return rev,author,changedate,commitlog
    return None

def check(rev = 1):
    global svn_urls
    svn_urls = list(reversed(svn_urls))
    sysstr = platform.system()
    chfiledict = {}#用来存储修改的文件

    #如果rev输入为-1，那就让程序帮忙查一下单拉分支创建时的svn revision
    if rev == -1:
        svninfo = getsvnlog(svn_urls[0],-1)
        if svninfo:
            rev = svninfo[0]

    #记录检查的时间和最新的SVN版本号
    svninfo = getsvnlog(svn_urls[-1])
    if svninfo:
        latestrev,author,changedate,commitlog = svninfo
        updateinfo = 'Check Time: %s\nLatest revision:%d\nCompare revision:%d\n\n' % \
                (time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())),latestrev,rev)
        check_his = updateinfo
    else:
        print 'Check Time: %s\nBase url is not right.\n\n' % \
                (time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())))
        return

    #找出各单拉分支存在的单拉文件，存到files_dict里
    overlap_dict = {}
    for loop,sub_url in enumerate(svn_urls[:-1]):
        print 'Scaning overlap files in %s' % (sub_url)
        args = ('svn ls -R %s' % (sub_url)).split(' ')
        proc = subprocess.Popen(args,stdout=subprocess.PIPE)
        info = proc.stdout.read()
        if info:
            if(sysstr == "Windows"):
                destfiles = info.split('\r\n')
            else:
                destfiles = info.split('\n')

            overlap_files = [ x for x in destfiles if (len(x) > 0 and x[-1] <> '/') ]
            overlap_dict[loop] = overlap_files

    #检测从rev开始到HEAD的修改的文件(注意检测顺序)
    for loop,url in enumerate(svn_urls):
        if loop == 0:
            continue
        print 'Scaning changed files in %s' % (url)
        bingo = False
        updateinfo += "===========================================================\n"
        updateinfo += 'Handling %s\n' % url
        updateinfo += "===========================================================\n\n"

        key1 = "/branches/%s" % (url.split('branches/')[1])
        args = ('svn log -r%d:HEAD --xml -v %s' % (rev,url)).split(' ')
        proc = subprocess.Popen(args,stdout=subprocess.PIPE)
        info = proc.stdout.read()
        for loglist in info.split('</logentry>'):
            objs = lastverobj.findall(loglist)
            if objs:
                ver,author,changedate,commitlog = objs[0]
                changefiles = changefireobj.findall(loglist)
                for chfile in changefiles:
                    chfile = chfile.replace(key1,'')
                    for index in xrange(loop):
                        if chfile in overlap_dict[index]:
                            #如果相对于下面的分支，有改动过，则记录下来
                            bingo = True
                            updateinfo += "-----------------------------------------------------------\n"
                            updateinfo += "\tFile name:  %s\n\tVersion:\t\t\tcompare ver=%d\t\t\tmodified ver=%s\n\tAuthor(base):  %s\n\tCommit time(base): %s\n\tCommit log(base): %s\n" % \
                            (chfile,rev,ver,author,changedate.replace('T',' '),commitlog)
                            updateinfo += "-----------------------------------------------------------\n\n"
                            os.system('echo Changed file: %s%s >> update.diff' % (svn_urls[loop],chfile))
                            os.system('svn diff -r%d:%d %s%s >> update.diff' % (int(ver)-1,int(ver),svn_urls[loop],chfile))
                            break#输出过的话，就不要再输出了
        if bingo:
            updateinfo = '%s\n\n' % updateinfo
        else:
            updateinfo = '%s\tNo update\n\n' % updateinfo

    outfile = open('update.log','w')
    try:
        outfile.write(updateinfo)
    finally:
        outfile.close()
    outfile = open('check_his.log','a+')
    try:
        outfile.write(check_his)
    finally:
        outfile.close()

def main():
    start = time.time()
    socket.setdefaulttimeout(120)
    try:
        rev = int(sys.argv[1])
    except:
        usuage = 'Usage: python checkupdate.py rev\nrev: interger, it\'s svn revision of last release software.\ne.g. python checkupdate.py 100\nIf first software release, python checupupdate.py -1'
        print usuage
        return
    if os.path.exists('update.diff'):
        os.remove('update.diff')
    check(rev)
    end = time.time()
    print 'Runtime = ',end-start

if __name__=="__main__":
    main()
