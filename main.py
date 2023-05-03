import random
import threading
import time
import os
import asyncio

from bleak import BleakScanner
from advertisement import advertise

async def main():
    myID = 0
    LeaderID = myID
    LeaderName = "ME"
    Threshold = 80

    emit = threading.Thread(target=advertise, args=(30,))
    print("Start emitting...")
    emit.start()

    print("Start discovering...")
    devices = await BleakScanner.discover(timeout=10)
    for d in devices:
        if d.name == 'BJPT':
            data = d.details['props']['ManufacturerData'][0xffff]
            id = data[0]
            battery = data[1]
            if battery >= Threshold:
                if id < LeaderID:
                    LeaderID = id
                    LeaderName = d.address
    
    print("The Leader is : " + str(LeaderName) + " Id : " + str(LeaderID))


if __name__ == "__main__":
    asyncio.run(main())