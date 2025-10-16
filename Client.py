from fastSocket import FastSocket
import asyncio
import json
import uuid
import time

mensajote = {
    "measurementDeltaTime": 996.0,
    "position": {
        "xCoordinate": {
            "value": 0.09388985173844638,
            "confidence": 1
        },
        "yCoordinate": {
            "value": 0.06514550737208115,
            "confidence": 1
        },
        "zCoordinate": {
            "value": 0.0,
            "confidence": 1
        }
    },
    "objectId": 82,
    "velocity": {
        "polarVelocity": {
            "velocityMagnitude": {
                "speedValue": 0,
                "speedConfidence": 0
            },
            "velocityDirection": {
                "value": 0,
                "confidence": 0
            }
        },
        "cartesianVelocity": {
            "xVelocity": {
                "value": 16383,
                "confidence": 1
            },
            "yVelocity": {
                "value": 16383,
                "confidence": 1
            },
            "zVelocity": {
                "value": 16383,
                "confidence": 126
            }
        }
    },
    "acceleration": {
        "polarAcceleration": {
            "accelerationMagnitude": {
                "accelerationMagnitudeValue": 0,
                "accelerationConfidence": 0
            },
            "accelerationDirection": {
                "value": 0,
                "confidence": 0
            }
        },
        "cartesianAcceleration": {
            "xAcceleration": {
                "value": 161,
                "confidence": 1
            },
            "yAcceleration": {
                "value": 161,
                "confidence": 1
            },
            "zAcceleration": {
                "value": 161,
                "confidence": 1
            }
        }
    },
    "angles": {
        "zAngle": {
            "value": 3598.128858933496,
            "confidence": 95
        }
    },
    "objectDimensionZ": {
        "value": 256,
        "confidence": 1
    },
    "objectDimensionY": {
        "value": 256,
        "confidence": 1
    },
    "objectDimensionX": {
        "value": 256,
        "confidence": 1
    },
    "objectAge": 46.0598892923465,
    "objectPerceptionQuality": 15,
    "classification": [
        {
            "objectClass": {
                "otherSubClass": 0
            },
            "confidence": 101
        }
    ]
}

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

            send_time_ns = time.time_ns()
            self.writer.write((json.dumps(message) + "\n").encode())
            await self.writer.drain()
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
        import socket
        client = Client(logfunc=None)
        client.set_addr('localhost', 8888)
        try:
            await client.connect()

            for i in range(1000):
                # await client.send({"message": f"Hello {i} from {socket.gethostname()}!"})
                await client.send(mensajote)
                await asyncio.sleep(0.005)
        except ConnectionError:
            print("Connection error occurred")
        finally:
            await client.close()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Client stopped by user")


