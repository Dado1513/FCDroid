import os
import json
from pymongo import MongoClient
import pymongo
class MongoDB:
    def __init__(self,logger):
        self.is_available = True
        self.logger = logger
        try:

            if 'DATABASE_URL' in os.environ:
                self.db_url = os.environ['DATABASE_URL']
            else:
                self.db_url = 'mongodb://localhost:27117/db' # conencto to mongodb inside docker
            
            max_delay = 5000
            self.client = MongoClient(self.db_url, connect=False, serverSelectionTimeoutMS=max_delay)
            self.client.server_info()
            self.db = self.client['db']
            self.analysis_db = self.db['HybridAnalysis']
        
        except pymongo.errors.ServerSelectionTimeoutError as err:
            self.logger.logger.warning("Unable to connect mongodb")
            self.is_available = False


    def find_analysis(self,apk_name):
        """
            search if analysis are  yet executed
        """
        result = self.analysis_db.find_one({"name_apk":apk_name})
        return result

    def delete_analysis(self, apk_name):
        """
            delete result apk_name
        """
        try:
            self.analysis_db.delete_one({"name_apk":apk_name})
            self.logger.logger.info("Success delete {0}".format(apk_name))
        except Exception as e:
            self.logger.logger.error("Unable delete {0} with {1}".format(apk_name,e))

    def find_all_results(self):
        """
            find all results
        """
        result =  self.analysis_db.find({})
        return result

    def insert_analysis(self,apk,retire_local,retire_remote,file_xss_vuln,logger, execution_time):
        """
            function to insert element in mongo db after scan

        """
        logger.logger.info("Insert document in collection db")
        dict_to_insert = dict()
        
        dict_to_insert['md5'] = apk.name_only_apk
        dict_to_insert['name_apk'] = apk.package_name
        dict_to_insert['html_file'] = list(apk.html_file.keys()) # all html file
        dict_to_insert['js_file'] = list(apk.javascript_file.keys())
        dict_to_insert['is_hybrid'] = str(apk.isHybrid)
        dict_to_insert['permission'] = apk.apk.get_permissions()
        dict_to_insert['frame_confusion_vulnerable'] = apk.is_vulnerable_frame_confusion
        dict_to_insert['js_enable'] = apk.javascript_enabled
        dict_to_insert['js_interface'] = apk.javascript_interface
        dict_to_insert['url_loaded'] = apk.url_loaded
        dict_to_insert['all_url'] = apk.all_url
        dict_to_insert['file_config_hybrid'] = apk.file_hybrid
        dict_to_insert['file_origin_access'] = apk.list_origin_access
        dict_to_insert['file_without_csp'] = [key for key,value in apk.find_csp.items() if not value ]
        dict_to_insert['file_with_string_iframe'] = apk.file_with_string_iframe
        dict_to_insert['dynamic_js_enable'] = apk.dynamic_javascript_enabled
        dict_to_insert['dynamic_js_interface'] = apk.dynamic_javascript_interface
        dict_to_insert['execution_time'] = execution_time   
        if type(apk.load_url_dynamic) is list:
            dict_to_insert['load_url_dynamic'] = apk.load_url_dynamic 

        if len(apk.url_dynamic) > 0:
            dict_to_insert['url_dynamic'] = apk.url_dynamic

        if len(file_xss_vuln) > 0:
            dict_to_insert['file_xss_vuln'] = file_xss_vuln
        
        dict_to_insert['http_connection'] = apk.http_connection
        dict_to_insert['http_connection_loadUrl'] = apk.http_connection_static

        if retire_local is not None:
            dict_to_insert['retire_locale'] = retire_local 
        if retire_remote is not None:   
            dict_to_insert['retire_remote'] = retire_remote
        try:
            if not os.path.isdir("json"):
                os.makedirs("json")
            name_file_json = "json/"+apk.name_apk.split("/")[-1]+".json"
            json_dict = json.dumps(dict_to_insert)
            with open(name_file_json, 'w') as outfile:
                json.dump(json_dict, outfile)
        except TypeError:
            pass

        self.analysis_db.insert_one(dict_to_insert)
        self.logger.logger.info("Success insert")
    
        
        