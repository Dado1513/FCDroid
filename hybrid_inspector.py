#!/usr/env/bin python3
import argparse
import glob
import json
import subprocess
from zipfile import BadZipfile
import os
from MyAPK import MyAPK
from ThreadDecompyling import ThreadDecompyling
import time
from bcolors import bcolors
from Logger import Logger
from mongo_utils import MongoDB
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

dir_log = "log"
file_conf = "conf.json"
apk_vulnerable = list()
apk_maybe_vulnerable = list()
apk_with_html_file = list() # numero di apk con file html all'interno
apk_with_js_enabled = list()
apk_with_js_interface = list()
apk_with_library_vulnerable = list()
apk_with_xss = list()
apk_that_use_http = list()
apk_that_use_http_loadUrl = list()


def analyze_start(conf, apk_to_analyze, tag, string_to_find, api_monitor_dict=None, network_dict=None):
    print(bcolors.BOLD+apk_to_analyze.split("/")[-1]+bcolors.ENDC)
    if not os.path.exists("log"):
        os.makedirs("log")
    
    log_file = "log/"+apk_to_analyze.split("/")[-1]+".log"
    #if not os.path.exists(log_file):

    logger = Logger(log_file)
    # file_log = open(log_file,"w")
    print(bcolors.WARNING+"[*] Searching in "+apk_to_analyze+bcolors.ENDC)
    logger.logger.info("Init Time ["+time.ctime()+"]")
    try:
        apk = MyAPK(apk_to_analyze, conf, log_file, tag, string_to_find, logger, \
                    api_monitor_dict=api_monitor_dict, network_dict=network_dict,use_smaliparser=True) # dict che arrivano dall'analisi dinamica
        
        mongo = MongoDB(logger)
        result = None
        if mongo.is_available: # connection available
            result = mongo.find_analysis(apk.name_only_apk)
        if result is None:

            ################################################################################
            type_apk = "[ANDROID NATIVE]" if not apk.is_hybird() else "[HYBRID]"
            logger.logger.info("TYPE APK: "+type_apk)
            print(bcolors.OKBLUE+type_apk+bcolors.ENDC)

            #################################################################################
            # thread per la decompilazione
            thread_decompilyng = ThreadDecompyling(apk,logger)
            # TODO gestire keyboard interrupt
            thread_decompilyng.start() # wait apktool output che arriva dall'istruzione sopra 

            #################################################################################
            logger.logger.info("\nStart HTML file")
            apk.find_string(apk.html_file)
            logger.logger.info("End HTML file \n")

            #################################################################################
            logger.logger.info("Start JavaScript file")
            apk.find_string(apk.javascript_file) 
            logger.logger.info("End JavaScript file \n")
            #################################################################################
            
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
                apk.vulnerable_frame_confusion()
                if apk.is_vulnerable_frame_confusion:
                    # TODO se file vulnerable == file_js_with_iframe modificare i controlli
                    apk_vulnerable.append(apk_to_analyze)
                    if not apk.file_vulnerable_frame_confusion == apk.file_js_with_iframe:
                        print(bcolors.FAIL + "\nThis app might be vulnerable on attack frame confusion." +bcolors.ENDC)
                        print(bcolors.FAIL + "This file are vulnerable " + str(apk.file_vulnerable_frame_confusion)+bcolors.ENDC)
                        logger.logger.info("This app might be vulnerable on attack frame confusion, This file are vulnerable %s", str(apk.file_vulnerable_frame_confusion))
                    else:
                        print(bcolors.WARNING + "\nThis app might be vulnerable on attack frame confusion (found string iframe inside js file)." +bcolors.ENDC)

                    if len(apk.file_js_with_iframe) > 0:
                        apk_maybe_vulnerable.append(apk_to_analyze)
                        print()
                        print(bcolors.WARNING+ "This file are suspect, contain iframe string inside:{0} ".format(apk.file_js_with_iframe)+ bcolors.ENDC)
                        logger.logger.info("This file are suspects, containe string iframe inside: {0}".format(apk.file_js_with_iframe))
                    print()
                    logger.logger.info("End time:[%s]",time.ctime())
                
                elif len(apk.file_js_with_iframe) == 0:
                    print(bcolors.OKGREEN+"\nThis app might be not vulnerable on attack iframe confusion"+bcolors.ENDC)
                    logger.logger.info("This app might be not vulnerable on  attack frame confusion.")
                    logger.logger.info("End time:["+str(time.ctime())+"]")
                
                else:
                    print(bcolors.WARNING+"\nThis app might be vulnerabile (found string iframe), in this file: "+str(apk.file_js_with_iframe) + bcolors.ENDC)
                    logger.logger.info("This app might be vulnerabile (found string iframe), in this file {0}".format(apk.file_js_with_iframe))
                    apk_maybe_vulnerable.append(apk_to_analyze)
                    
                if apk.javascript_enabled:
                    apk_with_js_enabled.append(apk_to_analyze)
                if apk.javascript_interface:
                    apk_with_js_interface.append(apk_to_analyze)

                if len(apk.html_file) > 0 or len(apk.url_loaded) > 0:
                    apk_with_html_file.append(apk_to_analyze)
            else:
                print(bcolors.FAIL + "Some error occured during decompilation." + bcolors.ENDC)
                logger.logger.error("Some error during decompilation.")

            apktool_retire,remote_retire = scan_retire(apk)
            
            logger.logger.info("Number of http connection {0}".format(apk.http_connection))
            if apk.http_connection > 0:
                apk_that_use_http.append(apk_to_analyze)
            
            logger.logger.info("Number of http connection inside loadUrl {0}".format(apk.http_connection_static))
            if apk.http_connection_static > 0:
                apk_that_use_http_loadUrl.append(apk_to_analyze)

            logger.logger.info("Number of all http url inside apk {0}".format(apk.all_http_connection))

            # logger.logger.info("RetireJS {0} {1}".format(apktool_retire, remote_retire))
            
            if apktool_retire != None or remote_retire != None:
                logger.logger.info("RetireJS: {0} , {1} ".format(apktool_retire, remote_retire))
                apk_with_library_vulnerable.append(apk_to_analyze)
            
            file_xss = list(apk.page_xss_vuln.keys())
            if len(file_xss) > 0:
                apk_with_xss.append(apk_to_analyze)
                logger.logger.info("File that use function js vulnerable at xss {0}".format(file_xss))  
            
            if mongo.is_available:
                mongo.insert_analysis(apk,apktool_retire,remote_retire,file_xss,logger)
            logger.shutdown()

        else:
            logger.logger.info("Analysis yet done")
            if len(result["file_js_with_iframe"]) > 0:
                apk_maybe_vulnerable.append(apk_to_analyze)
            if result["frame_confusion_vulnerable"]:
                apk_vulnerable.append(apk_to_analyze)
            if result["js_enable"]:
                apk_with_js_enabled.append(apk_to_analyze)
            if result["js_interface"]:
                apk_with_js_interface.append(apk_to_analyze)
            if len(result["html_file"]) > 0 or len(result["url_loaded"]) > 0:
                apk_with_html_file.append(apk)
            
            return True
            

    except BadZipfile:
        logger.logger.error("APK corrupted")
        print(bcolors.FAIL+"APK corrupted"+bcolors.ENDC)

 
    
