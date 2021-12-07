import argparse
import asyncio
import logging
import pickle
from typing import Dict, Optional

from dnslib.dns import DNSRecord

from aioquic.asyncio import QuicConnectionProtocol, serve
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.connection import QuicConnection
from aioquic.quic.events import ProtocolNegotiated, QuicEvent, StreamDataReceived, DatagramFrameReceived
from aioquic.quic.logger import QuicFileLogger
from aioquic.tls import SessionTicket

try:
    import uvloop
except ImportError:
    uvloop = None

stream_data = {}

recv_queue = []


def recv_queue_pop(idx):
    return recv_queue.pop(idx)


def recv_queue_len():
    return len(recv_queue)


class DnsConnection:
    def __init__(self, quic: QuicConnection):
        self._quic = quic
        # self.recv_queue = recv_queue

    # def do_query(self, payload) -> bytes:
    #     q = DNSRecord.parse(payload)
    #     return q.send(self.resolver(), 53)
    #
    # def resolver(self) -> str:
    #     return args.resolver

    def handle_event(self, event: QuicEvent) -> None:
        if isinstance(event, StreamDataReceived):
            print(f'Object received = {event.data}')
            if event.stream_id not in stream_data:
                stream_data[event.stream_id] = event.data
            else:
                stream_data[event.stream_id] += event.data

            print(f'END STREAM = {event.end_stream}')
            if event.data.endswith(b"/EOM"):
                print('--------END OF STREAM--------')
                val = stream_data[event.stream_id]
                print(f'--------VAL = {val} ------')
                data = pickle.loads(val.strip(b"/EOM"))
                print(f'PICKLE LOAD = {data}')
                global recv_queue
                recv_queue += [data]
                del stream_data[event.stream_id]
                print(f'RECV QUEUE server = {recv_queue}')
            # data = self.do_query(event.data
            # end_stream = False
            # self._quic.send_stream_data(event.stream_id, data, end_stream)


class DnsServerProtocol(QuicConnectionProtocol):
    # -00 specifies 'dq', 'doq', and 'doq-h00' (the latter obviously tying to
    # the version of the draft it matches). This is confusing, so we'll just
    # support them all, until future drafts define conflicting behaviour.
    SUPPORTED_ALPNS = ["dq", "doq", "doq-h00"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dns: Optional[DnsConnection] = None

    def quic_event_received(self, event: QuicEvent):
        if isinstance(event, ProtocolNegotiated):
            if event.alpn_protocol in DnsServerProtocol.SUPPORTED_ALPNS:
                self._dns = DnsConnection(self._quic)
        if self._dns is not None:
            self._dns.handle_event(event)


class SessionTicketStore:
    """
    Simple in-memory store for session tickets.
    """

    def __init__(self) -> None:
        self.tickets: Dict[bytes, SessionTicket] = {}

    def add(self, ticket: SessionTicket) -> None:
        self.tickets[ticket.ticket] = ticket

    def pop(self, label: bytes) -> Optional[SessionTicket]:
        return self.tickets.pop(label, None)


def get_or_create_eventloop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError as ex:
        if "There is no current event loop in thread" in str(ex):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return asyncio.get_event_loop()


def init_server(host, port):
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO,
    )

    quic_logger = None

    configuration = QuicConfiguration(
        alpn_protocols=["dq"],
        is_client=False,
        max_datagram_frame_size=300000,
        quic_logger=quic_logger,
    )

    certificate = "/Users/rohan/workspace/aioquic/tests/ssl_cert.pem"
    private_key = "/Users/rohan/workspace/aioquic/tests/ssl_key.pem"
    configuration.load_cert_chain(certificate, private_key)

    ticket_store = SessionTicketStore()

    if uvloop is not None:
        uvloop.install()
    loop = get_or_create_eventloop()
    loop.run_until_complete(
        serve(
            host,
            port,
            configuration=configuration,
            create_protocol=DnsServerProtocol,
            session_ticket_fetcher=ticket_store.pop,
            session_ticket_handler=ticket_store.add,
            retry=True,
        )
    )
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
