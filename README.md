# EDUP SmartSockets Fake Server

This repository hosts python code for a server that controls EDUP SmartSockets through TCP sockets.

Part of the 'Hacking SmartSockets' series from (http://n0wblog.blogspot.com.es/)

## Usage

```
mkdir /tmp/testpipe
python edupServer.py
```

##Changelog

###22 Nov 2015

* Code split into modules for clarity
* Better thread management
* Decreased default time between keepAlives to 5 seconds
* Better debug control
* Added log to syslog

##To Do
* Manual ON/OFF (through device pulsebutton) command receiving / parsing
