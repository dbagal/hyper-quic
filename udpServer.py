import socket

localIP     = "10.190.0.2"
localPort   = 20002
bufferSize  = 1024


msgFromServer       = "Hello UDP Client"
bytesToSend         = str.encode(msgFromServer)

UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
UDPServerSocket.bind((localIP, localPort))

print("UDP server up and listening")

def getBytesFromFile( fileName ):
    myfile = open( fileName, 'rb' )
    myFileBytes = myfile.read()
    print( 'Number of bytes in ', fileName, ' is ', len( myFileBytes ) )
    return myFileBytes

def parseRequest( request ):
    request = request.decode( "utf-8" )
    replyBytes = None
    if request == 'smallObject':
        # send small object bytes
        reply = 'smallObject'
        replyBytes = getBytesFromFile( '/home/asanthaliya/hyper-quic/smallObject.png' )
    elif request == 'largeObject':
        # send large object bytes
        reply = 'largeObject'
        replyBytes = getBytesFromFile( '/home/asanthaliya/hyper-quic/smallObject.png' )
    else:
        reply = 'Hey qt client'
        replyBytes = str.encode( reply )
    return replyBytes

def sendReply( replyBytes, clientIP ):
    #UDPServerSocket.sendto( replyBytes, clientIP )
    print( 'Total bytes to send: ', len( replyBytes ) )
    # First send size
    UDPServerSocket.sendto( str.encode( str( len( replyBytes ) ) ), clientIP )
    left = 0
    right = bufferSize
    while True:
        right = min( right, len( replyBytes ) )
        print( 'Sending: ', left, ' to ', right-1 )
        UDPServerSocket.sendto( replyBytes[left:right], clientIP )
        left = right
        right = left + bufferSize
        if left == len( replyBytes ):
            break

# Listen for incoming datagrams
while(True):

    bytesAddressPair = UDPServerSocket.recvfrom(bufferSize)
    message = bytesAddressPair[0]
    address = bytesAddressPair[1]
    clientMsg = "Message from Client:{}".format(message)
    clientIP  = "Client IP Address:{}".format(address)
    
    print(clientMsg)
    print(clientIP)

    # Sending a reply to client
    replyBytes = parseRequest( message )
    sendReply( replyBytes, address )
