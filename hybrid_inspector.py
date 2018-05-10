#!/usr/env/bin python3
import argparse
import glob
import json
import os
import time
from MyAPK import MyAPK
from MyAPK import ThreadDecompyling
import sys
import logging
import time

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

dir_log = "log"
file_conf = "conf.json"

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def analyze_start(conf,apk_to_analyze,tag,string_to_find):
    print("\n")
    print(bcolors.BOLD+apk_to_analyze.split("/")[-1]+bcolors.ENDC)
    if not os.path.exists("log"):
        os.makedirs("log")
    log_file = "log/"+apk_to_analyze.split("/")[-1]+".log"

    file_log = open(log_file,"w")
    print(bcolors.WARNING+"[*] Searching in "+apk_to_analyze+bcolors.ENDC)
    
    file_log.write("Init Time ["+time.ctime()+"]"+"\n")
    
    apk = MyAPK(apk_to_analyze,conf,file_log)
    # thread per la decompilazione
    thread_decompilyng = ThreadDecompyling(apk)
    thread_decompilyng.start()
    type_apk = "[NATIVE]" if not apk.is_hybird() else "[HYBRID]"
    file_log.write(type_apk+"\n")
    print(bcolors.OKBLUE+type_apk+bcolors.ENDC)
    apk.find_string(string_to_find,tag)
    
    #print("\n")
    list_loading = ["\\","|","/","-"]
    n = 1
    while not thread_decompilyng.finish:
        n = n % len(list_loading)
        print(bcolors.WARNING+"["+list_loading[n]+"] Decompilyng "+bcolors.ENDC ,end="\r")
        n = n +1
        time.sleep(0.5)

    apk.find_url_in_apk()
    if apk.vulnerable_frame_confusion():
        print(bcolors.FAIL +"\nThis app might be vulnerable on attack frame confusion."+bcolors.ENDC)
        print(bcolors.FAIL +"This file are vulnerable "+ str(apk.file_vulnerable_frame_confusion)+bcolors.ENDC)
        file_log.write("\nThis app might be vulnerable on attack frame confusion.\nThis file are vulnerable "+ str(apk.file_vulnerable_frame_confusion)+"\n")
        file_log.write("End time:["+time.ctime()+"]\n")
    else:
        print(bcolors.OKGREEN+"\nThis app might be not vulnerable on attack frame confusion"+bcolors.ENDC)
        file_log.write("\nThis app might be not vulnerable on  attack frame confusion.\n")
        file_log.write("End time:["+time.ctime()+"]\n")

    file_log.close()


def main():

    parser = argparse.ArgumentParser(
            description='Apk scraping',
            usage='\n\tpython apk_scraping.py -f \"example.apk\" -s \"iframe\" \n\tpython -d \"dir_apk\" -t -s \"iframe\" \n ',
            epilog="Author : Davide Caputo")
    
    
    parser.add_argument('-f', '--file-name', metavar='<string>',
                            help='file name apk')
    
    parser.add_argument('-d','--dir-apk', metavar='<string>',help='directory to analyze')
    
    parser.add_argument('-t', action="store_true",help='enable tag search', default=False)
    
    parser.add_argument('-s', '--string-to-find', metavar='<string>',
                            help='String to find inside apk file',required=True)
    
    args = parser.parse_args()

    if file_conf in os.listdir("."):

        conf = load_conf_file(file_conf)
        tag = args.t

        if args.dir_apk is not None:
            
            if args.dir_apk[-1] != "/":
                list_apk_to_analyze = glob.glob(args.dir_apk+"/*.apk")
            else:
                list_apk_to_analyze = glob.glob(args.dir_apk+"*.apk")

            for apk_to_analyze in list_apk_to_analyze:
                analyze_start(conf, apk_to_analyze,tag, args.string_to_find)
        
        elif(args.file_name is not None):
            analyze_start(conf, args.file_name, tag, args.string_to_find)
        else:
            parser.error(bcolors.FAIL+"tool required -f file-name or -d dir-apk "+bcolors.ENDC)    
    else:
        print(bcolors.FAIL+"file "+file_conf+" not found"+bcolors.ENDC)

def load_conf_file(file_name):
    
    conf = json.load(open(file_name,"r"))
    for key, value in conf.items():
        conf[key] = [str(s) for s in value]
    return conf

if __name__=="__main__":    
    main()
    