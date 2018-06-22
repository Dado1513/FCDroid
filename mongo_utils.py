import os
from pymongo import MongoClient


class MongoDB:
    def __init__(self):
        if 'DATABASE_URL' in os.environ:
            self.db_url = os.environ['DATABASE_URL']
            self.client = MongoClient(self.db_url, connect=False)
        else:
            self.db_url = 'mongodb://localhost:27117/db' # conencto to mongodb inside docker
            self.client = MongoClient(self.db_url, connect=False)
        try:
            self.db = self.client['db']
            self.analysis_db = self.db['HybridAnalysis']
        except Exception:
            print("Unable to connect mongodb")

    def find_analysis(self,apk_name):
        """
            search if analysis are  yet executed
        """
        result = self.analysis_db.find_one({"name_apk":apk_name})
        return result

    def insert_analysis(self,apk,retire_local,retire_remote):
        """
            function to insert element in mongo db after scan

        """
        dict_to_insert = dict()
        dict_to_insert["name_apk"] = apk.name_only_apk
        dict_to_insert["html_file"] = list(apk.html_file.keys()) # all html file
        dict_to_insert["js_file"] = list(apk.javascript_file.keys())
        dict_to_insert["is_hybrid"] = str(apk.isHybrid)
        dict_to_insert["permission"] = apk.apk.get_permissions()
        dict_to_insert["frame_confusion_vulnerable"] = apk.vulnerable_frame_confusion()
        dict_to_insert["js_enable"] = apk.javascript_enabled
        dict_to_insert["js_interface"] = apk.javascript_interface
        dict_to_insert["url_loaded"] = apk.url_loaded
        dict_to_insert["all_url"] = apk.all_url
        dict_to_insert["file_config_hybrid"] = apk.file_hybrid
        dict_to_insert["file_origin_access"] = apk.list_origin_access
        dict_to_insert["file_without_csp"] = [key for key,value in apk.find_csp.items() if not value ]
        dict_to_insert["file_js_with_iframe"] = apk.file_js_with_iframe
        if retire_local is not None:
            dict_to_insert["retire_locale"] = retire_local 
        if retire_remote is not None:   
            dict_to_insert["retire_remote"] = retire_remote
        self.analysis_db.insert_one(dict_to_insert)

    