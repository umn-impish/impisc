import asyncio
import packet_processing as pp


async def main():
    loop = asyncio.get_running_loop()

    server = await loop.create_server(
        lambda: FramedProtocol(pp.forward_packet),
        '127.0.0.1', 8888)

    async with server:
        await server.serve_forever()

asyncio.run(main())

