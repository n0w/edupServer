'''
+-------------------------------+
| EDUP SmartSockets Fake Server | 
+-------------------------------+
Angel Suarez-B Martin (n0w) 2015

              v2
'''

from SmartSocket import SmartSocket
import socket
import select
import sys
from thread import *
import os
import time
import syslog

# ----------------------------------------------------------------------- #
#                        G  L  O  B  A  L  S
# ----------------------------------------------------------------------- #
  
QUIT = 0
HOST = ''                      # Symbolic name meaning all available interfaces
EDUP_PORT = 221                # EDUP SmartSocket Default Port
CONTROL_PORT = 8989            # Default Control Port
PIPE_NAME = '/tmp/testpipe'    # Pipe for reading commands -> rabbitmq?
KEEPALIVETIME = 5              # Time between keepalive packets 

# ----------------------------------------------------------------------- #
#                     F  U  N  C  T  I  O  N  S
# ----------------------------------------------------------------------- #  
def pipeListener(devices):
    """
    Listens to pipe incoming commands
    """
    pipeName = PIPE_NAME
    
    try:
        pipein = open(pipeName, 'r')
        
    except Exception as e:
        syslog.syslog(syslog.LOG_ERR, "Failed to open pipe: %s" % e)
    
    while True:
        data = pipein.readline()
        
        if len(data) > 0:
            
            # ON command received
            if data[0:2] == "ON":
                receivedID = data[3]
                if receivedID.isdigit():
                    for deviceID, deviceObj in devices.iteritems():
                        if deviceID == receivedID:
                            syslog.syslog('Received ON for device %s' % receivedID)
                            devices[receivedID].on()
                            break
            
            # OFF command received
            if data[0:3] == "OFF":
                receivedID = data[4]
                if receivedID.isdigit(): 
                    for deviceID, deviceObj in devices.iteritems():
                        if deviceID == receivedID:
                            syslog.syslog('Received OFF for device %s' % receivedID)
                            devices[receivedID].off()
                            break
        
        # Wait 1 second to check again
        time.sleep(1)

def controlListener(sock, devices):
    """
    Listens, accepts and serves control connections
    """
    while True:
        conn, addr = sock.accept()
        syslog.syslog('Control connection established from ' + addr[0] + ':' + str(addr[1]))
        
        conn.send("      EDUP SmartSocket Fake Server Debug Console\n")
        conn.send("=====================================================\n")
        conn.send("[+]> Control connection initialized\n")
        conn.send(" |\n")
        conn.send("[+]> Send ON, OFF or LIST command\n")

        while True:
            try:
                conn.send ("\n> ")
            except socket.error:
                syslog.syslog('Control connection from ' + addr[0] + ':' + str(addr[1]) + ' is now closed')
                break

            data = conn.recv(10).upper()
            
            try: 
                # Print connected devices list
                if data[0:4] == "LIST":
                    conn.send("\nConnected devices: " + str(len(devices)))

                    for deviceID, deviceObj in devices.iteritems():
                        info = deviceObj.getInfo()
                        
                        conn.send("\n [+] Device ID:" + str(info['id']))
                        conn.send("\n  |     Socket:" + str(info['socket']))
                        conn.send("\n  |        MAC:" + str(info['mac']))
                        conn.send("\n  |         IP:" + str(info['ip']))
                        conn.send("\n [+]    Status:" + str(info['status']))
                        conn.send("\n")
                
                # ON command received
                elif data[0:2] == "ON":
                    receivedID = data[3]
                    if receivedID.isdigit(): 
                        for deviceID, deviceObj in devices.iteritems():
                            if deviceID == receivedID:
                                syslog.syslog('Received ON for device %s' % receivedID)
                                devices[receivedID].on()
                                break
                
                # OFF command received
                elif data[0:3] == "OFF":
                    receivedID = data[4]
                    if receivedID.isdigit(): 
                        for deviceID, deviceObj in devices.iteritems():
                            if deviceID == receivedID:
                                syslog.syslog('Received OFF for device %s' % receivedID)
                                devices[receivedID].off()
                                break
                
                # KILL command received
                elif data[0:4] == "KILL":
                    receivedID = data[5]
                    
                    if receivedID.isdigit(): 
                        for deviceID, deviceObj in devices.iteritems():
                            if deviceID == receivedID:
                                syslog.syslog('Received KILL for device %s' % receivedID)
                                devices[receivedID].close()
                                break

            except Exception as e:
                syslog.syslog(syslog.LOG_ERR, 'Error processing command: %s' % e)

def sendKA(smartSocket):
    """
    Manages sending KA packets to each SmartSocket
    Should manage the entire socket conversation -ie listening for manual ON/OFF
    """     
    smartSocketID = smartSocket.getID()
    
    while smartSocket.getConnectionStatus() == True:
        time.sleep(KEEPALIVETIME)         
        smartSocket.sendKeepAlive()

    syslog.syslog(syslog.LOG_ERR, 'Exiting keepAlive thread - device %s disconnected' % smartSocketID)
    exit()
      

# ----------------------------------------------------------------------- #
#                                M  A  I  N
# ----------------------------------------------------------------------- #
  
if __name__ == '__main__':
    print "     EDUP SmartSocket Fake Server"
    print "======================================"
    print " Written by Angel Suarez-B. Martin (n0w)"
    
    # Set syslog options
    syslog.openlog('edupServer', 0, syslog.LOG_LOCAL4 )
    syslog.syslog('edupServer started')
       
    # Declare and set sockets
    socketEDUP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socketEDUP.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    socketControl = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socketControl.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    syslog.syslog('Socket created')
    
    # Bind sockets to local host and ports
    try:
        socketEDUP.bind((HOST, EDUP_PORT))
        socketControl.bind((HOST, CONTROL_PORT))   
    
    except socket.error as msg:
        syslog.syslog(syslog.LOG_CRIT, 'Error binding socket! %s'% msg[1])
        sys.exit()
      
    syslog.syslog('Sockets bound')
    
    socketEDUP.listen(10)
    socketControl.listen(1)

    # Connected devices dictionary
    devicesDict = {}
    
    # To lock devices dictionary
    semDevices =  allocate_lock() 

    # Spawn new thread for control connections
    start_new_thread(controlListener, (socketControl, devicesDict,))
    
    # Spawn new thread for reading pipe
    start_new_thread(pipeListener, (devicesDict,))
    
    try:  
        while 1:
            conn, addr = socketEDUP.accept()
            syslog.syslog('New SmartSocket connection from %s:%s' % (addr[0],addr[1]))
                      
            # Create new SmartSocket object for incoming connection
            connectedDevice = SmartSocket(conn, addr[0], devicesDict, semDevices)            
            
            # Start a new thread to send keep alives every 30 secs
            start_new_thread(sendKA, (connectedDevice,))

    except KeyboardInterrupt:
        QUIT = 1
        socketControl.close()
        socketEDUP.close()
