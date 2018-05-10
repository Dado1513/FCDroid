import glob
import logging
import os
import re
import zipfile
from threading import Thread

from bs4 import BeautifulSoup
import urllib

from androguard.core.analysis.analysis import Analysis
from androguard.core.androconf import show_logging
from androguard.core.bytecodes.apk import APK
from androguard.core.bytecodes.dvm import DalvikVMFormat
from androguard.decompiler.decompiler import (DecompilerJADX,
                                              JADXDecompilerError)
from androguard.misc import AnalyzeAPK

show_logging(level=logging.CRITICAL)

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class ThreadDecompyling (Thread):

    def __init__(self, myapk):
        Thread.__init__(self)
        self.myapk = myapk
        self.finish = False

    def run(self):
        try:

            print(bcolors.WARNING+"[*] Start decompilyng"+bcolors.ENDC)
            self.myapk.find_method_used()
        except JADXDecompilerError:
            print(bcolors.FAIL+"Error jadx decompiler"+bcolors.ENDC+"\n")
        self.finish = True

class MyAPK:
    
    def __init__(self, name_file,conf):
        self.name_apk = name_file
        self.conf = conf
        self.apk = APK(name_file)
        self.dalviks_format = None
        self.analysis_object = None
        self.dict_file_with_string = dict()  # file che contengono la stringa ricercata
        self.string_to_find = None # stringa da cercare
        
        self.is_contain_permission = False # se contiene i permessi del file conf
        self.url_loaded = list() # list url that has been loaded 
        self.is_contain_file_hybrid = False # se contiene i file ibridi --> probabilmente app ibrida
        self.find_csp = dict() # pagine_html con iframe se contengono csp [True o False]
        self.is_contains_all_methods = False # se contiene i metodi all'interno del file conf.json
        self.html_file = dict()
        self.zip = zipfile.ZipFile(self.name_apk) # get zip object from apk
        self.list_file = self.zip.namelist()# tutti i file all'interno
        self.__find_html_file()

        self.file_vulnerable_frame_confusion = list()
        self.isHybrd = None
        self.method = list()
    
    def __find_html_file(self):
        
        r = re.compile(".*html$") # solo i file .html
        list_html_file = filter(r.match,self.list_file)
        for temp in list_html_file:
            self.html_file[temp] = True 
        
    def read(self,filename, binary=True):
        with open(filename, 'rb' if binary else 'r') as f:
            return f.read()


    def is_hybird(self):
        if self.isHybrd is None:
            list_file_to_find = self.conf["file_to_check"]
            list_permission_to_find = self.conf["permissions_to_check"]

            for name in self.list_file:
                for file_to_check in list_file_to_find:
                    if file_to_check in name:            
                        self.is_contain_file_hybrid = True # almeno un file
                        break

            permission_find = list()       
            for permission_to_check in list_permission_to_find:
                if permission_to_check in self.apk.get_permissions():
                    permission_find.append(True) # contenere tutti i permessi                    
                    #print(permission_to_check)
            self.is_contain_permission = len(permission_find) == len(list_permission_to_find)

            self.isHybrd = self.is_contain_permission and self.is_contain_file_hybrid
        
        return self.isHybrd 
            

    def find_string(self, string_to_find, tag=False):
        """
            find string inside file of apk(html,xml,ecc..) (not yet decompiled)
        """
        self.string_to_find = string_to_find
        for file_to_inspect, insideAPK in self.html_file.items():
            print("File: " +file_to_inspect)
            if insideAPK:
                data = self.zip.open(file_to_inspect)
            else:
                data = file(file_to_inspect,"r")
                
            file_read = str(data.read())
            soup = BeautifulSoup(file_read,'lxml')
            find_iframe = False
            list_row_string = []

            try:
                if tag: 
                    list_tag = soup.findAll(string_to_find)
                    file_line = file_read.split("\n")
                    for name_tag in list_tag:
                        find_iframe = True
                        list_row_string.append(name_tag)
                
                else:
                    file_line = file_read.split("\n")
                    for (counter,value) in enumerate(file_line):
                        if string_to_find in value:
                            list_row_string.append(str(counter+1))
                            find_iframe = True

                if find_iframe and self.string_to_find == "iframe":
                    self.dict_file_with_string[file_to_inspect] = list_row_string
                    if not tag:
                        print(bcolors.FAIL+"Found "+string_to_find+" in line "+str(list_row_string)+bcolors.ENDC)   
                    else:
                        print(bcolors.FAIL+"Found tag "+string_to_find +",  "+str(len(list_row_string)) +" times "+bcolors.ENDC)
                    find_csp  = soup.find("meta",{"http-equiv":"Content-Security-Policy"})
                    if find_csp is not None:
                        print(bcolors.OKGREEN+"Find CSP with content: [" +find_csp["content"]+"]"+bcolors.ENDC)
                        self.find_csp[file_to_inspect] = True
                    else:
                        print(bcolors.FAIL+"No CSP found!"+bcolors.ENDC)
                        self.find_csp[file_to_inspect] = False
                else:
                    print(bcolors.OKGREEN+"No "+string_to_find+" in "+file_to_inspect+bcolors.ENDC)
                
                print()

            except zipfile.BadZipfile:
                continue
            except ValueError:
                continue
        return None

    def find_method_used(self):
        """
            funzione per ricercare i metodi che sono usati 
            all'interno dell'apk
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
            decompiler = DecompilerJADX(self.dalvik_format, self.analysis_object)

            # propagate decompiler and analysis back to DalvikVMFormat
            self.dalvik_format.set_decompiler(decompiler)
            self.dalvik_format.set_vmanalysis(self.analysis_object)

            # Now you can do stuff like:
            self.method = self.analysis_object.get_methods()

        else:
            # return apk, list dex , object analysis
            _ , self.dalviks_format, self.analysis_object = AnalyzeAPK(self.name_apk)
            #self.dalvik_format = DalvikVMFormat(self.apk)
            # Create Analysis Object
            #self.analysis_object = Analysis(self.dalvik_format)

            method_analys = list()
            for method_encoded in self.analysis_object.get_methods():
                method_analys.append(method_encoded.get_method().get_name())
            self.method = list(set(self.method).union(method_analys))
            
            # save method used
            #method_file = open("method.txt","w")
            #for m in self.method:
            #    method_file.write(m + "\n")
            #dave/Developer/ToolTesi/inspectHybridApkmethod_file.writelines(self.method)
            #print("addJavascriptInterface" in self.method)

    def check_method_conf(self):
        """
            function to check se one method is used inside apk
        """
        method_present = list()

        method_to_find = self.conf["method_to_check"]
        for mf in method_to_find:
            for mapk in self.method:
                if mf in mapk:
                    print(mf)
                    method_present.append(True)
        self.is_contains_all_methods = len(method_present) == len(method_to_find)
        return self.is_contains_all_methods

    def find_url_in_apk(self):
        """
            find all url/uri inside apk
        """
        # function to get all url/uri used inside apk
        # url regularp expression
        #url_re = "(http:\/\/|https:\/\/|file:\/\/\/)?[-a-zA-Z0-9@:%._\+~#=]\.[a-z]([-a-zA-Z0-9@:%_\+.~#?&//=]*)"
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
                #class_analysis = value[0]
                encoded_method = value[1]
                # volendo c'è il metodo get_instructions
                source_code = encoded_method.get_source().replace("\n","")
                source_code = source_code.replace(" ","")
                source_code = source_code.split(";")
                if self.check_load_url_used_string(source_code,key):
                    self.url_loaded.append(key)
        #print(self.url_loaded)

    def check_load_url_used_string(self,list_source_code,url_to_find):
        # ToDo solo se in loadUrl è passata la stringa non il nome della variabile
        # il quale sarebbe da aggiungere
        r = re.compile("loadUrl") # per ora solo load_url
        list_new = filter(r.findall,list_source_code)
        for line_finded in list_new:
            if url_to_find in line_finded:
                #print("Used ("+url_to_find+"); "+line_finded)
                return True
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
                self.check_method_conf  and 
                len(self.dict_file_with_string) > 0 and
                self.is_contain_permission and
                not csp_in_file_iframe)
