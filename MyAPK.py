#!/usr/env/bin python3
import glob
import logging
import os
import re
import zipfile
import utility
import subprocess
import json
from xssdom import XSScanner
import re
from bs4 import BeautifulSoup
from stringanalysis import FileAnalysis
import requests
from androguard.core.analysis.analysis import Analysis
from androguard.core.androconf import show_logging
from androguard.core.bytecodes.apk import APK
from androguard.core.bytecodes.dvm import DalvikVMFormat
from androguard.core.analysis.analysis import MethodClassAnalysis
from androguard.core.bytecodes.apk import FileNotPresent
from androguard.core.bytecodes.axml import AXMLPrinter
from androguard.decompiler.decompiler import (DecompilerJADX,
                                              JADXDecompilerError)
from androguard.misc import AnalyzeAPK, AnalyzeDex
from androguard.core.analysis.analysis import StringAnalysis
from bcolors import bcolors
import threading
import xml.etree.ElementTree as ET
import hashlib
import smaliparser


show_logging(level=logging.CRITICAL)  # androguard


class MyAPK:

    def __init__(self, name_file, conf, file_log, tag, string_to_find, logger, api_monitor_dict=None, network_dict=None, use_smaliparser=True):

        self.name_apk = name_file
        self.name_only_apk = self.name_apk.split("/")[-1].rsplit(".", 1)[0]
        self.conf = conf
        self.apk = APK(name_file)
        self.package_name = self.apk.get_app_name()
        self.dalviks_format = None
        self.analysis_object = None
        self.dict_file_with_string = dict()  # file che contengono la stringa ricercata
        self.string_to_find = string_to_find  # stringa da cercare
        self.is_contain_permission = False  # se contiene i permessi del file conf
        self.url_loaded = list()  # list url that has been loaded
        # se contiene i file ibridi --> probabilmente app ibrida
        self.is_contain_file_hybrid = False
        # pagine_html con iframe se contengono csp [True o False]
        self.find_csp = dict()
        # se contiene i metodi all'interno del file conf.json
        self.is_contains_all_methods = False
        self.zip = zipfile.ZipFile(self.name_apk)  # get zip object from apk
        self.list_file = self.zip.namelist()  # tutti i file all'interno
        self.html_file = FileAnalysis.find_html_file(self.list_file)
        self.file_log = file_log  # name to file log
        self.javascript_enabled = False
        self.internet_enabled = False
        self.file_vulnerable_frame_confusion = list()
        self.file_with_string_iframe = list()
        self.isHybrid = None
        # dict indexes with name method and get encoded methods where function was called
        self.method = dict()
        self.all_url = list()  # all url in the apk
        self.file_download_to_analyze = dict()
        self.search_tag = tag
        self.md5_file_to_url = dict()  # dict with indexes with name and get url remote
        self.file_config_hybrid = None
        self.list_origin_access = list()
        self.logger = logger
        self.api_monitor_dict = api_monitor_dict
        self.network_dict = network_dict
        self.file_hybrid = list()
        self.javascript_interface = False
        self.javascript_file = FileAnalysis.find_js_file(self.list_file)
        self.src_iframe = dict()
        self.page_xss_vuln = dict()
        self.is_vulnerable_frame_confusion = False
        self.http_connection = list()
        self.http_connection_static = list()
        self.all_http_connection = list()
        self.url_dynamic = list()
        self.use_smaliparser = use_smaliparser
        self.use_analyze = not use_smaliparser
        self.method_2_value = dict()
        self.dynamic_javascript_enabled = False
        self.dynamic_javascript_interface = False
        self.all_url_dynamic = list()
        self.load_url_dynamic = list()

    def read(self, filename, binary=True):
        with open(filename, 'rb' if binary else 'r') as f:
            return f.read()

    
    def check_permission(self, list_permission_to_find):
        """
            check permission hybrid app
        """
        use_permission_checker = True
        if not use_permission_checker:    
            permission_find = list()
            for permission_to_check in list_permission_to_find:
                if permission_to_check in self.apk.get_permissions():
                    permission_find.append(True)  # contenere tutti i permessi
                    if permission_to_check == "android.permission.INTERNET":
                        self.internet_enabled = True

            # print(permission_to_check)
            self.logger.logger.info("[Permission declared Start]")
            for p in self.apk.get_permissions():
                self.logger.logger.info(p)
            self.logger.logger.info("[Permission End]\n")

            self.is_contain_permission = len(
                permission_find) == len(list_permission_to_find)
        else:
            
            if "PermissionChecker.jar" in os.listdir("."):
                dir_permission_checker = "PermissionChecker.jar"
            else:
                dir_permission_checker = os.path.join("inspectHybridApk","PermissionChecker.jar")
            try:
                cmd_permission_checker = ["java","-jar",dir_permission_checker,self.name_apk]
                process = subprocess.Popen(cmd_permission_checker,stdout=subprocess.PIPE)
                result = process.communicate()[0]
                # error here 
                result = json.loads(result)
                # requiredAndUsed = result['requiredAndUsed']

                notRequiredButUsed = result['notRequiredButUsed']
                declared = result['declared']
                # requiredButNotUsed = result['requiredButNotUsed']
                list_permission = list(set().union(notRequiredButUsed,declared))
                permission_find = list()
                for permission_to_check in list_permission_to_find:
                    if permission_to_check in list_permission:
                        permission_find.append(True)  # contenere tutti i permessi
                        if permission_to_check == "android.permission.INTERNET":
                            self.internet_enabled = True

                self.logger.logger.info("[Permission declared and not required but used Start]")
                for p in list_permission:
                    self.logger.logger.info(p)
                self.logger.logger.info("[Permission End]\n")

                self.is_contain_permission = len(
                    permission_find) == len(list_permission_to_find)

            except Exception as e:
                permission_find = list()
                for permission_to_check in list_permission_to_find:
                    if permission_to_check in self.apk.get_permissions():
                        permission_find.append(True)  # contenere tutti i permessi
                        if permission_to_check == "android.permission.INTERNET":
                            self.internet_enabled = True

                # print(permission_to_check)
                self.logger.logger.info("[Permission declared Start]")
                for p in self.apk.get_permissions():
                    self.logger.logger.info(p)
                self.logger.logger.info("[Permission End]\n")

                self.is_contain_permission = len(
                    permission_find) == len(list_permission_to_find)
            

    def is_hybird(self):
        """
            function to check se apk is hybrid,
            1) if contain file from conf.json (cordova/plugin/phonegap/config)
            2) if present permission internet (inutile)
        """
        if self.isHybrid is None:
            list_file_to_find = self.conf["file_to_check"]
            list_permission_to_find = self.conf["permissions_to_check"]

            self.is_contain_file_hybrid, self.file_hybrid = FileAnalysis.check_file_hybrid(
                self.list_file, list_file_to_find)

            if self.is_contain_file_hybrid:
                self.logger.logger.info(
                    "Hybrid file found are: " + str(self.file_hybrid))

            self.check_permission(list_permission_to_find)

            self.isHybrid = self.is_contain_permission and self.is_contain_file_hybrid

            # using apktool
            FNULL = open(os.devnull, 'w')
            print(bcolors.WARNING+"[*] Starting apktool "+bcolors.ENDC)
            self.logger.logger.info("Starting apktool")
            cmd = ["apktool", "d", "-o", "temp_dir_" +
                   self.name_only_apk, self.name_apk, "-f"]
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            try:
                if self.isHybrid:
                    # now can search file in temp_dir
                    file_xml = open(
                        "temp_dir_{0}/res/xml/config.xml".format(self.name_only_apk))
                    file_data_xml = str(file_xml.read())
                    self.file_config_hybrid = file_data_xml
                    # parsing file config
                    self.check_whitelist()

            except OSError as e:
                print(
                    bcolors.FAIL+"File config.xml not found, it is necessary to decompile the application first"+bcolors.ENDC)
                # remove dir
                self.logger.logger.error(
                    "[ERROR file config.xmls] {0} \n".format(e))

        return self.isHybrid

    def check_whitelist(self):
        """
            function that obtain access origin from file 
            config.xml
        """

        # get xml_object ElementTree
        if self.file_config_hybrid is not None and self.isHybrid:
            self.list_origin_access = list()
            root = ET.fromstring(self.file_config_hybrid)

            xmlns = "{http://www.w3.org/ns/widgets}"  # default namespace

            # TODO aggiungere altri elementi della whitelist
            # 1) <allow-navigation href="http://*/*" />
            # Controls which URLs the WebView itself can be navigated to. Applies to top-level navigations only.
            # 2) <allow-intent href="http://*/*" />
            # Controls which URLs the app is allowed to ask the system to open. By default, no external URLs are allowed
            # 3) <access origin="http://google.com" />
            # Controls which network requests (images, XHRs, etc) are allowed to be made (via cordova native hooks).

            for child in root.findall(xmlns+"access"):
                # print( child.tag, child.attrib.get("origin"))
                self.list_origin_access.append(child.attrib.get("origin"))

            self.logger.logger.info("[INIT ACCESS ORIGIN LIST]")
            for value in self.list_origin_access:
                self.logger.logger.info("origin: %s", value)
            self.logger.logger.info("[END ACCESS ORIGIN LIST]\n")

    def analyze_xss_dom(self, file_name, file_content):
        """ 
            search static dom xss based on regex
        """
        # TODO se file_name end with js use TaintJS altrimenti usare questo
        # per usare taint js salvare il contenuto in una dir temporanea e usarlo
        # da li dentro
        try:
            print("file xss dom analyze {0}".format(file_name))
            
            if file_name.endswith(".js"):
                file_open_temp = "inspectHybridApk/TaintJS/temp_file_to_analyze.js"
                file_to_write = open(file_open_temp,"w")
                file_to_write.write(file_content)
                file_to_write.close()
                cmd_node = ["node","--max-old-space-size=4096","inspectHybridApk/TaintJS/app.js",file_open_temp]
                process = subprocess.Popen(cmd_node,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                out,err = process.communicate()
                out = out.decode('utf-8').strip()
                err = err.decode('utf-8')
                os.remove(file_open_temp)
                # no error
                if err != '': # no error
                    if out == 'true': # is vuln
                        self.page_xss_vuln[file_name] = True
                else:

                    page_analyze = XSScanner(file_name, file_content)
                    page_analyze.analyze_page()
                    if len(page_analyze.sink) > 0 or len(page_analyze.source) > 0:
                        self.page_xss_vuln[file_name] = page_analyze
            else:
                soup = BeautifulSoup(file_content, 'html.parser')
                scripts = soup.find_all("script")
                for script in scripts:
                    value = script.get_text().strip()
                    file_open_temp = "inspectHybridApk/TaintJS/temp_file_to_analyze.js"
                    file_to_write = open(file_open_temp,"w")
                    file_to_write.write(value)
                    file_to_write.close()
                    cmd_node = ["node","--max-old-space-size=4096","inspectHybridApk/TaintJS/app.js",file_open_temp]
                    process = subprocess.Popen(cmd_node,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                    out,err = process.communicate()
                    out = out.decode('utf-8').strip()
                    err = err.decode('utf-8')
                    os.remove(file_open_temp)
                    # no error
                    if err != '': # no error
                        if out == 'true': # is vuln
                            self.page_xss_vuln[file_name] = True
                    else:

                        page_analyze = XSScanner(file_name, file_content)
                        page_analyze.analyze_page()
                        if len(page_analyze.sink) > 0 or len(page_analyze.source) > 0:
                            self.page_xss_vuln[file_name] = page_analyze
        except Exception:

            page_analyze = XSScanner(file_name, file_content)
            page_analyze.analyze_page()
            if len(page_analyze.sink) > 0 or len(page_analyze.source) > 0:
                self.page_xss_vuln[file_name] = page_analyze
    
    def find_string(self,  file_to_search, remote=False, debug=False):
        """
            find string inside file of apk(html,xml,ecc..) (not yet decompiled)
        """
        debug = True
        # print(self.md5_file_to_url.keys())
        if remote:
            self.logger.logger.info("[START REMOTE FILE ANALYZE]")
        else:
            self.logger.logger.info("[START FILE ANALYZE]")
        for file_to_inspect, insideAPK in file_to_search.items():
            if not remote and debug:
                self.logger.logger.info("File: "+file_to_inspect)
            else:
                if debug:
                    try:
                        m = hashlib.md5()
                        m.update(file_to_inspect.encode('utf-8'))
                        self.logger.logger.info(
                            "Remote File in: {0}".format(file_to_inspect))

                        if m.hexdigest() in self.md5_file_to_url.keys():
                            self.logger.logger.info(
                                "URL: {0}".format(self.md5_file_to_url[str(m.hexdigest())]))

                    except KeyError as e:
                        self.logger.logger.warning(
                            "Key error as {0} ".format(e))

            file_to_inspect_split = file_to_inspect.split("?",1)[0] # remove parameter 
            if remote and not (file_to_inspect_split.endswith(".js") or file_to_inspect_split.endswith(".html")) :
                # add extension html on file
                # of default wget add this extension
                file_to_inspect = file_to_inspect + ".html"

            if insideAPK:
                data = self.zip.open(file_to_inspect)
            else:
                data = open(file_to_inspect, "r")

            #######################################################################################################
            # start xss analysis on this file
            try:

                content_file = data.read()
                thread = threading.Thread(
                    name="xss_"+file_to_inspect, target=self.analyze_xss_dom, args=(file_to_inspect, str(content_file),))
                thread.start()
                #######################################################################################################

                file_read = str(content_file)
                soup = BeautifulSoup(file_read, 'lxml')
                try:

                    find_iframe, list_row_string, list_src_iframe, find_string_not_tag = FileAnalysis.find_string(
                        self.string_to_find, self.search_tag, file_to_inspect,  file_read, soup, self.logger)

                    #######################################################################################################
                    # TODO insert in method --> String Analysis
                    if find_iframe and self.string_to_find == "iframe":
                        if not find_string_not_tag:
                            self.dict_file_with_string[file_to_inspect] = list_row_string
                            self.src_iframe[file_to_inspect] = list_src_iframe
                        
                        # TODO search id iframe in file js in script src
                        if not self.search_tag or file_to_inspect_split.endswith(".js") or find_string_not_tag:
                            self.file_with_string_iframe.append(
                                file_to_inspect)  # append file with iframe
                            print(bcolors.FAIL+"Found "+self.string_to_find +
                                  " in line "+str(list_row_string)+bcolors.ENDC)
                            self.logger.logger.info(
                                "Found  %s file %s in line %s", self.string_to_find, file_to_inspect, str(list_row_string))

                        else:
                            print(bcolors.FAIL+"Found tag "+self.string_to_find +
                                  ",  "+str(len(list_row_string)) + " times "+bcolors.ENDC)
                            self.logger.logger.info(
                                "Found in file %s tag %s , %s times", file_to_inspect, self.string_to_find, str(len(list_row_string)))

                            if len(self.src_iframe[file_to_inspect]) > 0:
                                self.logger.logger.info("Founded this src {0} in iframe tag inside file {1}".format(
                                    str(self.src_iframe[file_to_inspect]), file_to_inspect))

                            else:
                                self.logger.logger.info(
                                    "No src founded in iframe tag inside file {0}".format(file_to_inspect))

                        #######################################################################################################

                        # TODO aggiungere il content e fare conclusioni su di esso e per i file JavaScript
                        find_csp = soup.find(
                            "meta", {"http-equiv": "Content-Security-Policy"})
                        if find_csp is not None:
                            print(
                                bcolors.OKGREEN+"Find CSP with content: [" + find_csp["content"]+"]"+bcolors.ENDC)
                            self.logger.logger.info(
                                "Find CSP with content: [" + find_csp["content"]+"]")
                            self.find_csp[file_to_inspect] = True

                        # only file html
                        elif not file_to_inspect_split.endswith(".js"):
                            print(bcolors.FAIL+"No CSP found!"+bcolors.ENDC)
                            self.logger.logger.info("No CSP found!")
                            self.find_csp[file_to_inspect] = False
                        elif file_to_inspect_split.endswith(".js"):
                            print(bcolors.FAIL+"It is a JS file, no CSP found!"+bcolors.ENDC)
                            self.logger.logger.info("It is a JS file, no CSP found!, investigate manually\n")
                            self.find_csp[file_to_inspect] = False

                    else:
                        print(bcolors.OKGREEN+"No "+self.string_to_find +
                              " in "+file_to_inspect+bcolors.ENDC)
                        self.logger.logger.info(
                            "No "+self.string_to_find+" in "+file_to_inspect+"\n")

                except zipfile.BadZipfile as e:
                    self.logger.error("Error bad zip file {0}".format(e))
                    continue
                except ValueError as e:
                    self.logger.error("Error value error {0}".format(e))
                    continue
            except UnicodeDecodeError as e:
                self.logger.logger.error("Error unicode error {0}".format(e))
                continue
        self.logger.logger.info("[END ANALYZE FILE]")
        return None

    def find_method_used(self):
        """
            funzione per ricercare i metodi che sono usati 
            all'interno dell'apk, tanto lenta
        """
        used_jadx = False
        if used_jadx:

            # Create DalvikVMFormat Object
            self.dalvik_format = DalvikVMFormat(self.apk)
            # Create Analysis Object
            self.analysis_object = Analysis(self.dalvik_format)
            # Load the decompiler
            # Make sure that the jadx executable is found in $PATH
            # or use the argument jadx="/path/to/jadx" to point to the executable
            decompiler = DecompilerJADX(
                self.dalvik_format, self.analysis_object)

            # propagate decompiler and analysis back to DalvikVMFormat
            self.dalvik_format.set_decompiler(decompiler)
            self.dalvik_format.set_vmanalysis(self.analysis_object)

            # Now you can do stuff like:
            list_method_analysis = self.analysis_object.get_methods()
            for method_analys in list_method_analysis:
                method_name = method_analys.get_method().get_name()
                # print(method_encoded.get_method().get_source())
                self.method[method_name] = list(method_analys.get_xref_from())

        elif self.use_analyze:
            # return apk, list dex , object analysis
            apk, self.dalvik_format, self.analysis_object = AnalyzeAPK(
                    self.name_apk)
            
            for method_analys in self.analysis_object.get_methods():
                method_name = method_analys.get_method().get_name()
                # from method_name get list dove esso viene chiamato
                self.method[method_name] = list(method_analys.get_xref_from())
        
        elif self.use_smaliparser:
            # use smali parser, apktool and grep invece di Androguard
            dir_apk_tool = "temp_dir_" + self.name_only_apk+"/"
            list_method_to_analyze = self.conf["method_smali_parser"]
            self.method_2_value, self.all_url = smaliparser.start(dir_apk_tool,list_method_to_analyze)


        else:  # TODO to make faster analysis but not work well
            self.dalvik_format = DalvikVMFormat(self.apk)
            for encoded_method in self.dalvik_format.get_methods():
                method_analysis = MethodClassAnalysis(encoded_method)

                method_name = method_analysis.get_method().get_name()
                # print(method_name)
                # from method_name get list dove esso viene chiamato
                self.method[method_name] = list(
                    method_analysis.get_xref_from())
                # print(self.method[method_name])

    def check_method_conf(self):
        """
            function to check se methods inside conf.json method_to_check is used inside apk
        """

        method_to_find = self.conf["method_to_check"]
        method_present = dict()

        try:
            
            if self.use_smaliparser:
                if "setJavaScriptEnabled" in self.method_2_value.keys():
                    if "0x1" in self.method_2_value["setJavaScriptEnabled"]:
                        self.javascript_enabled = True
                        method_present["setJavaScriptEnabled"] = True
                if  "addJavascriptInterface" in self.method_2_value.keys():
                    self.javascript_interface = True
                    method_present["addJavascriptInterface"] = True

            else:
                for mf in method_to_find:
                    method_present[mf] = False
                    for mapk in self.method.keys():
                        if mf in mapk:
                            method_present[mf] = True        
                
                if method_present["setJavaScriptEnabled"]:
                    for value in self.method["setJavaScriptEnabled"]:
                        try:
                            if value[1] is not None:
                                encoded_method = value[1]
                                source_code = FileAnalysis.get_list_source_code(
                                    encoded_method)
                                if FileAnalysis.check_method_used_value(source_code, "setJavaScriptEnabled", "1"):
                                    # volendo si possono memorizzare tutti i file che lo settano atrue
                                    self.javascript_enabled = True
                                    break

                        except (TypeError, AttributeError, KeyError) as e:
                            self.logger.logger.error(
                                "Exception during check method used {0}".format(e))
                            continue
            print()
            if self.dynamic_javascript_enabled:
                self.logger.logger.info(
                "[JavaScript enabled (check dynamically) :"+str(self.dynamic_javascript_enabled)+"]")    
            else:
                self.logger.logger.info(
                "[JavaScript enabled (check static):  "+str(self.javascript_enabled)+"]")

        except Exception as e:
            self.logger.logger.error(
                "File conf.json without method setJavaScriptEnabled {0}".format(e))

        try:
            if not self.use_smaliparser:
            
                if self.dynamic_javascript_interface:
                    
                    self.logger.logger.info("[Add interface WebView (check dynamically): "+str(self.dynamic_javascript_interface)+"]")
                    self.javascript_interface = self.dynamic_javascript_interface
                    
                else:

                    self.logger.logger.info("[Add interface WebView (check static): "+str(method_present["addJavascriptInterface"])+"]")
                    self.javascript_interface = method_present["addJavascriptInterface"]
            
            else:
            
                if self.dynamic_javascript_interface:
                    method_present["addJavascriptInterface"] = self.dynamic_javascript_interface
                    self.logger.logger.info("[Add interface WebView (check dynamically): "+str(self.dynamic_javascript_interface)+"]")
                
                else:
                    method_present["addJavascriptInterface"] = self.javascript_interface
                    self.logger.logger.info("[Add interface WebView (check static): "+str(self.javascript_interface)+"]")
            
        except Exception as e:
            # nothing
            self.logger.logger.error(
                "File conf.json without method addJavascriptInterface {0}\n".format(e))

        self.is_contains_all_methods = len(
            method_present) == len(method_to_find)
        return self.is_contains_all_methods

    def find_url_in_apk(self):
        """
            find all url/uri inside apk
        """

        # add url using dynamic analysis
        if self.api_monitor_dict is not None and self.network_dict is not None:
            self.add_url_dynamic()
        
        ##############################################################################
        # use smali_parser
        if self.use_smaliparser:
            # add url loaded for smali_parsr
            if "loadUrl" in self.method_2_value.keys(): 
                all_url_loaded = self.method_2_value["loadUrl"]  
                
                # da queste devo filtrare ottenendo solo quelle http/https
                temp_url_loaded = list(filter(lambda x: x is not None and (x.startswith("http") or x.startswith("https")) ,all_url_loaded))
                self.url_loaded = list(set().union(self.url_loaded,temp_url_loaded))

        else:
            # ALL string inside apk
            # use AndroGuard        
            # url regularp expression
            # url_re = "(http:\/\/|https:\/\/|file:\/\/\/)?[-a-zA-Z0-9@:%._\+~#=]\.[a-z]([-a-zA-Z0-9@:%_\+.~#?&//=]*)"
            url_re = "^(http:\/\/|https:\/\/)\w+"
            list_string_analysis = list()  # list of string analysis object
            # se uso aalysis object
            if self.analysis_object is not None:
                list_string_analysis = self.analysis_object.find_strings(
                    url_re)  # --> gen object

            else:
                list_string = self.dalvik_format.get_regex_strings(url_re)
                
                # get all string inside apk
                for string_value in list_string:
                    list_string_analysis.append(StringAnalysis(string_value))

            ##################################################################################
            temp_string_value = list()
            # string- tuple with classAnalysis e encodeMethod that use the string
            dict_class_method_analysis = dict()
            for string_analysis in list_string_analysis:
                temp_string_value.append(string_analysis.get_value()) # tutte le url
                dict_class_method_analysis[string_analysis.get_value()] = list(
                    string_analysis.get_xref_from()) # url e relativo codice dove le ho trovate

            ##################################################################################
            # per ogni file, otteniamo una lista di  tupla
            # class analysis e encoded_method
            for key in dict_class_method_analysis.keys():
                for value in dict_class_method_analysis[key]:
                    # class_analysis = value[0]
                    try:
                        if value[1] is not None:
                            encoded_method = value[1]
                            # split the instruction in a list
                            source_code = FileAnalysis.get_list_source_code(encoded_method)
                            if source_code is not None:
                                self.all_url.append(key) # appendo l'url
                                if FileAnalysis.check_method_used_value(source_code, "loadUrl", key):
                                    self.url_loaded.append(key) # appendo url se caricata dentro loadUrl

                    except (TypeError, AttributeError, KeyError) as e:
                        self.logger.logger.error(
                            "Exception during find url in apk {0}".format(e))
                        continue

        #######################################################################################################
        # debug part
        if len(self.url_loaded) > 0:
            # print(self.url_loaded)
            self.logger.logger.info("[START URL LOADED INSIDE LOAD FUNCTION]")
            self.url_loaded = list(set(self.url_loaded))
            for u in self.url_loaded:
                if u.startswith("http://"):
                    self.http_connection_static.append(u)
                self.logger.logger.info(
                    "Url inside load function: {0}".format(u))
            self.logger.logger.info("[END URL LOADED INSIDE LOAD FUNCTION]")

            md5_file_to_url, file_download_to_analyze = utility.download_page_with_wget(
                self.name_only_apk, self.url_loaded)
            for key in md5_file_to_url.keys():
                if key not in self.md5_file_to_url.keys():
                    self.md5_file_to_url[key] = md5_file_to_url[key]

            for key in file_download_to_analyze.keys():
                if key not in self.file_download_to_analyze.keys():
                    self.file_download_to_analyze[key] = file_download_to_analyze[key]

            # self.download_page_loaded_with_wget()
            self.find_string(self.file_download_to_analyze, remote=True)

        if len(self.all_url) > 0:
            self.all_url = list(set(self.all_url))
            self.logger.logger.info("[START ALL URL INSIDE APK]")
            for u in self.all_url:
                if u.startswith("http://"):
                    self.all_http_connection.append(u)
                self.logger.logger.info("Url inside apk {0}".format(u))
            self.logger.logger.info("[END ALL URL INSIDE APK]")
        
        html_dir = "temp_html_code/html_downloaded_{0}/".format(self.name_only_apk)
        if os.path.exists(html_dir) and len(os.listdir(html_dir)) > 0:
            # zip -r squash.zip dir1
            subprocess.call(["zip","-r","temp_html_code/html_{0}.zip".format(self.name_only_apk),html_dir], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
           
        # delete dir o provare a zip
        subprocess.Popen(["rm","-rf",html_dir],stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
    # check vulnerability
    def vulnerable_frame_confusion(self):
        """ 
            check if app is vulnerable on frame confusion
            1) iframe nella stringa di ricerca
            2) metodi addJavascriptInterface e setJavaScriptEnabled usati
            3) permesso internet
            4) almeno un file html con l'iframe all'interno e senza csp
        """

        # se esiste almeno un file con iframe senza csp --> vulnerble
        # se è false --> vulnerabile
        csp_in_file_iframe = True

        for file_with_iframe in self.dict_file_with_string.keys():
            csp_in_file_iframe = csp_in_file_iframe and self.find_csp[file_with_iframe]
            if not self.find_csp[file_with_iframe]:
                self.file_vulnerable_frame_confusion.append(file_with_iframe)

        # se vero whitelist implementato male
        white_list_bug = len(
            self.list_origin_access) == 0 or "*" in self.list_origin_access
        self.is_vulnerable_frame_confusion = ("iframe" in self.string_to_find and
                                              self.check_method_conf() and
                                              (len(self.dict_file_with_string) > 0 or len(self.file_with_string_iframe) > 0) and
                                              self.is_contain_permission and
                                              not csp_in_file_iframe and white_list_bug)

    def add_url_dynamic(self):
        """
            function that aggiunge le url caricate 
            diamicamente attraverso che sono state trovate precendetemente 
            dall'analisi dinamica
        """


        #######################################################################################################
        function_load_url = ["loadUrl"]  # funzioni che caricano url in Android
        url_api_monitor = list()
        for keys in self.api_monitor_dict.keys():
            
            if keys in function_load_url:
                url_api_monitor = list(set().union(
                    url_api_monitor, self.api_monitor_dict[keys]["args"]))
            # dynamic interface and javascript enabled
            if keys == "addJavascriptInterface":
                self.dynamic_javascript_interface = True
            
            # TODO check --> considero javascriptenabled se ho solo l'interface abilitata
            if keys == "setJavaScriptEnabled" and True in self.api_monitor_dict[keys]["args"]:
                self.dynamic_javascript_enabled = True
            
        # get all http/https/file in load function
        self.url_dynamic = filter(lambda x: x.startswith(
            "http://") or x.startswith("https://") or x.startswith("file://"), url_api_monitor)

        self.load_url_dynamic = self.url_dynamic
        #######################################################################################################
        # TODO mettere la funzione evaluateJavaScript o loadUrl javascript: --> come se fosse un file javascript
        javascript_load_url = filter(
            lambda x: x.startswith("javascript:"), url_api_monitor)

        # method that exec js in recent api
        javascript_evaluate = list()
        method_evaluate_js = ["evaluateJavascript"]
        for keys in self.api_monitor_dict.keys():
            if keys in method_evaluate_js:
                javascript_evaluate = list(set().union(
                    javascript_evaluate, self.api_monitor_dict[keys]["args"]))

        # now write this code in a file and analyze them
        javascript_code_exec = list(set().union(
            javascript_load_url, javascript_evaluate))

        name_file = "code_js_loaded_"
        i = 1
        list_file_js_dynamic = dict()
        dir_write = os.path.join("temp_html_code","html_downloaded_"+self.name_only_apk)
        
        if not os.path.isdir(dir_write):
            os.makedirs(dir_write)
        
        for code in javascript_code_exec:
            file_js = os.path.join(dir_write,name_file+"{0}.js".format(i)) 
            file = open(file_js,"w")
            file.write(code)
            file.close()
            list_file_js_dynamic[file_js] = False
            self.javascript_file[file_js] = False
        
        self.logger.logger.info("[Start javascript code dynamic]")
        self.find_string(list_file_js_dynamic)
        self.logger.logger.info("[End javascript code dynamic]\n")

        #######################################################################################################
        # TODO mettere metodi cordova

        #######################################################################################################
        # ora devo filtrare solo le url che sono http/https
        url_network = list()
        for keys in self.network_dict.keys():
            # TODO check
            url_list_new = list()
            for url in self.network_dict[keys]["url"]:
                # search ip
                ip = re.findall(r"[0-9]+(?:\.[0-9]+){3}", url)
                if ip != None and len(ip) > 0:
                    # change ip with host
                    # get only first element of every list --> every list are max 1 element
                    url_new = url.replace(
                        ip[0], self.network_dict[keys]["host"][0])
                    url_list_new.append(url_new)
                else:
                    url_list_new.append(url)
            # add new url
            self.network_dict[keys]["url"] = url_list_new
            url_network = list(set().union(
                url_network, self.network_dict[keys]["url"]))

        ##########################################################################################################
        # remove url google 
        # url effettivamente caricate nell'applicazione
        self.url_dynamic = list(set().union(self.url_dynamic, url_network)) 
        self.all_url_dynamic = self.url_dynamic
        url_dynamic_to_remove = list()
        for url_dyn in self.url_dynamic:
            for url_to_check in self.conf["url_to_remove"]:
                if url_to_check in url_dyn:
                    url_dynamic_to_remove.append(url_dyn)
        
        # TODO maybe to add 
        url_dynamic_to_remove = list(set(url_dynamic_to_remove))
        for url_to_remove in url_dynamic_to_remove:
            self.url_dynamic.remove(url_to_remove)


        #######################################################################################################
        self.url_loaded = list(set().union(
            self.url_loaded, self.url_dynamic))
        
        self.all_url = list(set().union(self.all_url, self.url_loaded))
        self.logger.logger.info("[Init add url dynamic ]")
        for u in self.url_dynamic:
            if u.startswith("http://"):
                self.http_connection.append(u)
            if u in self.load_url_dynamic:
                self.logger.logger.info("Url dynamic inside loadUrl{0}".format(u))
            else:
                self.logger.logger.info("Url dynamic {0}".format(u))

        self.logger.logger.info("[End url dynamic]\n")
