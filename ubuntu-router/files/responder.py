import asyncio
import sys


class UDPHandler(asyncio.DatagramProtocol):
    def __init__(self, loop):
        self.loop = loop

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        response = f"{addr[0]}:{addr[1]}"
        self.transport.sendto(response.encode(), addr)

    def error_received(self, exc):
        print(f"UDP error: {exc}")

    def connection_lost(self, exc):
        print("UDP connection lost")


async def tcp_handler(port):
    server = await asyncio.start_server(handle_tcp, '0.0.0.0', port)
    async with server:
        await server.serve_forever()


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

    _, _ = await loop.create_datagram_endpoint(
        lambda: UDPHandler(loop),
        local_addr=('0.0.0.0', port)
    )

    await tcp_handler(port)

asyncio.run(main())
