#!/usr/env/bin python3
import glob
import logging
import os
import re
import zipfile
import utility
import subprocess
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
from androguard.misc import AnalyzeAPK
from androguard.core.analysis.analysis import StringAnalysis
from bcolors import bcolors
import threading
import xml.etree.ElementTree as ET

show_logging(level=logging.CRITICAL) # androguard


class MyAPK:
    
    def __init__(self, name_file, conf, file_log, tag, string_to_find, logger, api_monitor_dict=None, network_dict=None):
        
        self.name_apk = name_file
        self.name_only_apk = self.name_apk.split("/")[-1].split(".")[0]
        self.conf = conf
        self.apk = APK(name_file)
        self.dalviks_format = None
        self.analysis_object = None
        self.dict_file_with_string = dict()  # file che contengono la stringa ricercata
        self.string_to_find = string_to_find  # stringa da cercare
        self.is_contain_permission = False  # se contiene i permessi del file conf
        self.url_loaded = list()  # list url that has been loaded
        self.is_contain_file_hybrid = False  # se contiene i file ibridi --> probabilmente app ibrida
        self.find_csp = dict()  # pagine_html con iframe se contengono csp [True o False]
        self.is_contains_all_methods = False  # se contiene i metodi all'interno del file conf.json
        self.zip = zipfile.ZipFile(self.name_apk) # get zip object from apk
        self.list_file = self.zip.namelist()  # tutti i file all'interno
        self.html_file = FileAnalysis.find_html_file(self.list_file)
        self.file_log = file_log  # name to file log
        self.javascript_enabled = False
        self.internet_enabled = False
        self.file_vulnerable_frame_confusion = list()
        self.file_js_with_iframe = list()
        self.isHybrid = None
        self.method = dict()  # dict indexes with name method and get encoded methods where function was called
        self.all_url = list()  # all url in the apk
        self.file_download_to_analyze = dict()
        self.search_tag = tag
        self.name_to_url = dict()  # dict with indexes with name and get url remote
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
        
    
    def read(self, filename, binary=True):
        with open(filename, 'rb' if binary else 'r') as f:
            return f.read()

    def check_permission(self,list_permission_to_find):
        """
            check permission hybrid app
        """
        permission_find = list()       
        for permission_to_check in list_permission_to_find:
            if permission_to_check in self.apk.get_permissions():
                permission_find.append(True)  # contenere tutti i permessi
                if permission_to_check == "android.permission.INTERNET":
                    self.internet_enabled = True

        # print(permission_to_check)
        self.logger.logger.info("[Permission Enble Start]")
        for p in self.apk.get_permissions():
            self.logger.logger.info(p)
        self.logger.logger.info("[Permission End]\n")
        self.is_contain_permission = len(permission_find) == len(list_permission_to_find)

    def is_hybird(self):
        """
            function to check se apk is hybrid,
            1) if contain file from conf.json (cordova/plugin/phonegap/config)
            2) if present permission internet (inutile)
        """
        if self.isHybrid is None:
            list_file_to_find = self.conf["file_to_check"]
            list_permission_to_find = self.conf["permissions_to_check"]

            self.is_contain_file_hybrid, self.file_hybrid = FileAnalysis.check_file_hybrid(self.list_file, list_file_to_find)
            
            if self.is_contain_file_hybrid:
                self.logger.logger.info("Hybrid file found are: " +str(self.file_hybrid))
            
            self.check_permission(list_permission_to_find)
    
            self.isHybrid = self.is_contain_permission and self.is_contain_file_hybrid
           
            # using apktool
            FNULL = open(os.devnull, 'w')
            print(bcolors.WARNING+"[*] Starting apktool "+bcolors.ENDC)
            self.logger.logger.info("Starting apktool")
            cmd = ["apktool","d","-o","temp_dir_"+self.name_only_apk,self.name_apk,"-f"]
            subprocess.call(cmd, stdout=FNULL,stderr=subprocess.STDOUT)
            
            try:
                if self.isHybrid:
                    # now can search file in temp_dir
                    file_xml = open("temp_dir_{0}/res/xml/config.xml".format(self.name_only_apk))
                    file_data_xml = str(file_xml.read())
                    self.file_config_hybrid = file_data_xml
                    # parsing file config
                    self.check_whitelist()
                    
            except OSError as e:
                print(bcolors.FAIL+"File config.xml not found, it is necessary to decompile the application first"+bcolors.ENDC)
                # remove dir
                self.logger.logger.error("[ERROR file config.xmls] {0} \n".format(e))

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
            
            xmlns = "{http://www.w3.org/ns/widgets}" # default namespace
            
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
                self.logger.logger.info("origin: %s",value)
            self.logger.logger.info("[END ACCESS ORIGIN LIST]\n")

    def analyze_xss_dom(self, file_name, file_content):
        """ 
            search static dom xss based on regex
        """
        page_analyze = XSScanner(file_name,file_content)
        page_analyze.analyze_page() 
        if len(page_analyze.sink) > 0 or len(page_analyze.source) > 0:
            self.page_xss_vuln[file_name] = page_analyze
        
    def find_string(self,  file_to_search, remote=False, debug=False):
        """
            find string inside file of apk(html,xml,ecc..) (not yet decompiled)
        """
        debug = True

        if remote:
            self.logger.logger.info("[START REMOTE FILE ANALYZE]")
        else:
            self.logger.logger.info("[START FILE ANALYZE]")
        for file_to_inspect, insideAPK in file_to_search.items():
            if not remote and debug:
                self.logger.logger.info("File: "+file_to_inspect)
            else:
                if debug:
                    self.logger.logger.info("Remote File in: %s",file_to_inspect)
                    self.logger.logger.info("URL: %s",self.name_to_url[file_to_inspect])
            
            if remote and not (file_to_inspect.endswith(".js") or file_to_inspect.endswith(".html")): 
                # add extension html on file
                # of default wget add this extension
                file_to_inspect = file_to_inspect + ".html"
                
            if insideAPK:
                data = self.zip.open(file_to_inspect)
            else:
                data = open(file_to_inspect,"r")
            
            #######################################################################################################
            # start xss analysis on this file
            content_file = data.read()
            thread = threading.Thread(name="xss_"+file_to_inspect,target=self.analyze_xss_dom,args=(file_to_inspect,str(content_file),))
            thread.start()
            #######################################################################################################

            try:
                file_read = str(content_file)
                soup = BeautifulSoup(file_read,'lxml')
                try:

                    find_iframe, list_row_string, list_src_iframe = FileAnalysis.find_string(self.string_to_find, self.search_tag, file_to_inspect, file_read, soup, self.logger)
                    
                    #######################################################################################################
                    # TODO insert in method --> String Analysis
                    if find_iframe and self.string_to_find == "iframe":
                        self.dict_file_with_string[file_to_inspect] = list_row_string
                        self.src_iframe[file_to_inspect] = list_src_iframe
                        # TODO search id iframe in file js in script src
                       
                        if not self.search_tag or file_to_inspect.endswith(".js"):
                            self.file_js_with_iframe.append(file_to_inspect) # append file with iframe                             
                            print(bcolors.FAIL+"Found "+self.string_to_find+" in line "+str(list_row_string)+bcolors.ENDC)  
                            self.logger.logger.info("Found  %s file %s in line %s",self.string_to_find,file_to_inspect,str(list_row_string)) 

                        else:
                            print(bcolors.FAIL+"Found tag "+self.string_to_find +",  "+str(len(list_row_string)) +" times "+bcolors.ENDC)
                            self.logger.logger.info("Found in file %s tag %s , %s times",file_to_inspect,self.string_to_find,str(len(list_row_string)) )

                            if len(self.src_iframe[file_to_inspect]) > 0:
                                self.logger.logger.info("Founded this src {0} in iframe tag inside file {1}".format(str(self.src_iframe[file_to_inspect]),file_to_inspect))

                            else:
                                self.logger.logger.info("No src founded in iframe tag inside file {0}".format(file_to_inspect))


                        #######################################################################################################

                        # TODO aggiungere il content e fare conclusioni su di esso e per i file JavaScript
                        find_csp  = soup.find("meta",{"http-equiv":"Content-Security-Policy"})
                        if find_csp is not None :
                            print(bcolors.OKGREEN+"Find CSP with content: [" +find_csp["content"]+"]"+bcolors.ENDC)
                            self.logger.logger.info("Find CSP with content: [" +find_csp["content"]+"]")
                            self.find_csp[file_to_inspect] = True

                        elif not file_to_inspect.endswith(".js"): # only file html
                            print(bcolors.FAIL+"No CSP found!"+bcolors.ENDC)
                            self.logger.logger.info("No CSP found!")
                            self.find_csp[file_to_inspect] = False

                    else:
                        print(bcolors.OKGREEN+"No "+self.string_to_find+" in "+file_to_inspect+bcolors.ENDC)
                        self.logger.logger.info("No "+self.string_to_find+" in "+file_to_inspect+"\n")
                    

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
        use_analyze = True

        if used_jadx:

            # Create DalvikVMFormat Object
            self.dalvik_format = DalvikVMFormat(self.apk)
            # Create Analysis Object
            self.analysis_object = Analysis(self.dalvik_format)
            # Load the decompiler
            # Make sure that the jadx executable is found in $PATH
            # or use the argument jadx="/path/to/jadx" to point to the executable
            decompiler = DecompilerJADX(self.dalvik_format, self.analysis_object)

            # propagate decompiler and analysis back to DalvikVMFormat
            self.dalvik_format.set_decompiler(decompiler)
            self.dalvik_format.set_vmanalysis(self.analysis_object)

            # Now you can do stuff like:
            list_method_analysis = self.analysis_object.get_methods()
            for method_analys in list_method_analysis:
                method_name = method_analys.get_method().get_name()
                #print(method_encoded.get_method().get_source())
                self.method[method_name] = list(method_analys.get_xref_from())

        elif use_analyze:
            # return apk, list dex , object analysis
            apk, self.dalvik_format, self.analysis_object = AnalyzeAPK(self.name_apk)
            
            for method_analys in self.analysis_object.get_methods():
                method_name = method_analys.get_method().get_name()
                # from method_name get list dove esso viene chiamato
                self.method[method_name] = list(method_analys.get_xref_from())
        
        else: # TODO to make faster analysis but not work well
            self.dalvik_format = DalvikVMFormat(self.apk)
            for encoded_method in self.dalvik_format.get_methods():
                method_analysis = MethodClassAnalysis(encoded_method)

                method_name = method_analysis.get_method().get_name()
                print(method_name)
                # from method_name get list dove esso viene chiamato
                self.method[method_name] = list(method_analysis.get_xref_from())
                print(self.method[method_name])
                   
    def check_method_conf(self):
        """
            function to check se methods inside conf.json method_to_check is used inside apk
        """
        method_present = dict()

        method_to_find = self.conf["method_to_check"]
        for mf in method_to_find:
            method_present[mf] = False
            for mapk in self.method.keys():
                if mf in mapk:
                    method_present[mf] = True                    
        try:
            if method_present["setJavaScriptEnabled"]:
                for value in self.method["setJavaScriptEnabled"]:
                    try:
                        if value[1] is not None:
                            encoded_method = value[1]
                            source_code = self.get_list_source_code(encoded_method)
                            if self.check_metod_used_value(source_code,"setJavaScriptEnabled","1"):
                                # volendo si possono memorizzare tutti i file che lo settano atrue
                                self.javascript_enabled = True
                                break

                    except (TypeError, AttributeError, KeyError) as e:
                        self.logger.logger.error("Exception during check method used {0}".format(e))
                        continue
            print()
            self.logger.logger.info("[JavaScript enabled: "+str(self.javascript_enabled)+"]")
        except Exception:
            self.logger.logger.error("File conf.json without method setJavaScriptEnabled")

        try:
            self.logger.logger.info("[Add interface WebView: "+str(method_present["addJavascriptInterface"])+"]")
            self.javascript_interface = method_present["addJavascriptInterface"]
        except Exception:
            # nothing
            self.logger.logger.error("File conf.json without method addJavascriptInterface\n")

        self.is_contains_all_methods = len(method_present) == len(method_to_find)
        return self.is_contains_all_methods

    def find_url_in_apk(self):
        """
            find all url/uri inside apk
        """
        # add url using dynamic analysis
        if self.api_monitor_dict is not None and self.network_dict is not None:
            self.add_url_dynamic()
        
        # url regularp expression
        # url_re = "(http:\/\/|https:\/\/|file:\/\/\/)?[-a-zA-Z0-9@:%._\+~#=]\.[a-z]([-a-zA-Z0-9@:%_\+.~#?&//=]*)"
        url_re = "^(http:\/\/|https:\/\/)\w+"
        list_string_analysis = list() # list of string analysis object
        # se uso aalysis object
        if self.analysis_object is not None:
            list_string_analysis = self.analysis_object.find_strings(url_re) #--> gen object
            
        else:
            list_string = self.dalvik_format.get_regex_strings(url_re)
            
            for string_value in list_string:
                list_string_analysis.append(StringAnalysis(string_value))
        
        temp_string_value = list()
        # string- tuple with classAnalysis e encodeMethod that use the string
        
        dict_class_method_analysis = dict() 
        for string_analysis in list_string_analysis:          
            temp_string_value.append(string_analysis.get_value())
            dict_class_method_analysis[string_analysis.get_value()] = list(string_analysis.get_xref_from())
            

        # per ogni file, otteniamo una lista di  tupla
        # class analysis e encoded_method
        for key in dict_class_method_analysis.keys():
            for value in dict_class_method_analysis[key]:
                # class_analysis = value[0]
                try:
                    if value[1] is not None:
                        encoded_method = value[1]
                        # split the instruction in a list
                        source_code = self.get_list_source_code(encoded_method)
                        if source_code is not None:
                            self.all_url.append(key)
                            if self.check_metod_used_value(source_code,"loadUrl",key):
                                self.url_loaded.append(key)
                            
                except (TypeError, AttributeError, KeyError) as e:
                    self.logger.logger.error("Exception during find url in apk {0}".format(e))
                    continue

        #######################################################################################################
        # debug part
        if len(self.url_loaded) > 0:
            #print(self.url_loaded)
            self.logger.logger.info("[START URL LOADED INSIDE LOAD FUNCTION]")
            for u in self.url_loaded:
                self.logger.logger.info("Url inside load function: {0}".format(u))
            self.logger.logger.info("[END URL LOADED INSIDE LOAD FUNCTION]")
            
            # TODO check if work
            # self.download_page_loaded()
            name_to_url, file_download_to_analyze = utility.download_page_with_wget(self.name_only_apk, self.url_loaded)
            self.name_to_url = dict(self.name_to_url, **name_to_url)
            self.file_download_to_analyze = dict(self.file_download_to_analyze, **file_download_to_analyze)
            
            # self.download_page_loaded_with_wget()
            self.find_string(self.file_download_to_analyze, remote=True)

        if len(self.all_url) > 0 :
            self.logger.logger.info("[START ALL URL INSIDE APK]")
            for u in self.all_url:
                self.logger.logger.info("Url inside apk {0}".format(u))
            self.logger.logger.info("[END ALL URL INSIDE APK]")

    def get_list_source_code(self, encoded_method):
        """
            from object encoded_method obtain source code list
        """  
        try:
            source_code = encoded_method.get_source().replace("\n", "")
            source_code = source_code.replace(" ", "")
            source_code = source_code.split(";")
            return source_code
        except TypeError as e:
            #self.logger.logger.error("Error as encoded_method {0} on method get_source_code {1}".format(encoded_method,e))
            return None

    def download_page_loaded_with_wget(self):
        """
            function to download the page loaded by the app
            using list self.url_loaded
            after this -> check if frame confusion may come from this
        """
        html_dir = "temp_html_code/html_downloaded_"+self.name_only_apk
        print(bcolors.WARNING+"\n[*] Download remote page in: "+html_dir+bcolors.ENDC)
        cmd_wget = ['wget' ,'-E', '-H' ,'-k',' -K ','-T','1','-nd' ,'-N', '-p','-P', html_dir]
        FNULL = open(os.devnull, 'w')
        for url in self.url_loaded:
            if url[-1] == "/":
                url = url[:-1]    
            cmd_wget.append(url)
            subprocess.call(cmd_wget,stdout=FNULL,stderr=FNULL)
            name_file = url.split("/")[-1]
            path_complete = html_dir+"/"+name_file
            self.name_to_url[path_complete] = url 
            # self.file_download_to_analyze[path_complete] = False
            cmd_wget.remove(url)

        # now add all file download in this dir with extension html and js
        for root, _, files in os.walk(html_dir):
                for file_download in files:
                    if file_download.endswith(".html") or file_download.endswith(".js"):
                        self.file_download_to_analyze[os.path.join(root,file_download)] = False
            
    def download_page_loaded(self):
        """
            function to download the page loaded by the app
            using list self.url_loaded
            after this -> check if frame confusion may come from this
        """
        # name_only_apk = self.name_apk.split("/")[-1].split(".")[0]
        
        html_dir = "temp_html_code/html_downloaded_"+self.name_only_apk
        if not os.path.exists(html_dir):
            os.makedirs(html_dir)
        print(bcolors.WARNING+"\n[*] Download remote page in: "+html_dir+bcolors.ENDC)
        
        for url in self.url_loaded:
            try:
                r = requests.get(url,timeout=10)
                # print(url)
                if r.status_code == 200:
                    name_file = url.split("/")[-1]
                    path_complete = html_dir+"/"+name_file
                    open(path_complete,"wb").write(r.content)
                    self.name_to_url[path_complete] = url 
                    self.file_download_to_analyze[path_complete] = False
                else:
                    self.logger.logger.error("Failed response code: {0} for {1}  ".format(r.status_code,url))
            except requests.exceptions.InvalidSchema:
                self.logger.logger.error("Invalid Schema exception for url: {0}, try add http:// ".format(url))
                url = "http://{0}".format(url)
                
                # print(url)
                try: # provo aggiungendo http o https
                    r = requests.get(url,timeout=10)
                    if r.status_code == 200:
                
                        name_file = url.split("/")[-1]
                        path_complete = html_dir+"/"+name_file
                        open(path_complete,"wb").write(r.content)
                        self.name_to_url[path_complete] = url 
                        self.file_download_to_analyze[path_complete] = False
                    else:
                        self.logger.logger.error("Failed response code: {0} for {1}  ".format(r.status_code,url))
                except requests.exceptions.ConnectionError as e: # se non funziona di nuovo
                    self.logger.logger.error("Failed connection errror after add http download: {0} ".format(url))
                    continue
            except requests.exceptions.ConnectionError as e:
                self.logger.logger.error("Failed connection error download: {0} ".format(url))
                continue
            except Exception as e:
                self.logger.logger.error("Failed download: {0} for exception {1}".format(url,e))
                continue

    # invece che valore magari che venga passato una variabile come valore
    def check_metod_used_value(self,list_source_code,metodo,value):
        """
           funzione che prende in ingresso un metodo
           e il valore, e controlla se in quel metodo viene passato quel 
           valore
        """
        r = re.compile(metodo) # per ora solo load_url
        list_new = filter(r.findall,list_source_code)
        for line_finded in list_new:
            if value in line_finded:
                return True
        return False
        
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
        white_list_bug = len(self.list_origin_access) == 0 or "*" in self.list_origin_access
        self.is_vulnerable_frame_confusion = ("iframe" in self.string_to_find and 
                self.check_method_conf()  and 
                len(self.dict_file_with_string) > 0 and
                self.is_contain_permission and
                not csp_in_file_iframe and white_list_bug)
    
    def add_url_dynamic(self):
        """
            function that aggiunge le url caricate 
            diamicamente attraverso che sono state trovate precendetemente 
            dall'analisi dinamica
        """

        self.logger.logger.info("[Init add url dynamic ]")

        #######################################################################################################
        function_load_url = ["loadUrl"] # funzioni che caricano url in Android
        url_api_monitor = list()
        for keys in self.api_monitor_dict.keys():
            if keys in function_load_url:
                url_api_monitor = list(set().union(url_api_monitor,self.api_monitor_dict[keys]["args"]))
        url_api_monitor = filter(lambda x: x.startswith("http://") or x.startswith("https://"),url_api_monitor)

        #######################################################################################################
        # TODO mettere la funzione evaluateJavaScript o loadUrl javascript: --> come se fosse un file javascript


        #######################################################################################################
        # ora devo filtrare solo le url che sono http/https
        url_network = list()
        for keys in self.network_dict.keys():
            # TODO check
            url_list_new = list()
            for url in self.network_dict[keys]["url"]:
                # search ip
                ip = re.findall(r"[0-9]+(?:\.[0-9]+){3}",url)
                if ip != None and len(ip) > 0:
                    # change ip with host
                    # get only first element of every list --> every list are max 1 element
                    url_new = url.replace(ip[0],self.network_dict[keys]["host"][0])
                    url_list_new.append(url_new)
                else:
                    url_list_new.append(url)
            # add new url
            self.network_dict[keys]["url"] = url_list_new
            url_network = list(set().union(url_network,self.network_dict[keys]["url"]))

        #######################################################################################################
        self.url_loaded = list(set().union(self.url_loaded,url_api_monitor,url_network))
        self.all_url = list(set().union(self.all_url,self.url_loaded))
        for u in self.url_loaded:
            self.logger.logger.info("Url dynamic {0}".format(u))
        self.logger.logger.info("[End url dynamic]\n")