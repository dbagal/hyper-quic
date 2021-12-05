
class HyperQuicPacket:

    class Flags:
        def __init__(self, **params) -> None:
            for param, val in params.items():
                setattr(self, param, val)

    def __init__(self, connection_id, flags, packet_num, payload) -> None:
        self.connection_id = bytes(connection_id)
        self.packet_num = bytes(packet_num)
        self.payload = bytes(payload)