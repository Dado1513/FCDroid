# Hybrid Inspector

Simple tool written in python that is able to:
- Identify if the apk is native or hybrid (cordova / phonegap)

- Look for strings inside passed through CLI

- If you search "iframe" able to identify frame_confusion problem

- Necessary to have in PATH the dir of apktool 

- Necessary download [retirejs](https://retirejs.github.io/retire.js/)

```
Usage: python3.6 hybrid_inspector.py -d "/home/User/dir_apk" -t -s "iframe"
```
___
Work In Progress:
- [x] Search loadUrl e string used inside
- [x] Search loadUrl e string used if assigned to a variable before (done apimonitor)
- [x] Download web page used 
- [x] log output on file using logging
- [x] controllare enableJavaScript se passa argomento true
- [x] url runtime (using dynamic analysis before) such as droidbot and get file apimonitor
- [x] whitelist url(intent/network/navigation)
- [x] check iframe in js script
- [x] identify dom xss static
- [x] use retirejs 
___
