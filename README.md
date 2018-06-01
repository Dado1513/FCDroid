# Hybrid Inspector

Simple tool written in python that is able to:
- Identify if the apk is native or hybrid (cordova / phonegap)

- Look for strings inside passed through CLI

- If you search "iframe" able to identify frame confusion

- Necessary to have in PATH the dir of apktool
```
Usage: pythonAnaconda3.6 hybrid_inspector.py -d "/home/User/dir_apk" -t -s "iframe"
```
___
Work In Progress:
- [ ] search method used using smali code invece che androguard
- [x] Search loadUrl e string used inside
- [ ] Search loadUrl e string used if assigned to a variable before (done apimonitor)
- [x] Download web page used 
- [ ] loadUrl/EvaluateJavaScript --> containe javascript code exec (apimonitor)
- [x] log output on file using logging
- [x] controllare enableJavaScript se passa argomento true
- [x] url runtime (using dynamic analysis before) such as droidbot and get file apimonitor
- [ ] whitelist url(intent/network/navigation)
- [ ] check iframe in js script
___
