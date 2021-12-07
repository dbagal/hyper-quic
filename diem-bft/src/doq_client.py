import argparse
import asyncio
import logging
import pickle
import ssl
from typing import Optional, cast

from dnslib.dns import QTYPE, DNSQuestion, DNSRecord

from aioquic.asyncio.client import connect
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import QuicEvent, StreamDataReceived
from aioquic.quic.logger import QuicFileLogger

logger = logging.getLogger("client")


class DoQClient(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ack_waiter: Optional[asyncio.Future[None]] = None

    async def query(self, obj: bytes) -> None:
        # query = DNSRecord(q=DNSQuestion(dns_query, getattr(QTYPE, query_type)))
        stream_id = self._quic.get_next_available_stream_id()
        logger.debug(f"Stream ID: {stream_id}")
        end_stream = False
        print(f'Sending object = {obj}')
        self._quic.send_stream_data(stream_id, obj, end_stream)
        waiter = self._loop.create_future()
        self._ack_waiter = waiter
        self.transmit()

        return await asyncio.shield(waiter)

    # def quic_event_received(self, event: QuicEvent) -> None:
    #     if self._ack_waiter is not None:
    #         if isinstance(event, StreamDataReceived):
    #             answer = DNSRecord.parse(event.data)
    #             logger.info(answer)
    #             waiter = self._ack_waiter
    #             self._ack_waiter = None
    #             waiter.set_result(None)


def save_session_ticket(ticket):
    """
    Callback which is invoked by the TLS engine when a new session ticket
    is received.
    """
    logger.info("New session ticket received")
    # if args.session_ticket:
    #     with open(args.session_ticket, "wb") as fp:
    #         pickle.dump(ticket, fp)


async def run(
        configuration: QuicConfiguration,
        host: str,
        port: int,
        obj: bytes,
) -> None:
    logger.debug(f"Connecting to {host}:{port}")
    async with connect(
            host,
            port,
            configuration=configuration,
            session_ticket_handler=save_session_ticket,
            create_protocol=DoQClient,
    ) as client:
        client = cast(DoQClient, client)
        logger.debug("Sending DNS query")
        await client.query(obj)

def get_or_create_eventloop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError as ex:
        if "There is no current event loop in thread" in str(ex):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return asyncio.get_event_loop()

def send_data(host, port, obj):
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO,
    )

    configuration = QuicConfiguration(
        alpn_protocols=["dq"], is_client=True, max_datagram_frame_size=300000
    )

    ca_certs = '/Users/rohan/workspace/aioquic/tests/pycacert.pem'
    if ca_certs:
        configuration.load_verify_locations(ca_certs)
    logger.debug("No session ticket defined...")

    loop = get_or_create_eventloop()
    loop.run_until_complete(
        run(
            configuration=configuration,
            host=host,
            port=port,
            obj=obj,
        )
    )
    print('DATA SENT')