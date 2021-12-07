# hyper-quic


This branch contains 3 files: <br />
1. client.pcap          - The packet capture file for client-server setup with UDP as transport protocol. <br />
2. quicdnsclient.pcap   - The packet capture file for DNS server setup with aioquic as transport protocol. <br />
3. quichttpclient.pcap  - The packet capture file for HTTP server setup with aioquic as transport protocol. <br />
<br />
Below is how the above files were captured on the client using tcpdump: <br />
sudo tcpdump --interface ens4 host {serverIP} -w {fileName} <br />
1. To capture client.pcap run udpServer.py on the server size and run performace.py on the client side and capture packets on client using the above tcpdump command. <br />
2. To capture quicdnsclient.pcap run dns exmaple of aioquic using steps described in the final report.  <br />
3. To capture quichttpclient.pcap run http exmaple of aioquic using steps described in the final report.  <br /> 
<br />
<br />
<br />
All the above code was run using python 3.10 <br />
