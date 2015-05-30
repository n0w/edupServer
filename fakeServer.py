'''
+-------------------------------+
| EDUP SmartSockets Fake Server | 
+-------------------------------+
Angel Suarez-B Martin (n0w) 2015

'''
#!/usr/bin/python

import socket
import sys
from thread import *
import time
import sqlite3

QUIT = 0
HOST = ''  # Symbolic name meaning all available interfaces
EDUP_PORT = 221  # EDUP SmartSocket Default Port
CONTROL_PORT = 8989  # Default Control Port

class SmartSocket:
  
    def __init__(self, socket, ip):
        # SmartSocket Object Attribs.
        # Parameters
        self.ipAddr = str(ip)
        self.socket = socket
        
        self.id = None
        self.macAddr= None
        self.heloCMD = None
        self.onCMD = None
        self.offCMD = None
        self.keepAliveCMD = None
        
        # Device-related attribs.
        # Short description of what device is this smartsocket controlling.
        self.description = None
        # Actual status (ON/OFF) of the smartsocket relay.
        self.status = None
        
        # Initialize database and prepare query.
        dbConnection = sqlite3.connect('edup.db')
        dbCursor = dbConnection.cursor()
        
        sqlQuery = """SELECT devices.id, 
                                 macAddr,
                                 heloCMD,
                                 onCMD,
                                 offCMD,
                                 keepAliveCMD,
                                 estado,
                                 desc
                       FROM   devices, parameters 
                       WHERE        parameters.ipAddr=? 
                              AND   devices.id = parameters.id;"""
        # Using IP address as key, get attributes from database      
        # We have to pass a tuple instead a grouped expression, hence the comma
        dbCursor.execute(sqlQuery,(self.ipAddr,))
        retrievedInfo = dbCursor.fetchone()
        
        # We have to keep commands as hexadecimal values      
        self.id = retrievedInfo[0]
        self.macAddr= retrievedInfo[1]
        self.heloCMD = retrievedInfo[2].decode('hex')
        self.onCMD = retrievedInfo[3].decode('hex')
        self.offCMD = retrievedInfo[4].decode('hex')
        self.keepAliveCMD = retrievedInfo[5].decode('hex')
        self.status = retrievedInfo[6]
        self.description = retrievedInfo[7]
        
        # Start talking
        # Send HELO first
        self.socket.send(self.heloCMD)
        
        # Check if received MAC address matches our own
        data = ByteToHex(self.socket.recv(30))
        if data[22:34] == self.macAddr:
            pass
        
        # Discard next packet
        data = self.socket.recv(30)
        
        # -- Connection is now established --
        
    def getID(self):
        return str(self.id)
     
    def on(self):
        self.socket.send(self.onCMD)
        data = self.socket.recv(30)
        self.status = 1
    
    def off(self):
        self.socket.send(self.offCMD)
        data = self.socket.recv(30)
        self.status = 0

    def sendKeepAlive(self):
        self.socket.send(self.keepAliveCMD)
    
    def close(self):
        self.socket.close()
        
    def showInfo(self):
        return "Id: {} - {} - Status: {}".format(self.id, self.description, self.status) 

# --------------------------------------------------------------------------- #

def remoteListener(sock, devices):
    sock.send("      EDUP SmartSocket Fake Server\n")
    sock.send("======================================\n")
    sock.send("Control connection initialized\n")
    sock.send("Send ON or OFF command\n")
  
    while True:
        sock.send ("\n> ")
        data = sock.recv(10)
        
        try:
            # Print connected devices list
            if data[0:4] == "LIST":
                for deviceID, deviceObj in devices.iteritems():
                    sock.send ("\n" + deviceObj.showInfo())
                
            if data[0:2] == "ON":
                receivedID = data[3]
                
                if receivedID.isdigit(): #comprobar tambien que existe!!!
                    sock.send("\n[+] On command sent to device " + receivedID)
                    devices[receivedID].on()
              
            if data[0:3] == "OFF":
                receivedID = data[4]
                
                if receivedID.isdigit(): #comprobar tambien que existe!!!
                    sock.send("\n[+] Off command sent to device " + receivedID)
                    devices[receivedID].off()
        except:
            pass
   
def sendKA(smartSocket):     
    while QUIT <> 1:
        time.sleep(30)         
        smartSocket.sendKeepAlive()
    smartSocket.close()

      
def ByteToHex(byteStr):
    """
    Convert a byte string to it's hex string representation e.g. for output.
    """
    return ''.join([ "%02X" % ord(x) for x in byteStr ]).strip()
  
if __name__ == '__main__':
    print "     EDUP SmartSocket Fake Server"
    print "======================================"
    print " Written by Angel Suarez-B. Martin (n0w)"
    
    # Connected devices dictionary
    devicesDict = {}
    
    # Declare and set sockets
    socketControl = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socketControl.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  
    socketEDUP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socketEDUP.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    print '[+] Sockets created'

    # Bind sockets to local host and ports
    try:
        socketEDUP.bind((HOST, EDUP_PORT))
        socketControl.bind((HOST, CONTROL_PORT))     
    except socket.error as msg:
        print '[e] Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
        sys.exit()
      
    print '[+] Sockets bind complete'
    
    # Start listening on control socket
    socketControl.listen(10)
    print '[>] Control Socket now listening' 
    
    conn, addr = socketControl.accept()
    print '[i] Control connection from ' + addr[0] + ':' + str(addr[1])
    start_new_thread(remoteListener, (conn, devicesDict))
    
    socketEDUP.listen(10)
    print '[>] Socket now listening' 
    try:  
        while 1:
            conn, addr = socketEDUP.accept()
            print '[!] Incoming SmartSocket from ' + addr[0] + ':' + str(addr[1])
            
            # Create new SmartSocket object from incoming connection
            connectedDevice = SmartSocket(conn,addr[0])
            # Add it to the devices dictionary
            devicesDict[connectedDevice.getID()] = connectedDevice
            # Start a new thread to send keep alives every 30 secs
            start_new_thread(sendKA, (connectedDevice,))

    except KeyboardInterrupt:
        QUIT = 1
        socketControl.close()
        socketEDUP.close()
