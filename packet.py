import struct


class HyperQuicPacket:

    class Flags:
        def __init__(self, **params) -> None:
            for param, val in params.items():
                setattr(self, param, val)

    def __init__(self, connection_id:bytes, flags:list, packet_num:int, look_ahead_packet_num:int, payload:bytes) -> None:
        self.connection_id = connection_id
        self.packet_num = packet_num
        self.look_ahead_packet_num = look_ahead_packet_num
        self.payload = payload
        self.flags = HyperQuicPacket.Flags(
            ichlo = flags[0],
            cchlo = flags[1],
            shlo = flags[2],
            rej = flags[3],
            nack = flags[4],
            regular = flags[5]
        )


class HyperQuicPacketHandler:

    @staticmethod
    def assemble(hyper_quic_packet:HyperQuicPacket):
        conn_id = hyper_quic_packet.connection_id
        packet_num = struct.pack(">I", hyper_quic_packet.packet_num)  # big-endian unsigned int (4 bytes) -> bytes
        look_ahead_packet_num = struct.pack(">I", hyper_quic_packet.look_ahead_packet_num)

        flags = [
            hyper_quic_packet.flags.ichlo,
            hyper_quic_packet.flags.cchlo,
            hyper_quic_packet.flags.shlo,
            hyper_quic_packet.flags.rej,
            hyper_quic_packet.flags.nack,
            hyper_quic_packet.flags.regular
        ]

        flag_bin_string = "".join([str(bit) for bit in flags])
        flag_int = int(flag_bin_string, 2)
        flag_byte = struct.pack(">H", flag_int)[1]  # big-endian unsigned short (2 bytes) -> bytes 

        packet_bytes = conn_id + flag_byte + packet_num + look_ahead_packet_num + hyper_quic_packet.payload
        return packet_bytes


    @staticmethod
    def disassemble(raw_bytes:bytes):
        conn_id_bytes = raw_bytes[0:8]
        flag_int = raw_bytes[8]
        flag_list = [1 if flag_int & (1 << (7-n)) else 0 for n in range(8)]
        packet_num = struct.unpack(">I", raw_bytes[9:13])[0]
        look_ahead_packet_num = struct.unpack(">I", raw_bytes[13:17])[0]
        payload = raw_bytes[17:]

        return HyperQuicPacket(
            connection_id=conn_id_bytes,
            flags=flag_list,
            packet_num=packet_num,
            look_ahead_packet_num=look_ahead_packet_num,
            payload=payload
        )
