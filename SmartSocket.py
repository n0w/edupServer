
'''
+-------------------------------+
| EDUP SmartSockets Fake Server | 
+-------------------------------+
Angel Suarez-B Martin (n0w) 2015

              v2
'''
import sqlite3
import syslog
import socket

def ByteToHex(byteStr):
    """
    Returns hex string representation of byteStr
    """
    return ''.join([ "%02X" % ord(x) for x in byteStr ]).strip()

class SmartSocket:
  
    def __init__(self, socket, ip, devices, mutex):
        """ 
        Retrieves device information from db,
        starts conversation and initializes connection
        """
        # SmartSocket Object Attribs.
        # Parameters
        self.ipAddr = str(ip)
        self.socket = socket
        self.devices = devices
        self.mutex = mutex
        
        self.connected = None
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
        
        if retrievedInfo == None:
            syslog.syslog(syslog.LOG_ERR, 'Unknown device tried to connect from %s' % self.ipAddr)
            return 
        
        # We have to keep commands as hexadecimal values      
        # Important! db returns INT id type, hence the cast to str
        self.id = str(retrievedInfo[0])
        self.macAddr= retrievedInfo[1]
        self.heloCMD = retrievedInfo[2].decode('hex')
        self.onCMD = retrievedInfo[3].decode('hex')
        self.offCMD = retrievedInfo[4].decode('hex')
        self.keepAliveCMD = retrievedInfo[5].decode('hex')
        self.status = retrievedInfo[6]
        self.description = retrievedInfo[7]
        
        try:
            # Start talking
            # Send HELO first
            self.socket.send(self.heloCMD)
            
            # Check if received MAC address matches our own
            data = ByteToHex(self.socket.recv(30))
            if data[22:34] == self.macAddr:
                pass
            
            # Discard next packet
            data = self.socket.recv(30)
        
        except socket.error, e:
            syslog.syslog(syslog.LOG_ERR, '[%s]: Error trying to connect to device: %s' % (self.id, e))
            return
        
        # -- Connection is now established --
        self.connected = True
        
        # Add self to the devices dictionary
        # We need to ask for mutex
        self.mutex.acquire()
        self.devices[self.id] = self
        self.mutex.release()

        
    def getID(self):
        """
        Returns its ID
        """
        return self.id
     
    def on(self):
        """
        Turns the device on by sending the on command 
        and waiting for its response
        """
        try:
            self.socket.send(self.onCMD)
        except socket.error, e:
            syslog.syslog(syslog.LOG_ERR, '[%s]: Error sending ON command. Disconnecting device..' % self.id)
            self.close()
            
        try:
            data = self.socket.recv(30)
        except socket.error, e:
            syslog.syslog(syslog.LOG_ERR, '[%s]: Error receiving ON acknowledgement. Disconnecting device..' % self.id)
            self.close()
    
        self.status = 1
    
    def off(self):
        """
        Turns the device off by sending the off command
        and waiting for its response
        """
        try:
            self.socket.send(self.offCMD)
        except socket.error, e:
            syslog.syslog(syslog.LOG_ERR, '[%s]: Error sending OFF command. Disconnecting device..' % self.id)
            self.close()
            
        try:
            data = self.socket.recv(30)
        except socket.error, e:
            syslog.syslog(syslog.LOG_ERR, '[%s]: Error receiving OFF acknowledgement. Disconnecting device..' % self.id)
            self.close()
        
        self.status = 0
    
    def sendKeepAlive(self):
        """
        Keeps track of the device connection status by sending keepalive packets
        """
        try:
            self.socket.send(self.keepAliveCMD)
            # DEBUG
            syslog.syslog(syslog.LOG_INFO, '[%s]: KeepAlive command sent!' % self.id)
        except socket.error, e:
            syslog.syslog(syslog.LOG_ERR, '[%s]: Error sending KeepAlive command. Disconnecting device..' % self.id)
            self.close()
    
    def close(self):
        """
        Closes socket and tries to delete itself from the devices dictionary
        """
        # Catch lookup error in case other thread deleted it before        
        self.socket.close()
        self.connected = False
        
        try:
            self.mutex.acquire()
            del self.devices[self.id]
        except LookupError:
            pass
        
        # Release mutex after trying to delete;
        # if an exception gets raised, releasing it won't take place
        self.mutex.release()
        
    def getConnectionStatus(self):
        """ 
        DEPRECATED // Returns connection status
        """
        return self.connected
    
    def getInfo(self):
        """
        Returns a dictionary containing self' status information
        """
        statusDict = {}
        
        statusDict['ip'] = self.ipAddr
        statusDict['socket'] = self.socket
        statusDict['mac'] = self.macAddr
        statusDict['status'] = self.status
        statusDict['id'] = self.id
        statusDict['connected'] = self.connected
        
        return statusDict
    
    