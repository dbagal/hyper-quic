# Hyper-QUIC!

The major transport layer protocols in use today are TCP and UDP. Each of them have their own advantages and disadvantages. While many applications need the functionality of TCP, the overhead associated with it sometimes weighs down its benefits. On the other hand, UDP is a very lightweight protocol, but not at all reliable and secure. Moreover it doesn’t even have packet sequencing. It is a send and forget kind of protocol. Systems like State Machine Replication (SMR), Big data systems which need a lot of message passing need the features of TCP but have to compromise with the overhead associated with it. This gets worse when one TCP connection need to be used per message sent/received. Thus, we find a need for a new protocol which includes a blend of features from both TCP and UDP. We propose Hyper-QUIC which borrows some ideas from the popular QUIC protocol and make some enhancements that will meet these needs.


# Branches

This project was done as part of CSE 534 course under Prof.   
Aruna Balasubramanian. We did not find enough time to merge all the contributor's branches and hence we describe below what each branch contains:
- dbagal - This contains the code related to our humble effort of using raw sockets to remove dependency on any trasnsport layer protocol.
- performanceMetrics - This contains a basic UDP client-server setup and also scripts to measure some performace metrics based on a packet capture file.
- rohan - This contains other code related to our same humble effort. The code here is mainly related to encryption and Diffie-Hellman key exchange.

## Contributors
- Dhaval Bagal 
- Rohan Chhabra
- Avishek Santhaliya
