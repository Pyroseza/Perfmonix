# Codename: Eureka
the purpose of this script is to parse a truss or strace log file and summarise all the commands
## Prerequisites
Install Python3
Generate a truss or strace log file
- e.g. on AIX generate a truss log file like this: 
```
    truss -d -f -o truss.log -p <pid>
```
- e.g. on Linux generate a strace log file like this: 
```
    strace -ttt -T -f -o strace.log -p <pid>
```
## Usage
Call the script as an argument to python and give filename as an additioanl argument
```
    python PerfTracerParser.py logfile
```
### N.B. if no file is specified then it will default to "trace.log"
---
## Author
* **Jarrod Price** - *Creator* - [jarpri08@gmail.com](mailto:jarpri08@gmail.com?subject=Eureka)
