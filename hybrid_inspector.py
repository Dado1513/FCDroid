#!/usr/env/bin python3
import argparse
import glob
import json
from zipfile import BadZipfile
import os
from MyAPK import MyAPK
from ThreadDecompyling import ThreadDecompyling
import time
from bcolors import bcolors
from Logger import Logger
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

dir_log = "log"
file_conf = "conf.json"
apk_vulnerable = list()

def analyze_start(conf, apk_to_analyze, tag, string_to_find, api_monitor_dict=None, network_dict=None):
    print("\n")
    print(bcolors.BOLD+apk_to_analyze.split("/")[-1]+bcolors.ENDC)
    if not os.path.exists("log"):
        os.makedirs("log")
    
    log_file = "log/"+apk_to_analyze.split("/")[-1]+".log"
    logger = Logger(log_file)
    # file_log = open(log_file,"w")
    print(bcolors.WARNING+"[*] Searching in "+apk_to_analyze+bcolors.ENDC)
    logger.logger.info("Init Time ["+time.ctime()+"]")
    try:
        apk = MyAPK(apk_to_analyze, conf, log_file, tag, string_to_find, logger, \
                    api_monitor_dict=api_monitor_dict, network_dict=network_dict) # dict che arrivano dall'analisi dinamica
    
        # thread per la decompilazione
        thread_decompilyng = ThreadDecompyling(apk,logger)
        # TODO gestire keyboard interrupt
        thread_decompilyng.start()

        type_apk = "[NATIVE]" if not apk.is_hybird() else "[HYBRID]"
        logger.logger.info("TYPE APK: "+type_apk+"\n")
        print(bcolors.OKBLUE+type_apk+bcolors.ENDC)
        apk.find_string(apk.html_file)
        
        # print("\n")
        list_loading = ["\\","|","/","-"]
        n = 1
        while not thread_decompilyng.finish:
            n = n % len(list_loading)
            print(bcolors.WARNING+"["+list_loading[n]+"] Analysis "+bcolors.ENDC, end="\r")
            n = n +1
            time.sleep(0.5)

        if not thread_decompilyng.error:
            apk.find_url_in_apk()
            if apk.vulnerable_frame_confusion():
                print(bcolors.FAIL + "\nThis app might be vulnerable on attack frame confusion." +bcolors.ENDC)
                apk_vulnerable.append(apk_to_analyze)
                print(bcolors.FAIL + "This file are vulnerable " + str(apk.file_vulnerable_frame_confusion)+bcolors.ENDC)
                logger.logger.info("This app might be vulnerable on attack frame confusion, This file are vulnerable %s", str(apk.file_vulnerable_frame_confusion))
                logger.logger.info("End time:[%s]",time.ctime())
            else:
                print(bcolors.OKGREEN+"\nThis app might be not vulnerable on attack frame confusion"+bcolors.ENDC)
                logger.logger.info("This app might be not vulnerable on  attack frame confusion.")
                logger.logger.info("End time:["+str(time.ctime())+"]")
        else:
            print(bcolors.FAIL + "Some error occured during decompilation." + bcolors.ENDC)
            logger.logger.error("Some error during decompilation.")

        logger.shutdown()
    except BadZipfile:
        logger.logger.error("APK corrupted")
        print(bcolors.FAIL+"APK corrupted"+bcolors.ENDC)
    
    if len(apk_vulnerable) > 0:
        print(bcolors.FAIL+"This app maybe are vulnerable: "+str(apk_vulnerable)+bcolors.ENDC)

def main():
    parser = argparse.ArgumentParser(
            description='Insepct hybrid apk',
            usage='\n\tpython hybrid_inspector.py -f \"example.apk\" -s \"iframe\" \n\tpython -d \"dir_apk\" -t -s \"iframe\" \n ',
            epilog="Author : Davide Caputo")

    parser.add_argument('-f', '--file-name', metavar='<string>',
                            help='file name apk')
    
    parser.add_argument('-d','--dir-apk', metavar='<string>',help='directory to analyze')
    
    parser.add_argument('-t', action="store_true",help='enable tag search', default=False)
    
    parser.add_argument('-s', '--string-to-find', metavar='<string>',
                            help='String to find inside apk file', required=True)
    
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
        
        elif args.file_name is not None:
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


if __name__ == "__main__":
    main()