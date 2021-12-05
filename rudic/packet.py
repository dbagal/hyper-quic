import struct


class RUDICPacket:

    class Flags:
        def __init__(self, **params) -> None:
            for param, val in params.items():
                setattr(self, param, val)

    def __init__(self, flags:list, nack:int, packet_num:int, look_ahead_packet_num:int, payload:bytes) -> None:
        self.packet_num = packet_num
        self.look_ahead_packet_num = look_ahead_packet_num
        self.payload = payload,
        self.nack = nack
        self.flags = RUDICPacket.Flags(
            nack = flags[0]
        )


class RUDICPacketHandler:

    @staticmethod
    def assemble(rudic_packet:RUDICPacket):
        
        packet_num = struct.pack(">I", rudic_packet.packet_num)  # big-endian unsigned int (4 bytes) -> bytes
        look_ahead_packet_num = struct.pack(">I", rudic_packet.look_ahead_packet_num)
        nack = struct.pack(">I", rudic_packet.packet_num)

        flags = [
            rudic_packet.flags.nack
        ]

        flag_bin_string = "".join([str(bit) for bit in flags])
        flag_int = int(flag_bin_string, 2)
        flag_byte = struct.pack(">H", flag_int)[1]  # big-endian unsigned short (2 bytes) -> bytes 

        packet_bytes = flag_byte + packet_num + look_ahead_packet_num + nack + rudic_packet.payload
        return packet_bytes


    @staticmethod
    def disassemble(raw_bytes:bytes):
        flag_int = raw_bytes[0]
        flag_list = [1 if flag_int & (1 << (7-n)) else 0 for n in range(8)]

        packet_num = struct.unpack(">I", raw_bytes[1:5])[0]
        look_ahead_packet_num = struct.unpack(">I", raw_bytes[5:9])[0]
        payload = raw_bytes[9:]

        return RUDICPacket(
            flags=flag_list,
            packet_num=packet_num,
            look_ahead_packet_num=look_ahead_packet_num,
            payload=payload
        )
