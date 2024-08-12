import asyncio


class FramedProtocol(asyncio.Protocol):
    def __init__(self, processor=None):
        self.buffer = b""
        self.transport = None

        default = lambda z: print('got:', z)
        self.process_message = processor or default

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        self.buffer += data
        while b'\n' in self.buffer:
            message, self.buffer = unframe_buffer(self.buffer)
            self.process_message(unescape_message(message))

    def send_message(self, message):
        self.transport.write(frame_message(message))


def frame_message(message):
    return escape_message(message).encode() + b'\n'


def unframe_buffer(buf):
    return buf.split(b'\n', 1)


def escape_message(message):
    '''Escape the framing characters'''
    return message.replace(b'\\', b'\\\\').replace(b'\n', b'\\n')


def unescape_message(message):
    '''Unescape the framing characters'''
    return message.replace(b'\\n', b'\n').replace(b'\\\\', b'\\')


if __name__ == '__main__':
    async def main():
        loop = asyncio.get_running_loop()

        server = await loop.create_server(
            lambda: FramedProtocol(),
            '127.0.0.1', 8888)

        async with server:
            await server.serve_forever()


    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        exit()

