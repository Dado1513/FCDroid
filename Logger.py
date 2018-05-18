import logging


class Logger:

    def __init__(self, log_file):
        self.logger = logging.getLogger(__name__)
        level = logging.DEBUG
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        handler = logging.FileHandler(log_file,mode="w")
        handler.setFormatter(formatter)
        handler.setLevel(level)

        self.logger.addHandler(handler)
        consolehandle = logging.StreamHandler()
        consolehandle.setLevel(logging.ERROR)
        self.logger.addHandler(consolehandle)

    def shutdown(self):
        handlers = self.logger.handlers[:]
        for handler in handlers:
            handler.close()
            self.logger.removeHandler(handler)