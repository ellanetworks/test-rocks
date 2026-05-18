import asyncio
import sys


class UDPHandler(asyncio.DatagramProtocol):
    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        # addr is (host, port) for AF_INET and (host, port, flowinfo,
        # scopeid) for AF_INET6 — only the first two elements are used.
        response = f"{addr[0]}:{addr[1]}"
        self.transport.sendto(response.encode(), addr)

    def error_received(self, exc):
        print(f"UDP error: {exc}")


async def handle_tcp(reader, writer):
    _ = await reader.read(1024)
    addr = writer.get_extra_info('peername')
    writer.write(f"{addr[0]}:{addr[1]}".encode())
    writer.close()
    await writer.wait_closed()


async def main():
    try:
        port = int(sys.argv[1])
    except (IndexError, ValueError):
        print("Usage: responder.py <port>")
        sys.exit(1)

    loop = asyncio.get_event_loop()

    # UDP: one explicit listener per address family so behaviour is
    # the same regardless of the host's IPV6_V6ONLY default.
    for host in ('0.0.0.0', '::'):
        await loop.create_datagram_endpoint(
            UDPHandler,
            local_addr=(host, port),
        )

    # TCP: host=None makes asyncio create a socket per family.
    server = await asyncio.start_server(handle_tcp, host=None, port=port)
    async with server:
        await server.serve_forever()


asyncio.run(main())
