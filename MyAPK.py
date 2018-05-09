import glob
import logging
import os
import re
import zipfile
from threading import Thread

from bs4 import BeautifulSoup

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
        # file che contengono la string  
        self.dict_file_with_string = dict()
        # stringa da cercare
        self.string_to_find = None
        # se contiene i permessi
        self.is_contain_permission = False
        self.url_inside = list()
        # se contiene i file ibridi
        self.is_contain_file_hybrid = False
        # se le pagine html con iframe contengono CSP
        self.find_csp = dict()
        # se contiene i metodi all'interno del file conf.json
        self.is_contains_all_methods = False
        #self.raw = self.read(name_file)
        #self.zip = zipfile.ZipFile(StringIO(self.raw),'r');
        self.zip = zipfile.ZipFile(self.name_apk)
        # tutti i file all'interno
        self.list_file = self.zip.namelist()
        # solo i file .html
        r = re.compile(".*html$")
        self.html_file = filter(r.match,self.list_file)
        #
        self.file_vulnerable_frame_confusion = list()
        self.isHybrd = None
        self.method = list()

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
            

    def find_string(self,string_to_find,tag=False):
        """
            find string inside file of apk(html,xml,ecc..) (not yet decompiled)
        """
        # search string 
        self.string_to_find = string_to_find
        #print()
        # cerco solo nei file con estensione html
        for file_to_inspect in self.html_file:
            print("File: " +file_to_inspect)
            data = self.zip.open(file_to_inspect)
            file_read = str(data.read())
            soup = BeautifulSoup(file_read,'lxml')
            find_iframe = False
            list_row_string = []

            try:
                # se devo cercare il tag
                if tag:
                 
                    list_tag = soup.findAll(string_to_find)
                    file_line = file_read.split("\n")
                    for name_tag in list_tag:
                        #print("Founded "+string_to_find+" tag in : "+file_to_inspect)  
                        find_iframe = True
                        list_row_string.append(name_tag)
                
                # se devo cercare la stringa
                else:
                    file_line = file_read.split("\n")
                    # find Content-Security-Policy
                    for (counter,value) in enumerate(file_line):
                        if string_to_find in value:
                            list_row_string.append(str(counter+1))
                            #print("Founded "+string_to_find+" in line ["+str(counter+1)+"] : "+file_to_inspect)   
                            find_iframe = True

                # se l'ho trovato e la stringa era iframe
                if find_iframe and self.string_to_find == "iframe":
                    # aggiungo il file con l'iframe all'interno
                    self.dict_file_with_string[file_to_inspect] = list_row_string
                    if not tag:
                    
                        print(bcolors.FAIL+"Found "+string_to_find+" in line "+str(list_row_string)+bcolors.ENDC)   
                    
                    else:
                    
                        print(bcolors.FAIL+"Found tag "+string_to_find +",  "+str(len(list_row_string)) +" times "+bcolors.ENDC)
                    # cerco CSP
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
            #_ , self.dalviks_format, self.analysis_object = AnalyzeAPK(self.name_apk)
            self.dalvik_format = DalvikVMFormat(self.apk)
            # Create Analysis Object
            self.analysis_object = Analysis(self.dalvik_format)

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

    def check_method(self):
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
        url_re = re.compile(r'\b(([\w-]+://?|www[.])[^\s()<>]+(?:\([\w\d]+\)|([^[:punct:]\s]|/)))')
        list_string = self.analysis_object.find_strings(url_re)
        # all string
        #list_string = self.analysis_object.get_strings()
        for m in list_string:          
            self.url_inside.append(m.get_value())
        #print(self.url_inside)
            

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
                self.check_method  and 
                len(self.dict_file_with_string) > 0 and
                self.is_contain_permission and
                not csp_in_file_iframe)
