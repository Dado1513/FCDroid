import subprocess
from bcolors import bcolors
from urllib.parse import urlparse
import os
import hashlib


def download_page_with_wget(name_apk, url_loaded):
    """
            function to download the page loaded by the app
            using list self.url_loaded
            after this -> check if frame confusion may come from this
    """
    html_dir = "temp_html_code/html_downloaded_"+name_apk

    file_name_counter = dict()
    print(bcolors.WARNING+"\n[*] Download remote page in: "+html_dir+bcolors.ENDC)
    cmd_wget = ['wget' ,'-E', '-H' ,'-k',' -K ','-T','1','-nd' ,'-N', '-p','-P', html_dir]
    # cmd_wget = ['wget' ,'-E', '-H' ,'-k',' -K ','-T','1','-nd' ,'-N', '-p','-P', html_dir, "-O"]

    FNULL = open(os.devnull, 'w')
    md5_file_to_url = dict()
    file_download_to_analyze = dict()
    for url in url_loaded:
        url_parse = urlparse(url)
        if url[-1] == "/":
            url = url[:-1]
        url_without_parameter = url.split("?",1)[0]
        #################################################################
        name_file = url.split("/")[-1] 
        file_name = os.path.basename(url_parse.path)
        path_complete = os.path.join(html_dir,file_name)

        m = hashlib.md5()
        m.update(file_name.encode('utf-8'))
        md5 = m.hexdigest() 

        if not os.path.isfile(path_complete): 
            file_name_counter[md5] = 1
        else:
            file_name_split_extension = file_name.split(".")
            if md5 not in file_name_counter.keys():
                file_name_counter[md5] = 1
                # print("Strano non dovrebbe accadere, {0} {1}".format(file_name,md5))
            
            file_name_counter[md5] = file_name_counter[md5] + 1
            file_name_split_extension[0] = file_name_split_extension[0]+"_"+str(file_name_counter[md5]) 
            if len(file_name_split_extension) > 1:
                file_name = file_name_split_extension[0] + "." + file_name_split_extension[1]
            else:
                file_name = file_name_split_extension[0]
        
        # append file to save file
        cmd_wget.append(url_without_parameter)
        subprocess.call(cmd_wget,stdout=FNULL,stderr=FNULL) # download file
        
        ####################################################################
        # save url from this md5
        m = hashlib.md5()
        m.update(path_complete.encode('utf-8')  )
        md5_file_to_url[m.hexdigest()] = url 
        cmd_wget.remove(url_without_parameter)
        # cmd_wget.remove(file_name)
    # now add all file download in this dir with extension html and js
    for root, _, files in os.walk(html_dir):
            for file_download in files:
                if file_download.endswith(".html") or file_download.endswith(".js"):
                    file_download_to_analyze[os.path.join(root,file_download)] = False 
        
    return md5_file_to_url,file_download_to_analyze