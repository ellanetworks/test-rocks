import asyncio
import socket
import sys

# Fixed-length echo so flow-report byte counts are deterministic
# regardless of the client's address representation.
RESPONSE = b"ella-responder-rp"  # 17 bytes

# The reporting port answers with the source it observed instead, so a caller can
# tell whether the network is still translating its flow the same way. It is a
# separate port because the echo above is fixed-length on purpose: a variable
# reply there would change the byte counts flow reports assert on.
REPORT_PORT_OFFSET = 1


def format_source(addr):
    """addr as the responder saw it, with v4-mapped addresses unwrapped so the
    representation does not depend on the socket family."""
    host, port = addr[0], addr[1]
    if host.startswith("::ffff:"):
        host = host[len("::ffff:"):]

    return "src={} {}\n".format(host, port).encode()


class UDPHandler(asyncio.DatagramProtocol):
    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        self.transport.sendto(RESPONSE, addr)

    def error_received(self, exc):
        print(f"UDP error: {exc}")


class UDPReportHandler(asyncio.DatagramProtocol):
    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        self.transport.sendto(format_source(addr), addr)

    def error_received(self, exc):
        print(f"UDP report error: {exc}")


async def handle_tcp_report(reader, writer):
    _ = await reader.read(1024)
    writer.write(format_source(writer.get_extra_info("peername")))
    writer.close()
    await writer.wait_closed()


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

    report_port = port + REPORT_PORT_OFFSET

    await loop.create_datagram_endpoint(
        UDPReportHandler, sock=dual_stack_socket(socket.SOCK_DGRAM, report_port))

    report_sock = dual_stack_socket(socket.SOCK_STREAM, report_port)
    report_sock.listen()
    report_server = await asyncio.start_server(handle_tcp_report, sock=report_sock)

    tcp_sock = dual_stack_socket(socket.SOCK_STREAM, port)
    tcp_sock.listen()
    server = await asyncio.start_server(handle_tcp, sock=tcp_sock)
    async with server, report_server:
        await asyncio.gather(server.serve_forever(), report_server.serve_forever())


asyncio.run(main())
