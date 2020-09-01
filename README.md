# FCDroid

**FCDroid** (**F**rame **C**onfusion An**droid**) is a tool to detect automatically the **Frame Confusion** vulnerability in Android hybrid apps.

Frame Confusion is a vulnerability affecting hybrid applications which allows circumventing the isolation granted by the Same-Origin Policy. The detection of such vulnerability is still carried out manually by application developers, but the process is error-prone and often underestimated. In this article, we propose a sound and complete methodology to detect the Frame Confusion on Android as well as a publicly-released tool (i.e., FCDroid) which implements such methodology and allows to detect the Frame Confusion in hybrid applications, automatically. We also make public the results obtained by analyzing 50K apps using FCDroid, which have revealed that many hybrid applications suffer from Frame Confusion.

## ❱ Publications
More details about **FCDroid** can be found in the paper "[Droids in Disarray: Detecting Frame Confusion in Hybrid Android Apps](https://link.springer.com/chapter/10.1007/978-3-030-22479-0_7)"

Please use the following bibtex entry to cite our work:


``` Bibtex
@inproceedings{caputo2019droids,
  title={Droids in disarray: detecting frame confusion in hybrid android apps},
  author={Caputo, Davide and Verderame, Luca and Aonzo, Simone and Merlo, Alessio},
  booktitle={IFIP Annual Conference on Data and Applications Security and Privacy},
  pages={121--139},
  year={2019},
  organization={Springer}
}
```
---

## ❱ Requirements
- Tested only on Ubuntu 18.04 and Ubuntu 20.04
- Use python 3.x
- Install virtualenv
  ```console
  $ pip3 install virtualenv
  ```
- Download [Oracle VirtualBox](https://www.virtualbox.org/)
- Download emulator 
  * [Androidx86](https://www.android-x86.org/releases/releasenote-6-0-r3.html) (recommended) or [Genymotion](https://www.genymotion.com/):
- Setup emulator (if needed)
    * Obtain root permissions (if needed)
    * emulator with nat e forward ports 5555 and 5554
    * emulator with bridged adapter 
    * install droidbot app ([download](https://github.com/honeynet/droidbot/tree/master/droidbot/resources))
- Enable accessibility services
- Add adb path in PATH environment variable

---

## ❱ Start Analysis
1. Create Virtualenv
  ```console
  $ virtualenv -p python3 venv
  ```
2. Enable Virtualenv
  ```console
  $ source venv/bin/activate
  ```
3. Install Requirements
  ```console
  $ pip install -r requirements
  ```
3. Start Emulator Manager 
  ```console
  $ python3 emulator_manager.py
  ```
4. Move apps to analyze within **dir_apk** dir
5. Start experiments
  ```console
  $ python3.6 hybrid_inspector.py -d "/home/User/dir_apk" -t -s "iframe"
  ```


---
