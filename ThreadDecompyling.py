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

from bcolors import bcolors

class ThreadDecompyling (Thread):

    def __init__(self, myapk):
        Thread.__init__(self)
        self.myapk = myapk
        self.finish = False
        self.error = False

    def run(self):
        try:

            print(bcolors.WARNING+"[*] Start decompilyng"+bcolors.ENDC)
            self.myapk.find_method_used()
        except Exception:
            print(bcolors.FAIL+"Error jadx decompiler"+bcolors.ENDC+"\n")
            self.error = True
        self.finish = True
