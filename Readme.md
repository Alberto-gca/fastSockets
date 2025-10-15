## Porpose
This library is a general porpouse abstraction layer for asyncronous sockets.

It`s made for creating a client-server pair, sendig messages and being able to measure latency of these messages. This need comes from the V2X project.

## ROS compatibility
The functionalities this library offers are intended to be compatible with ROS1 and ROS2 at any version.

The procedure to achive the non blocking behavior with ros is as follows:

```python
import rospy
import fastSocket

client = fastSocket.Client()

def thecallback(msg):
    client.send(msg)
    ...

def ros_main():
    rospy.init_node("node_name")
    sub = rospy.Subscriber("/onetopic", messagetype, thecallback)

def main():
    threading.Thread(target=ros_main, daemon=True).start()
    client.run()

if __name__ == '__main__':
    main()

```
This runs the socket in an asyncrhonous way while runing the ROS node at a separate thread, allowing non-bloking socket and ROS normal operation.

## Structure

```
asyncsockets/
│
├── __init__.py
├── Client.py
├── fastSocket.py
├── Readme.md
└── Server.py
```

## Messages

Transmited messages are intended to be Json. This package adds metadata to the messages transmited in order to calculate delay and acknowledge the information arrival.

The transmision schema is as follows:
```
            Client          Server
            |                |
            |---Menssage---->|          Client sends msg to the server.
        ↑   |                |               msg: {id:<uuid>, 
        |   |                |                     type:message, 
    T1  |   |                |                     data}
        ↓   |                |          
            |<----ACK--------|          Servidor responde con ACK
            |                |   ↑           msg: {id:<uuid>,
            |                |   |                 type:ack}
            |                |   | T2 
            |                |   ↓  
            |----ACK-------->|          Cliente responde al ACK con su propio ACK
            |                |               msg: {id:<uuid>,
                                                   type:ack,
                                                   send_and_ack_time_ns: T1}
  ```
The schema followed by the fastSocket makes possible to calculate the time it takes for the Message to arrive:
```Math
    T_{transmit} = T_1 - T_2 / 2

```

This meand that the time it takes to the message to arrive the server is equal to the time it takes to the client to receive the server acknowledge minus half the time it takes to the server to receive the client acknowledge (it is suposed to be the same time it took for the server ack to reach the client from the server, so sould be the same as substracting the server ack time).

Messages have the following json format:
```json
{
    "id": "<uuid>",                     # Unic identifyer 
    "type": "message" | "ack",          # Type of the message
    "payload": "...",                   # for message type only
    "send_and_ack_time_ns": 1234567890  # for ack from client to server only
}
```
Every field of the messages is been automaticly set. The only settable field is payload. Also ack messages are automaticaly managed.
