# Hybrid Inspector

Simple tool written in python that is able to:
- Identify if the apk is native or hybrid (cordova / phonegap)

- Look for strings inside passed through CLI

- If you search "iframe" able to identify frame confusion

```
Usage: pythonAnaconda3.6 hybrid_inspector.py -d "/home/User/dir_apk" -t -s "iframe"
```
___
Work In Progress:
- [x] Search loadUrl e string used inside
- [ ] Search loadUrl e string used if assigned to a variable before
- [ ] Download web page used 
- [ ] loadUrl/EvaluateJavaScript --> containe javascript code exec
- [ ] log output on file using logging
- [ ] controllare enableJavaScript se passa argomento true
___
