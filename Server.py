from fastSocket import FastSocket
import asyncio
import json
import time

class Server(FastSocket):
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.msg_pool = {}

    async def _handle_message(self, message, reception_time):
        async with asyncio.Lock():
            self.ack_pool[message.get("id")] = {"received": reception_time}
            self.msg_pool[message.get("id")] = message.get("payload")

    async def _handle_ack(self, message, reception_time):
        id = message.get("id")
        send_and_back = message.get("send_and_ack_time_ns")
        async with asyncio.Lock():
            if id in self.ack_pool:
                latency_ns = (send_and_back - (reception_time - self.ack_pool[id]["received"]) / 2 )
                payload = self.msg_pool.get(id, None)

        if payload:
            await self._in_queue.put({"payload": payload, "latency_ns": latency_ns})
            self.log(f"Message {id} latency calculated: {latency_ns} ns with payload: {payload}")

    async def _receive(self, reader, writer, addr):
        data = await reader.readline()
        reception_time = time.time_ns()
        if not data:
            self.log("Empty message received, connection might be closed")
            raise ConnectionError("Empty message received")
        message = json.loads(data.decode())
        self.log(f"Received {message} from {addr}")

        if message.get("type") == "message":
            await self._handle_message(message, reception_time)
            ack_message = {
                "id": message.get("id"),
                "type": "ack"
            }
            writer.write((json.dumps(ack_message) + "\n").encode())
            await writer.drain()
            
        elif message.get("type") == "ack":
            await self._handle_ack(message, reception_time)

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        self.log(f"Connection from {addr} established")

        while True:
            try:
                await self._receive(reader, writer, addr)
            except ConnectionError:
                self.log(f"Connection from {addr} lost")
                break
            except ConnectionResetError:
                self.log(f"Connection from {addr} reset by peer")
                break
            # finally:
            #     writer.close()
            #     await writer.wait_closed()
            #     self.log(f"Connection from {addr} closed") 

        writer.close()
        await writer.wait_closed()
        self.log(f"Connection from {addr} closed")

    async def start(self):
        server = await asyncio.start_server(self.handle_client, *self.addr)
        addr = server.sockets[0].getsockname()
        self.log(f'Serving on {addr}')

        async with server:
            await server.serve_forever()
        
if __name__ == "__main__":

    server = Server(logfunc=None)
    async def print_messages(server):
        while True:
            msg = await server._in_queue.get()
            print(f"Received message: {msg['payload']} with latency: {msg['latency_ns']} ns")
    
    async def main():
        asyncio.create_task(print_messages(server))        
        server.set_addr('0.0.0.0', 8888)
        await server.start()

    
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\nServer stopped by user")
