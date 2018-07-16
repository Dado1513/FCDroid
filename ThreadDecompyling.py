#!/usr/env/bin python3
from threading import Thread
from bcolors import bcolors



class ThreadDecompyling (Thread):

    def __init__(self, myapk, logger):
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
