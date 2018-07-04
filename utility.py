import subprocess
from bcolors import bcolors
import os

def download_page_with_wget(name_apk, url_loaded):
    """
            function to download the page loaded by the app
            using list self.url_loaded
            after this -> check if frame confusion may come from this
    """
    html_dir = "temp_html_code/html_downloaded_"+name_apk
    print(bcolors.WARNING+"\n[*] Download remote page in: "+html_dir+bcolors.ENDC)
    cmd_wget = ['wget' ,'-E', '-H' ,'-k',' -K ','-T','1','-nd' ,'-N', '-p','-P', html_dir]
    FNULL = open(os.devnull, 'w')
    name_to_url = dict()
    file_download_to_analyze = dict()
    for url in url_loaded:
        if url[-1] == "/":
            url = url[:-1]    
        cmd_wget.append(url)
        subprocess.call(cmd_wget,stdout=FNULL,stderr=FNULL)
        name_file = url.split("/")[-1]
        path_complete = html_dir+"/"+name_file
        name_to_url[path_complete] = url 
        # self.file_download_to_analyze[path_complete] = False
        cmd_wget.remove(url)

    # now add all file download in this dir with extension html and js
    for root, _, files in os.walk(html_dir):
            for file_download in files:
                if file_download.endswith(".html") or file_download.endswith(".js"):
                    file_download_to_analyze[os.path.join(root,file_download)] = False
        
    return name_to_url,file_download_to_analyze