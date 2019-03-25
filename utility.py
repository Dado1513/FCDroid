import subprocess
from .bcolors import bcolors
import os
import requests
import hashlib
from bs4 import BeautifulSoup



def download_page_with_wget(name_apk, url_loaded):
    """
            function to download the page loaded by the app
            using list self.url_loaded
            after this -> check if frame confusion may come from this
    """
    html_dir = "temp_html_code/html_downloaded_"+name_apk

    file_name_counter = dict()
    print(bcolors.WARNING+"\n[*] Download remote page in: "+html_dir+bcolors.ENDC)
    # download only file .js and .html

    # cmd_wget = ['wget','-nd','-nc','-T','1','-E','-r','-l','2','-t','3','-P',html_dir]
    # cmd_wget = ['wget' ,'-E', '-H' ,'-k','-T','1','-nd' ,'--accept-regex','".*\.html.*|.*\.js.*"','-N', '-r','-l','2','-P', html_dir]
    # cmd_wget = ['wget' ,'-E', '-H' ,'-k',' -K ','-T','1','-nd' ,'--accept-regex','".*\.html.*|.*\.js.*"','-N', '-r','-l','2','-P', html_dir]

    # cmd_wget = ['wget','--page-requisites','--html-extension','-nd','-E','-H','-k','-T','1','-P',html_dir]    
    cmd_wget = ["timeout","20","wget" ,"-E", "-H", "-k", "-nd", "-T" ,"1","-nc","-N", "-K","-q","-o" ,"/dev/null", "-p",'--tries=1', "-P", html_dir]

    FNULL = open(os.devnull, 'w')
    md5_file_to_url = dict()
    file_download_to_analyze = dict()
    for url in url_loaded:
        if url[-1] == "/":
            url = url[:-1]

        # print("Url to download {0}".format(url))
        url_without_parameter = url.split("?",1)[0]
        #################################################################
        name_file = url_without_parameter.split("/")[-1] 
        path_complete = os.path.join(html_dir,name_file)

        file_name_split_extension = name_file.split(".")
        if len(file_name_split_extension) == 1: # no extension
            name_file = name_file + ".html" # add .html
            path_complete = os.path.join(html_dir, name_file)
            
        m = hashlib.md5()
        m.update(name_file.encode('utf-8')) # md5 to set count same file
        md5 = m.hexdigest() 

        if not os.path.isfile(path_complete): 
            file_name_counter[md5] = 1
        else:
            if md5 not in file_name_counter.keys():
                file_name_counter[md5] = 1            
            file_name_counter[md5] = file_name_counter[md5] + 1
            
            # file_name_split_extension[0] = file_name_split_extension[0]+"_"+str(file_name_counter[md5]) 
            # if len(file_name_split_extension) > 1:
            #     name_file = file_name_split_extension[0] + "." + file_name_split_extension[1]
            # else:
            #     name_file = file_name_split_extension[0]  

        cmd_wget.append(url_without_parameter) # url senza parameter 
        subprocess.call(cmd_wget,stdout=FNULL,stderr=FNULL) # download file
        
        ####################################################################
        # save url from this md5
        m = hashlib.md5()
        # add extension  (wget if no exist attach html) o number file if exist yet             
        m.update(path_complete.encode('utf-8'))

        # print(path_complete, url_without_parameter, name_file, m.hexdigest(), url)
        md5_file_to_url[m.hexdigest()] = url 
        cmd_wget.remove(url_without_parameter)
    
    # now add all file download in this dir with extension html and js
    for root, _, files in os.walk(html_dir):
            for file_download in files:
                file_download_split = file_download.split("?",1)[0] # remove parameter 
                if file_download_split.endswith(".html") or file_download_split.endswith(".js") :
                    file_download_to_analyze[os.path.join(root,file_download)] = False 
        
    return md5_file_to_url,file_download_to_analyze

def download_page_with_requests(name_apk, url_loaded):

    html_dir = "temp_html_code/html_downloaded_"+name_apk
    os.makedirs(html_dir,exist_ok=True)
    print(bcolors.WARNING+"\n[*] Download remote page in: "+html_dir+bcolors.ENDC)
    md5_file_to_url = dict()
    file_download_to_analyze = dict()
    list_js_file = list()
    # download url page
    #######################################################################
    for url in url_loaded:
        if url[-1] == "/":
            url = url[:-1]
        url_without_parameter = url.split("?",1)[0]
        
        #################################################################
        name_file = url_without_parameter.split("/")[-1] 
        extension_file = name_file.split(".")[-1]
        if extension_file == name_file:
            # file without extension
            name_file = name_file + ".html"
        elif extension_file  in ["jar"]:
            break # no download
        path_complete = os.path.join(html_dir,name_file)
        

        r = requests.get(url, timeout=5)
        file_to_write = open(path_complete,"w")
        file_to_write.write(r.text)
        file_to_write.close()
        ###################################################################
        # save url from this md5
        m = hashlib.md5()
        # add extension  (wget if no exist attach html) o number file if exist yet             
        m.update(path_complete.encode('utf-8'))

        # print(path_complete, url_without_parameter, name_file, m.hexdigest(), url)
        md5_file_to_url[m.hexdigest()] = url 
        soup = BeautifulSoup(r.text,"lxml")
        sources = soup.findAll('script',{"src":True})
        for source in sources:
            list_js_file.append(source["src"])
    
    # from this url page donwload all script js file loaded inside
    ########################################################################
    for js in list_js_file:
        url_without_parameter = js.split("?",1)[0]
        
        #################################################################
        name_file = url_without_parameter.split("/")[-1] 
        extension_file = name_file.split(".")[-1]
        if extension_file == name_file:
            # file without extension
            name_file = name_file + ".html"
        elif extension_file not in ["html","js"]:
            break # no download
        path_complete = os.path.join(html_dir,name_file)
        

        r = requests.get(js, timeout=5)
        file_to_write = open(path_complete,"w")
        file_to_write.write(r.text)
        file_to_write.close()
        ###################################################################
        # save url from this md5
        m = hashlib.md5()
        # add extension  (wget if no exist attach html) o number file if exist yet             
        m.update(path_complete.encode('utf-8'))

        # print(path_complete, url_without_parameter, name_file, m.hexdigest(), url)
        md5_file_to_url[m.hexdigest()] = url 

    for root, _, files in os.walk(html_dir):
        for file_download in files:
            file_download_split = file_download.split("?",1)[0] # remove parameter 
            if file_download_split.endswith(".html") or file_download_split.endswith(".js") :
                file_download_to_analyze[os.path.join(root,file_download)] = False 
    
    return md5_file_to_url,file_download_to_analyze