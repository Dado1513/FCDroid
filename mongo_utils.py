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
        result = self.client.find_one({"name_apk":apk_name})
        return result

    def insert_analysis(self,apk,retire_local,retire_remote):
        """
            function to insert element in mongo db after scan

        """
        dict_to_insert = dict()
        dict_to_insert["html_file"] = list(apk.html_file.keys()) # all html file
        dict_to_insert["js_file"] = list(apk.javascript_file.keys())
        dict_to_insert["is_hybrid"] = str(apk.is_hybrid)
        dict_to_insert["permission"] = apk.get_permissions()