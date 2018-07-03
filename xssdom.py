
import re

SOURCES_RE = re.compile("""/(location\s*[\[.])|([.\[]\s*["']?\s*(arguments|dialogArguments|innerHTML|write(ln)?|open(Dialog)?|showModalDialog|cookie|URL|documentURI|baseURI|referrer|name|opener|parent|top|content|self|frames)\W)|(localStorage|sessionStorage|Database)/""")
SINKS_RE = re.compile("""/((src|href|data|location|code|value|action)\s*["'\]]*\s*\+?\s*=)|((replace|assign|navigate|getResponseHeader|open(Dialog)?|showModalDialog|eval|evaluate|execCommand|execScript|setTimeout|setInterval)\s*["'\]]*\s*\()/""")
# try to add outerHTML
# jQuery like html|append|after|before|replaceAll|replaceWith|
class Page:
    def __init__(self, name_file, source=None):
        self.name_file = name_file
        self.source_code = source if source != None else open(name_file,"r").read()
        self.sink = []
        self.source = []

    def add_sink(self,k,grp):
        sink = (k,grp)
        self.sink.append(sink)

    
    def add_source(self,k,grp):
        source = (k,grp)
        self.source.append(source)
        
    def analyze_page(self):

    
        for k, line in enumerate(self.source_code.split("\n")):
            for pattern in re.finditer(SOURCES_RE, line):
                for grp in pattern.groups():
                    if grp is None: continue
                    self.add_source(k, grp) 
                    #print "[Line: %s] Possible Source: %s" % (k, grp)
            for pattern in re.finditer(SINKS_RE, line):
                for grp in pattern.groups():
                    if grp is None: continue
                    self.add_sink(k, grp) 