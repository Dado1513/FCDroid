#!/usr/env/bin python3
import glob
import logging
import os
import re
import zipfile
from threading import Thread

from bs4 import BeautifulSoup
import requests

from androguard.core.analysis.analysis import Analysis
from androguard.core.androconf import show_logging
from androguard.core.bytecodes.apk import APK
from androguard.core.bytecodes.dvm import DalvikVMFormat
from androguard.decompiler.decompiler import (DecompilerJADX,
                                              JADXDecompilerError)
from androguard.misc import AnalyzeAPK
import sys
from bcolors import bcolors
import logging



    

class ThreadDecompyling (Thread):

    def __init__(self, myapk,logger):
        Thread.__init__(self)
        self.myapk = myapk
        self.logger = logger

        self.finish = False
        self.error = False

    def run(self):
        try:

            print(bcolors.WARNING+"[*] Start Analysis"+bcolors.ENDC)
            self.logger.logger.info("Start Analysis")
            self.myapk.find_method_used()
        except Exception as e:
            print(bcolors.FAIL+"Error decompiler {0} \n".format(e)+bcolors.ENDC)
            self.logger.logger.error("Error decompiler {0} \n".format(e))
    
            self.error = True
  
        self.finish = True
