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
apk_with_html_file = list() # numero di apk con file html all'interno
apk_with_js_enabled = list()
apk_with_js_interface = list()


def analyze_start(conf, apk_to_analyze, tag, string_to_find, api_monitor_dict=None, network_dict=None):
    print("\n")
    print(bcolors.BOLD+apk_to_analyze.split("/")[-1]+bcolors.ENDC)
    if not os.path.exists("log"):
        os.makedirs("log")
    
    log_file = "log/"+apk_to_analyze.split("/")[-1]+".log"
    if not os.path.exists(log_file):

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

            type_apk = "[ANDROID NATIVE]" if not apk.is_hybird() else "[HYBRID]"
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
                
                if apk.javascript_enabled:
                    apk_with_js_enabled.append(apk_to_analyze)
                if apk.javascript_interface:
                    apk_with_js_interface.append(apk_to_analyze)

                if len(apk.html_file) > 0 or len(apk.url_loaded) > 0:
                    apk_with_html_file.append(apk_to_analyze)
            else:
                print(bcolors.FAIL + "Some error occured during decompilation." + bcolors.ENDC)
                logger.logger.error("Some error during decompilation.")

            logger.shutdown()
        except BadZipfile:
            logger.logger.error("APK corrupted")
            print(bcolors.FAIL+"APK corrupted"+bcolors.ENDC)
    else:
        print("Analysis already done see file {0}\n".format(log_file))
        return False
   
def main():
    second_start = time.time()
    parser = argparse.ArgumentParser(
            description='Inspect hybrid apk',
            usage='\n\tpython hybrid_inspector.py -f \"example.apk\" -s \"iframe\" \n\tpython -d \"dir_apk\" -t -s \"iframe\" \n ',
            epilog="Author : Davide Caputo")

    parser.add_argument('-f', '--file-name', metavar='<string>',
                            help='file name apk')
    
    parser.add_argument('-d','--dir-apk', metavar='<string>',help='directory to analyze')
    
    parser.add_argument('-t', action="store_true",help='enable tag search', default=False)
    
    parser.add_argument('-s', '--string-to-find', metavar='<string>',
                            help='String to find inside apk file', required=True)
    parser.add_argument('-o','--file-output-stat',metavar='<string>', default='all_stats_{0}.txt'.format(time.strftime("%d_%m_%Y_%H_%M")))
    
    args = parser.parse_args()

    if file_conf in os.listdir("."):

        conf = load_conf_file(file_conf)
        tag = args.t

        if args.dir_apk is not None:
            number_apk = 1
            
            if args.dir_apk[-1] != "/":
                list_apk_to_analyze = glob.glob(args.dir_apk+"/*.apk")
            else:
                list_apk_to_analyze = glob.glob(args.dir_apk+"*.apk")
            list_apk_yet_analyzed = list()
            for apk_to_analyze in list_apk_to_analyze:
                print(bcolors.BOLD+" APK: {0}".format(number_apk))
                number_apk = number_apk + 1
                scan = analyze_start(conf, apk_to_analyze,tag, args.string_to_find)
                if scan is not None and not scan: # non ho fatto analisi perchè già presente:
                    list_apk_yet_analyzed.append(apk_to_analyze)
            
            list_apk_to_analyze = list(set(list_apk_to_analyze)-set(list_apk_yet_analyzed))
            if len(list_apk_to_analyze) > 0:  
                file_stat_final = open("log/{0}".format(str(args.file_output_stat)),"w")    
                
                percentual_vuln = len(apk_vulnerable) / len(list_apk_to_analyze) 
                percentual_html_apk = len(apk_with_html_file) / len(list_apk_to_analyze) # app with at least one html page
                percentual_js_enabled = len(apk_with_js_enabled) / len(list_apk_to_analyze) # app with js enable
                percentual_js_interface = len(apk_with_js_interface) / len(list_apk_to_analyze) # app with js interface

                string_html = "Percentual app with at least one html file inside: {0}%\n".format(percentual_html_apk*100)
                string_js_enabled = "Percentual app with js enabled {0}%\n".format(percentual_js_enabled * 100)
                string_js_interface = "Percentual app with js interface {0}%\n".format(percentual_js_interface * 100)
                string_percentual_vuln = "Percentual app maybe vulnerable: {0}%, based on tot {1}.\n".format(percentual_vuln*100,len(list_apk_to_analyze))
                second_finish= time.time()
                average_time_apk = (second_finish - second_start)/len(list_apk_to_analyze)
                string_time_percentual = "Average time  single apk analyzed {0} sec\n".format(average_time_apk)

                # print on file
                file_stat_final.write("Apk analyzed: {0}\n".format(len(list_apk_to_analyze)))
                file_stat_final.write(string_html)
                file_stat_final.write(string_js_enabled)
                file_stat_final.write(string_js_interface)
                file_stat_final.write(string_percentual_vuln)
                file_stat_final.write(string_time_percentual)
                
                # print on terminal
                print()
                print()
                print(bcolors.BOLD+"-- Final Result -- \n")
                print("Apk analyzed: {0}\n".format(len(list_apk_to_analyze)))
                print(string_html)
                print(string_percentual_vuln)
                print(string_js_enabled)
                print(string_js_interface)
                print(string_time_percentual)

                if len(apk_vulnerable) > 0:
                    string_app_vulnerable = "".join(("- "+str(i).split("/")[-1]+"\n" for i in apk_vulnerable))
                    file_stat_final.write("\nThis app maybe are vulnerable:\n"+string_app_vulnerable)    
                    print("This app maybe are vulnerable:"+bcolors.ENDC)
                    print(bcolors.FAIL+string_app_vulnerable+bcolors.ENDC)
                
                file_stat_final.close()

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