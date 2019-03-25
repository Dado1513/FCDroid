import logging


class Logger:

    def __init__(self, log_file):
        self.logger = logging.getLogger(__name__)
        level = logging.DEBUG
        self.logger.setLevel(level)
        formatter = logging.Formatter('[INTERNAL_LOG][%(asctime)s][%(levelname)s][%(funcName)s()] %(message)s')

        # handler = logging.FileHandler(log_file, mode="w")
        # handler.setLevel(level)
        consolehandle = logging.StreamHandler()
        consolehandle.setLevel(logging.ERROR)
        
        # handler.setFormatter(formatter)
        consolehandle.setFormatter(formatter)

        # self.logger.addHandler(handler)
        self.logger.addHandler(consolehandle)
        # logging.getLogger().addHandler(handler)
        # logging.getLogger().addHandler(consolehandle)
        
    def shutdown(self):
        handlers = self.logger.handlers[:]
        for handler in handlers:
            handler.close()
            self.logger.removeHandler(handler)
