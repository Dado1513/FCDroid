#!/usr/env/bin python3
import glob
import logging
import os
import re
import zipfile
from bs4 import BeautifulSoup
import requests
from androguard.core.analysis.analysis import Analysis
from androguard.core.androconf import show_logging
from androguard.core.bytecodes.apk import APK
from androguard.core.bytecodes.dvm import DalvikVMFormat
from androguard.core.bytecodes.apk import FileNotPresent
from androguard.core.bytecodes.axml import AXMLPrinter
from androguard.decompiler.decompiler import (DecompilerJADX,
                                              JADXDecompilerError)
from androguard.misc import AnalyzeAPK
from bcolors import bcolors
import xml.etree.ElementTree as ET

show_logging(level=logging.CRITICAL)


class MyAPK:
    
    def __init__(self, name_file, conf, file_log, tag, string_to_find, logger, api_monitor_dict=None, network_dict=None):
        
        self.name_apk = name_file
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
        self.html_file = dict()  # html file inside apk
        self.zip = zipfile.ZipFile(self.name_apk) # get zip object from apk
        self.list_file = self.zip.namelist()  # tutti i file all'interno
        self.__find_html_file()  # call function to full html_file
        self.file_log = file_log  # name to file log
        self.javascript_enabled = False
        self.internet_enabled = False
        self.file_vulnerable_frame_confusion = list()
        self.isHybrid = None
        self.method = dict()  # dict indexes with name method and get encoded methods where function was called
        self.all_url = list()  # all url in the apk
        self.file_download_to_analyze = dict()
        self.search_tag = tag
        self.name_to_url = dict()  # dict with indexes with name and get url remote
        self.file_config_hybrid = None
        self.list_origin_access = None
        self.logger = logger
        self.api_monitor_dict = api_monitor_dict
        self.network_dict = network_dict        
        
    
    def __find_html_file(self):
        
        r = re.compile(".*html$")  # solo i file .html
        list_html_file = filter(r.match,self.list_file)
        for temp in list_html_file:
            self.html_file[temp] = True 
        
    def read(self, filename, binary=True):
        with open(filename, 'rb' if binary else 'r') as f:
            return f.read()

    def is_hybird(self):
        """
            function to check se apk is hybrid,
            1) if contain file from conf.json (cordova/plugin/phonegap/config)
            2) if present permission internet (inutile)
        """
        if self.isHybrid is None:
            list_file_to_find = self.conf["file_to_check"]
            list_permission_to_find = self.conf["permissions_to_check"]

            for name in self.list_file:
                for file_to_check in list_file_to_find:
                    if file_to_check in name:            
                        self.is_contain_file_hybrid = True  # almeno un file
                        break
            # Add se trova il file config.xml all'interno allora lo memorizzo:

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

            self.isHybrid = self.is_contain_permission and self.is_contain_file_hybrid
            try:
                if self.isHybrid:
                    # non sempre funziona a volte bisogna decompilare l'app manualmente per ottenere questo file
                    # TODO 
                    axml = AXMLPrinter(self.apk.get_file("res/xml/config.xml"))
                    self.file_config_hybrid = axml.get_xml()
                    # parsing file config
                    self.check_whitelist()
            except FileNotPresent as e:
                print(bcolors.FAIL+"File config.xml not found, it is necessary to decompile the application first"+bcolors.ENDC)
                self.logger.logger.error("[ERROR file config.xmls] {0} \n".format(e))

        return self.isHybrid 

    def check_whitelist(self):
        """
            function that obtain access origin from file 
            config.xml
        """
        # TODO add

        # get xml_object ElementTree 
        if self.file_config_hybrid is not None and self.isHybrid:
            self.list_origin_access = list()
            root = ET.fromstring(self.file_config_hybrid)
            
            xmlns = "{http://www.w3.org/ns/widgets}" # default namespace
            # xmlns = root.tag.split("}")[0]
            # xmlns = xmlns + "}" # add delimeter
            # print(root.attrib)
            for child in root.findall(xmlns+"access"):
                # print( child.tag, child.attrib.get("origin"))
                self.list_origin_access.append(child.attrib.get("origin"))

            self.logger.logger.info("[INIT ACCESS ORIGIN LIST]")
            for value in self.list_origin_access:
                self.logger.logger.info("origin: %s",value)
            self.logger.logger.info("[END ACCESS ORIGIN LIST]\n")

    def find_string(self,  file_to_search, remote=False, debug=False):
        """
            find string inside file of apk(html,xml,ecc..) (not yet decompiled)
        """
        print("\n")
        # TODO aggiungere opzione debug
        debug = True

        if remote:
            self.logger.logger.info("[START REMOTE FILE ANALYZE]")
        else:
            self.logger.logger.info("[START FILE ANALYZE]")
        for file_to_inspect, insideAPK in file_to_search.items():
            if not remote and debug:
                print("File: " +file_to_inspect)
                self.logger.logger.info("File: "+file_to_inspect)
            else:
                if debug:
                    print("Remote File in: " +file_to_inspect)
                    print("URL: "+self.name_to_url[file_to_inspect])
                    self.logger.logger.info("Remote File in: %s",file_to_inspect)
                    self.logger.logger.info("URL: %s",self.name_to_url[file_to_inspect])
                
            if insideAPK:
                data = self.zip.open(file_to_inspect)
            else:
                data = open(file_to_inspect,"r")
                
            file_read = str(data.read())
            soup = BeautifulSoup(file_read,'lxml')
            find_iframe = False
            list_row_string = []

            try:
                if self.search_tag: 
                    list_tag = soup.findAll(self.string_to_find)
                    file_line = file_read.split("\n")
                    for name_tag in list_tag:
                        find_iframe = True
                        list_row_string.append(name_tag)
                
                else:
                    file_line = file_read.split("\n")
                    for (counter,value) in enumerate(file_line):
                        if self.string_to_find in value:
                            list_row_string.append(str(counter+1))
                            find_iframe = True

                if find_iframe and self.string_to_find == "iframe":
                    self.dict_file_with_string[file_to_inspect] = list_row_string
                    
                    if not self.search_tag:
                        print(bcolors.FAIL+"Found "+self.string_to_find+" in line "+str(list_row_string)+bcolors.ENDC)  
                        self.logger.logger.info("Found tsg %s file %s in line %s",self.string_to_find,file_to_inspect,str(list_row_string)) 
                    else:
                        print(bcolors.FAIL+"Found tag "+self.string_to_find +",  "+str(len(list_row_string)) +" times "+bcolors.ENDC)
                        self.logger.logger.info("Found in file %s tag %s , %s times",file_to_inspect,self.string_to_find,str(len(list_row_string)) )
                    
                    # TODO aggiungere il content e fare conclusioni su di esso
                    find_csp  = soup.find("meta",{"http-equiv":"Content-Security-Policy"})
                    if find_csp is not None:
                        print(bcolors.OKGREEN+"Find CSP with content: [" +find_csp["content"]+"]"+bcolors.ENDC)
                        self.logger.logger.info("Find CSP with content: [" +find_csp["content"]+"]")
                        self.find_csp[file_to_inspect] = True
                    else:
                        print(bcolors.FAIL+"No CSP found!"+bcolors.ENDC)
                        self.logger.logger.info("No CSP found!")
                        self.find_csp[file_to_inspect] = False
                else:
                    print(bcolors.OKGREEN+"No "+self.string_to_find+" in "+file_to_inspect+bcolors.ENDC)
                    self.logger.logger.info("No "+self.string_to_find+" in "+file_to_inspect)
                
                print()

            except zipfile.BadZipfile:
                continue
            except ValueError:
                continue
        self.logger.logger.info("[END ANALYZE FILE]\n")
        return None

    def find_method_used(self):
        """
            funzione per ricercare i metodi che sono usati 
            all'interno dell'apk
        """
        used_jadx = True
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

        else:
            # return apk, list dex , object analysis
            apk, self.dalviks_format, self.analysis_object = AnalyzeAPK(self.name_apk)
            
            # self.dalvik_format = DalvikVMFormat(self.apk)
            # Create Analysis Object
            # self.analysis_object = Analysis(self.dalvik_format)
            # se decompilyng = androguard.misc.Run_Decompyler(dalvik_fromat, dx (VMAnalysis object),
            # decompyler_name (dad,dex2jar,ded))
            # method_analys = list()
            for method_analys in self.analysis_object.get_methods():
                method_name = method_analys.get_method().get_name()
                # from method_name get list dove esso viene chiamato
                self.method[method_name] = list(method_analys.get_xref_from())
            
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

                    except (TypeError, AttributeError) as e:
                        continue

            self.logger.logger.info("[JavaScript enabled: "+str(self.javascript_enabled)+"]\n")
        except Exception:
            self.logger.logger.error("File conf.json without method setJavaScriptEnabled\n")

        try:
            self.logger.logger.info("[Add interface WebView: "+str(method_present["addJavascriptInterface"])+"]\n")
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
        list_string_analysis = self.analysis_object.find_strings(url_re) #--> gen object
        # contain all url in apk
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
                # print(type(value))
                try:
                    if value[1] is not None:
                        encoded_method = value[1]
                        # split the instruction in a list
                        source_code = self.get_list_source_code(encoded_method)
                        self.all_url.append(key)
                        if self.check_metod_used_value(source_code,"loadUrl",key):
                            self.url_loaded.append(key)
                        
                except (TypeError, AttributeError) as e:
                    continue
        # debug part
        
        if len(self.url_loaded) > 0:
            #print(self.url_loaded)
            self.logger.logger.info("[START URL LOADED INSIDE LOAD FUNCTION]")
            self.logger.logger.info("".join(str(i)+"\n" for i in self.url_loaded))
            self.logger.logger.info("[END URL LOADED INSIDE LOAD FUNCTION]")
            self.download_page_loaded()
            self.find_string(self.file_download_to_analyze, remote=True)
        if len(self.all_url) > 0 :
            self.logger.logger.info("[START ALL URL INSIDE APK]")
            self.logger.logger.info("".join(str(i)+"\n" for i in self.all_url))
            self.logger.logger.info("[END ALL URL INSIDE APK]")
            
        #    print(self.all_url)

    def get_list_source_code(self, encoded_method):
        """
            from object encoded_method obtain source code list
        """
        
        source_code = encoded_method.get_source().replace("\n", "")
        source_code = source_code.replace(" ", "")
        source_code = source_code.split(";")
        return source_code

    def download_page_loaded(self):
        """
            function to download the page loaded by the app
            using list self.url_loaded
            after this -> check if frame confusion may come from this
        """
        name_only_apk = self.name_apk.split("/")[-1].split(".")[0]
        
        html_dir = "temp/html_downloaded_"+name_only_apk
        if not os.path.exists(html_dir):
            os.makedirs(html_dir)
        print(bcolors.WARNING+"[*] Download remote page in: "+html_dir+bcolors.ENDC)
        
        for url in self.url_loaded:
            try:
                r = requests.get(url,allow_redirects=True)
                name_file = url.split("/")[-1]
                path_complete = html_dir+"/"+name_file
                open(path_complete,"wb").write(r.content)
                self.name_to_url[path_complete] = url 
                self.file_download_to_analyze[path_complete] = False
            except requests.exceptions.InvalidSchema:
                url = "http://{0}".format(url)
                r = requests.get(url,allow_redirects=True)
                name_file = url.split("/")[-1]
                path_complete = html_dir+"/"+name_file
                open(path_complete,"wb").write(r.content)
                self.name_to_url[path_complete] = url 
                self.file_download_to_analyze[path_complete] = False

    # invece che valore magari che venga passato una variabile come valore
    def check_metod_used_value(self,list_source_code,metodo,value):
        """
           funzione che prende in ingresso un metodo
           e il valore, e controlla se in quel metodo viene passato quel 
           valore
        """
        # ToDo solo se in loadUrl è passata la stringa non il nome della variabile
        # il quale sarebbe da aggiungere
        r = re.compile(metodo) # per ora solo load_url
        list_new = filter(r.findall,list_source_code)
        for line_finded in list_new:
            if value in line_finded:
                # print("Used ("+url_to_find+"); "+line_finded)
                return True
            # else:
                #p rint("Load url in this function but not url string inside: "+url_to_find)
        return False
        
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
        
        return ("iframe" in self.string_to_find and 
                self.check_method_conf()  and 
                len(self.dict_file_with_string) > 0 and
                self.is_contain_permission and
                not csp_in_file_iframe)
    
    def add_url_dynamic(self):
        """
            function that aggiunge le url caricate 
            diamicamente attraverso che sono state trovate precendetemente 
            dall'analisi dinamica
        """

        self.logger.logger.info("Init add url dynamic analysis")
        function_load_url = ["loadUrl"] # funzioni che caricano url in Android
        url_api_monitor = list()
        for keys in self.api_monitor_dict.keys():
            if keys in function_load_url:
                url_api_monitor = list(set().union(url_api_monitor,self.api_monitor_dict[keys]["args"]))
        url_api_monitor = filter(lambda x: x.startswith("http://") or x.startswith("https://"),url_api_monitor)
        # ora devo filtrare solo le url che sono http/https
        url_network = list()
        for keys in self.network_dict.keys():
            url_network = list(set().union(url_network,self.network_dict[keys]["url"]))
        
        self.url_loaded = list(set().union(self.url_loaded,url_api_monitor,url_network))
        self.all_url = list(set().union(self.all_url,self.url_loaded))
        self.logger.logger.info("".join(str(i)+"\n" for i in self.url_loaded))
        self.logger.logger.info("End, url dynamic analysis added")