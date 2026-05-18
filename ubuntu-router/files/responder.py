import asyncio
import socket
import sys

# Fixed-length echo so flow-report byte counts are deterministic
# regardless of the client's address representation.
RESPONSE = b"ella-responder-rp"  # 17 bytes


class UDPHandler(asyncio.DatagramProtocol):
    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        self.transport.sendto(RESPONSE, addr)

    def error_received(self, exc):
        print(f"UDP error: {exc}")


async def handle_tcp(reader, writer):
    _ = await reader.read(1024)
    writer.write(RESPONSE)
    writer.close()
    await writer.wait_closed()


def dual_stack_socket(kind, port):
    """AF_INET6 socket with IPV6_V6ONLY=0 — accepts both IPv4 and IPv6
    via v4-mapped addresses. Explicit setsockopt so behavior doesn't
    depend on the host's sysctl default for net.ipv6.bindv6only."""
    sock = socket.socket(socket.AF_INET6, kind)
    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
    sock.bind(('::', port))
    return sock


async def main():
    try:
        port = int(sys.argv[1])
    except (IndexError, ValueError):
        print("Usage: responder.py <port>")
        sys.exit(1)

    loop = asyncio.get_event_loop()

    await loop.create_datagram_endpoint(
        UDPHandler, sock=dual_stack_socket(socket.SOCK_DGRAM, port))

    tcp_sock = dual_stack_socket(socket.SOCK_STREAM, port)
    tcp_sock.listen()
    server = await asyncio.start_server(handle_tcp, sock=tcp_sock)
    async with server:
        await server.serve_forever()


asyncio.run(main())
