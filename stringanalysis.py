
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import re

class FileAnalysis:
    def __init__(self, name_file=None, content_file=None, type_file=None, contain_iframe=None, inside_apk=False, tag_to_search="iframe"):
        self.name_file = name_file
        self.content_file = content_file
        self.type_file = type_file
        self.contain_iframe = contain_iframe
        self.inside_apk = inside_apk
        self.tag_to_search = "iframe"



    @staticmethod
    def find_html_file(list_file):
        r = re.compile(".*html$")
        html_file = dict()  # solo i file .html
        list_html_file = filter(r.match,list_file)
        for temp in list_html_file:
            html_file[temp] = True # 
        return html_file

    @staticmethod
    def find_js_file(list_file):
        javascript_file = dict()
        r = re.compile(".*js$")  # solo i file .js
        list_js_file = filter(r.match,list_file)
        for temp in list_js_file:
            javascript_file[temp] = True # true that mean inside apk
        return javascript_file

    @staticmethod
    def check_file_hybrid(list_file_all, list_file_to_find):
        is_contain_file_hybrid = False
        file_hybrid = list()
        for name in list_file_all:
            for file_to_check in list_file_to_find:
                #name = name.split("/")[-1] # get last name
                if file_to_check in name:
                    is_contain_file_hybrid = True
                    file_hybrid.append(name)

        return is_contain_file_hybrid, file_hybrid

    @staticmethod
    def find_string( string_to_find, is_tag, name_file, file_read, soup, logger):
        
      
        find_iframe = False
        list_row_string = []
        list_src_iframe = []
        file_line = list()
        if  is_tag and not name_file.endswith(".js"):
            list_tag = soup.find_all(string_to_find)
            file_line = file_read.split("\n")
            for name_tag in list_tag:
                try:
                    if name_tag["src"] is not None:
                        list_src_iframe.append(name_tag["src"])
                except KeyError: 
                    # allora i file js dovrebbero fare a caso nostro, dovrei cercare l'id dell'iframe all'interno del file javascript
                    pass
                find_iframe = True
                logger.logger.info("Found this tag {0}".format(name_tag))
                list_row_string.append(name_tag)
        else:
            file_line = file_read.split("\n")
            string_regex = re.compile("\b"+string_to_find+"\b",re.IGNORECASE)
            string_regex_v2 = re.compile(string_to_find,re.IGNORECASE) # only string complete
             # only string complete
            for (counter,value) in enumerate(file_line) or re.search(string_regex_v2,value):
                if re.search(string_regex,value):
                    list_row_string.append(str(counter+1))
                    find_iframe = True
        
        # provo a vedere se esiste iframe come string all'interno
        if not find_iframe and name_file.endswith(".html"):
            string_regex = re.compile("\b"+string_to_find+"\b",re.IGNORECASE)
            string_regex_v2 = re.compile(string_to_find,re.IGNORECASE) # only string complete
            for (counter,value) in enumerate(file_line):
                if re.search(string_regex,value) or re.search(string_regex_v2,value):
                    list_row_string.append(str(counter+1))
                    find_iframe = True

        return find_iframe, list_row_string, list_src_iframe