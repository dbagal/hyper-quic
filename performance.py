import udpClient 
# Have options to select big object/small object

# Change client here for our code. NOTE: Our client should have sendRequest and receiveData methods
client = udpClient

# Request for small message first
client.sendRequest( 'Hey server' )
client.receiveData( 1024, 'message.txt' )

# Request for small object
client.sendRequest( 'smallObject' )
client.receiveData( 10000000, 'smallObject.png' )

# Request for big object
client.sendRequest( 'largeObject' )
client.receiveData( 10000000, 'largeObject.png' )
