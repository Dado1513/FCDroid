import os
from pymongo import MongoClient


class MongoDB:
    def __init__(self):
        if 'DATABASE_URL' in os.environ:
            self.db_url = os.environ['DATABASE_URL']
            self.client = MongoClient(self.db_url, connect=False)
        else:
            self.db_url = 'mongodb://localhost:27117/db'
            self.client = MongoClient(self.db_url, connect=False)
        try:
            self.db = self.client['db']
            self.analysis_db = self.db['HybridAnalysis']
        except Exception:
            print("Unable to connect mongodb")
