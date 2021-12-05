import socket

msgFromClient       = "Hello UDP Server"
bytesToSend         = str.encode(msgFromClient)
serverAddressPort   = ("10.190.0.2", 20002)
bufferSize          = 1024

# Create a UDP socket at client side

UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

# Send to server using created UDP socket
def sendRequest( request ):
    serverInfo = serverAddressPort
    requestBytes = str.encode( request )
    UDPClientSocket.sendto( requestBytes, serverInfo )

def receiveData( bufferSize, fileName ):
    # msg = "Message from Server {}".format(msgFromServer[0])
    # print(msg)
    # First get size
    myfile = open( fileName, 'ab' )
    msgFromServer = UDPClientSocket.recvfrom( bufferSize )
    dataSize = int( msgFromServer[0].decode( "utf-8" ) )
    bytesReceived = 0
    while bytesReceived < dataSize:
        msgFromServer = UDPClientSocket.recvfrom( bufferSize )
        replyBytes = msgFromServer[0]
        bytesReceived = bytesReceived + len( replyBytes )
        myfile.write( replyBytes )
        print( bytesReceived, ":", dataSize )
    myfile.close()