def main():
    second_start = time.time()
    parser = argparse.ArgumentParser(
            description='Inspect hybrid apk \nAnalyze xss, use lib js with vulnerability and check frame_confusion problem',
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
                print(bcolors.BOLD+"\n APK: {0}".format(number_apk))
                number_apk = number_apk + 1
                scan = analyze_start(conf, apk_to_analyze,tag, args.string_to_find)
                if scan is not None and not scan: # non ho fatto analisi perchè già presente:
                    list_apk_yet_analyzed.append(apk_to_analyze)
            
            list_apk_to_analyze = list(set(list_apk_to_analyze)-set(list_apk_yet_analyzed))
            if len(list_apk_to_analyze) > 0:  
                print_summary(list_apk_to_analyze,args.file_ouptut_stat, second_start)

        elif args.file_name is not None:
            analyze_start(conf, args.file_name, tag, args.string_to_find)
        else:
            parser.error(bcolors.FAIL+"tool required -f file-name or -d dir-apk "+bcolors.ENDC)    
    else:
        print(bcolors.FAIL+"file "+file_conf+" not found"+bcolors.ENDC)

def scan_retire(apk):
    """
        method that use retirejs to scan eventually vulnerability 
        in library js used by app
    """
    dir_apk_tool = "temp_dir_"+apk.name_only_apk
    cmd = ['retire','-j','--outputformat','json','--path',dir_apk_tool]
    process = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out,err = process.communicate()
    #print(str(out))
    output_retire_apk_tool = None
    if process.returncode == 13:
        # print(process.returncode)
        # print(str(out))
        output = str(err,'utf-8') # output retire js
        output_retire_apk_tool = json.loads(output)
        # print(output_retire_apk_tool)

    dir_html_code = "temp_html_code/html_downlaoded_"+apk.name_only_apk
    cmd.remove(dir_apk_tool)
    cmd.append(dir_html_code)
    process = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out,err = process.communicate()
    output_retire_remote = None
    if process.returncode == 13:
        # print(str(out))
        output = str(err,'utf-8') # output retire js
        output_retire_remote = json.loads(output)
        # print(output_retire_remote)
    cmd_remove_dir = ["rm","-rf",dir_apk_tool]
    subprocess.call(cmd_remove_dir)
    
    return output_retire_apk_tool,output_retire_remote

def print_summary(list_apk_to_analyze, file_output_stat, second_start):
        
        file_stat_final = open("log/{0}".format(str(file_output_stat)),"w")    
        
        #######################################################################################################
        percentual_vuln = len(apk_vulnerable) / len(list_apk_to_analyze) 
        percentual_html_apk = len(apk_with_html_file) / len(list_apk_to_analyze) # app with at least one html page
        percentual_js_enabled = len(apk_with_js_enabled) / len(list_apk_to_analyze) # app with js enable
        percentual_js_interface = len(apk_with_js_interface) / len(list_apk_to_analyze) # app with js interface
        percentual_iframe_not_in_html = len(apk_maybe_vulnerable) / len(list_apk_to_analyze) 
        percentual_app_lib_vuln_retire = len(apk_with_library_vulnerable) / len(list_apk_to_analyze)
        percentual_app_with_xss_dom = len(apk_with_xss) / len(list_apk_to_analyze)
        percentual_app_use_http = len(apk_that_use_http) / len(list_apk_to_analyze)

        #######################################################################################################
        string_html = "\nPercentual app with at least one html file inside: {0}%\n".format(percentual_html_apk*100)
        string_js_enabled = "Percentual app with js enabled {0}%\n".format(percentual_js_enabled * 100)
        string_js_interface = "Percentual app with js interface {0}%\n".format(percentual_js_interface * 100)
        string_percentual_vuln = "Percentual app maybe vulnerable: {0}%, based on tot {1}.\n".format(percentual_vuln*100,len(list_apk_to_analyze))
        string_percentual_iframe_not_in_html = "Percentual app with iframe not in html file {0}\n".format(percentual_iframe_not_in_html*100)
        string_percentual_app_lib_vuln = "Percentual app that use library js vulnerable {0}  based on tot {1}\n".format(percentual_app_lib_vuln_retire * 100, len(list_apk_to_analyze)) 
        string_percentual_app_xss = "Percentual app that use method js vulnerable on xss {0}  based on tot {1}\n".format(percentual_app_with_xss_dom * 100, len(list_apk_to_analyze))
        string_percentual_app_use_http = "Percentual app that use http connection {0}\n".format(percentual_app_use_http * 100)

        apk_string_to_print = "\n-".join(list_apk_to_analyze)

        ########################################################################################################
        second_finish= time.time()
        average_time_apk = (second_finish - second_start)/len(list_apk_to_analyze)
        string_time_percentual = "Average time single apk analyzed {0} sec\n".format(average_time_apk)

        ########################################################################################################
        # print on file
        file_stat_final.write("Apk analyzed: {0} \n-{1} \n".format(len(list_apk_to_analyze),apk_string_to_print))
        file_stat_final.write(string_html)
        file_stat_final.write(string_js_enabled)
        file_stat_final.write(string_js_interface)
        file_stat_final.write(string_percentual_vuln)
        file_stat_final.write(string_percentual_iframe_not_in_html)
        file_stat_final.write(string_time_percentual)
        file_stat_final.write(string_percentual_app_lib_vuln)
        file_stat_final.write(string_percentual_app_xss)
        ########################################################################################################
        # print on terminal
        print()
        print()
        print(bcolors.BOLD+"-- Final Result -- \n")
        print("Apk analyzed: {0} \n-{1} \n".format(len(list_apk_to_analyze),apk_string_to_print))
        print(string_html)
        print(string_js_enabled)
        print(string_js_interface)
        print(string_percentual_vuln)
        print(string_percentual_iframe_not_in_html)
        print(string_time_percentual)
        print(string_percentual_app_lib_vuln)
        print(string_percentual_app_xss)

        

        ########################################################################################################
        if len(apk_vulnerable) > 0:
            string_app_vulnerable = "".join(("- "+str(i).split("/")[-1]+"\n" for i in apk_vulnerable))
            file_stat_final.write("\nThis apps maybe are vulnerable:\n"+string_app_vulnerable)    
            print("This app maybe are vulnerable:"+bcolors.ENDC)
            print(bcolors.FAIL+string_app_vulnerable+bcolors.ENDC)
        
        ########################################################################################################
        if len(apk_maybe_vulnerable) > 0:
            string_app_iframe_inside = "".join(("- "+str(i).split("/")[-1]+"\n" for i in apk_maybe_vulnerable))
            file_stat_final.write("\nThis apps have inside iframe string :\n"+string_app_iframe_inside)    
            print("This app have inside iframe string:"+bcolors.ENDC)
            print(bcolors.WARNING+string_app_iframe_inside+bcolors.ENDC)

        ########################################################################################################
        if len(apk_with_library_vulnerable) > 0:
            app_retire = "".join(("- "+str(i).split("/")[-1]+"\n" for i in apk_with_library_vulnerable))
            file_stat_final.write("\nThis apps use lib vulnerable :\n"+app_retire)    
            print("This apps use lib vulnerable:"+bcolors.ENDC)
            print(bcolors.WARNING+app_retire+bcolors.ENDC)

        ########################################################################################################
        if len(apk_with_xss) > 0:
            app_xss = "".join(("- "+str(i).split("/")[-1]+"\n" for i in apk_with_xss))
            file_stat_final.write("\nThis apps use method js xss vulnerable :\n"+app_xss)    
            print("This apps use function maybe vulnerable on xss:"+bcolors.ENDC)
            print(bcolors.WARNING+app_xss+bcolors.ENDC)
        
        ########################################################################################################
        if len(apk_that_use_http) > 0:
            file_stat_final.write(string_percentual_app_use_http)
            print(string_percentual_app_use_http)
            app_use_http = "".join(("- "+str(i).split("/")[-1]+"\n" for i in apk_that_use_http))
            file_stat_final.write("This apps use http connection:\n"+app_use_http)
            print("This apps maybe use http connection"+bcolors.ENDC)
            print(bcolors.FAIL+app_use_http+bcolors.ENDC)
        

        file_stat_final.close()


def load_conf_file(file_name):
    
    conf = json.load(open(file_name,"r"))
    for key, value in conf.items():
        conf[key] = [str(s) for s in value]
    return conf


if __name__ == "__main__":
    main()