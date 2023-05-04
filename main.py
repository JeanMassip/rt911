import random
import threading
import time
import os
import asyncio

from bleak import BleakScanner
from advertisement import advertise

async def main():
  myID = 0
  PreviousLeader = -1
  LeaderID = myID
  LeaderName = "ME"
  Threshold = 80
  BatteryUsage = 80

  while True:
    emit = threading.Thread(target=advertise, args=(myID, BatteryUsage, Threshold, 40,))
    print("Start emitting...")
    emit.start()

    print("Start discovering...")
    devices = await BleakScanner.discover(timeout=40)
    for d in devices:
        if d.name == 'BJPT':
            data = d.details['props']['ManufacturerData'][0xffff]
            id = data[0]
            battery = data[1]
            if battery >= Threshold:
                if id < LeaderID:
                    LeaderID = id
                    LeaderName = d.address
                    Threshold = data[2]
                    print("Threshold is: " + str(Threshold))
    
    PreviousLeader == LeaderID
    if LeaderID == myID:
        BatteryUsage -= 10
        if PreviousLeader == myID:
            Threshold -=10
  
  print("The Leader address is : " + str(LeaderName) + " and it's Id : " + str(LeaderID))
  time.sleep(30)



if __name__ == "__main__":
    asyncio.run(main())