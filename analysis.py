#!/usr/local/bin/python2.7

import dpkt
from scapy.all import Ether

filename = 'client.pcap'
clientIp = '10.182.0.2'
serverIp = '10.190.0.2'
numPacketsClient = 0
numPacketsServer = 0
totalBytesClient = 0
totalBytesServer = 0
startTimeClient = None
startTimeServer = None
endTimeClient = None
endTimeServer = None

for ts, pkt in dpkt.pcap.Reader( open( filename, 'r' ) ):
    etherFrame = Ether( pkt )
    src = etherFrame.payload.src
    dst = etherFrame.payload.dst
    if src == clientIp:
        numPacketsClient += 1
        totalBytesClient += len( pkt )
        if not startTimeClient:
            startTimeClient = ts
        endTimeClient = ts
    elif src == serverIp:
        numPacketsServer += 1
        totalBytesServer += len( pkt )
        if not startTimeServer:
            startTimeServer = ts
        endTimeServer = ts

print( 'Client stats' )
totalTimeClient = endTimeClient - startTimeClient
print( 'Total packets sent: ', numPacketsClient )
print( 'Total bytes sent: ', totalBytesClient )
print( 'Total time: ', totalTimeClient )
print( 'Throughput: ', totalBytesClient / totalTimeClient )

print( 'Server stats')
totalTimeServer = endTimeServer - startTimeServer
print( 'Total packets sent: ', numPacketsServer )
print( 'Total bytes sent: ', totalBytesServer )
print( 'Total time: ', totalTimeServer )
print( 'Throughput: ', totalBytesServer / totalTimeServer )
        
