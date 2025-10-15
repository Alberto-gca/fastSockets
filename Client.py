from fastSocket import FastSocket
import asyncio
import json
import uuid
import time
 
class Client(FastSocket):
    def __init__(self,*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reader = None
        self.writer = None

    async def connect(self):
        self.log(f"Connecting to server at {self.addr}")
        self.reader, self.writer = await asyncio.open_connection(*self.addr)
        self.log(f"Connected to server at {self.addr}")
        asyncio.create_task(self._sender())
        asyncio.create_task(self._ack_manager())

    async def send(self, message):
        await self._out_queue.put(message)

    async def _ack_pool_put(self, id, timestamp):
        async with asyncio.Lock():
            self.ack_pool[id] = {"sent": timestamp}
        self.log(f"Ack info stored for {id}: {self.ack_pool[id]}")

    async def _ack_pool_get(self, id):
        async with asyncio.Lock():
            ack_info = self.ack_pool.get(id, None)
        self.log(f"Retrieving ack info for {id}: {ack_info}")
        return ack_info

    async def _sender(self):
        while True:
            data = await self._out_queue.get()
            if data is None:
                break

            message = {
                "id": str(uuid.uuid4()),
                "type": "message",
                "payload": data,
            }

            self.writer.write((json.dumps(message) + "\n").encode())
            await self.writer.drain()
            send_time_ns = time.time_ns()
            await self._ack_pool_put(message["id"], send_time_ns)
            self.log(f"Sent: {message['id']} at {send_time_ns}")

    async def _ack_manager(self):
        while True:
            data = await self.reader.readline()
            reception_time_ns = time.time_ns()
            if not data:
                self.log("Empty message received, connection might be closed")
                await self.close()
                break
            message = json.loads(data.decode())
            self.log(f"Received: {message} at {reception_time_ns}")

            if message.get('type') == 'ack':
                id = message.get("id")
                ack_info = await self._ack_pool_get(id)
                if ack_info:
                    send_and_back = reception_time_ns - ack_info["sent"]
                    
                    ack_response = {
                        "id": id,
                        "type": "ack",
                        "send_and_ack_time_ns": send_and_back
                    }

                    self.writer.write((json.dumps(ack_response) + "\n").encode())
                    await self.writer.drain()
                    self.log(f"Sent ack response for {id} with send_and_ack_time_ns: {send_and_back}")
            else:
                self.log(f"Unknown message type received: {message.get('type')}")

    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self.log(f"Connection with {self.addr} closed")

if __name__ == "__main__":
    async def main():
        client = Client()
        client.set_addr('localhost', 8888)
        try:
            await client.connect()

            for i in range(5):
                await client.send({"message": f"Hello, server {i}!"})
                await asyncio.sleep(5)
        except ConnectionError:
            print("Connection error occurred")
        finally:
            await client.close()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Client stopped by user")
