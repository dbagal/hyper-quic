def fetch_id_components(id):
    node_name, ip_port = id.split("@")
    ip, send_port, recv_port = ip_port.split(":")
    return node_name, ip, int(send_port), int(recv_port)