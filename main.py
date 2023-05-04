import random
import threading
import time
import os
import asyncio

from bleak import BleakScanner
from advertisement import advertise

UNKNOWN_LEADER = 256
SLEEP_TIME = 10

async def main():
  myID = 0
  PreviousLeader = -1
  LeaderName = "ME"
  Threshold = 80
  BatteryUsage = 80

  while True:
    emit = threading.Thread(target=advertise, args=(myID, BatteryUsage, Threshold, 10,))
    print("Start emitting...")
    emit.daemon = True
    emit.start()

    print("Start discovering...")
    devices = await BleakScanner.discover(timeout=10)
    if BatteryUsage < Threshold:
      LeaderID = UNKNOWN_LEADER
    else :
      LeaderID = myID
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
    
    PreviousLeader = LeaderID
    if LeaderID == UNKNOWN_LEADER:
      BatteryUsage -= 10
      LeaderID = PreviousLeader
      if PreviousLeader == myID:
        Threshold -=10
    
    print("The Leader address is : " + str(LeaderName) + " and it's  Id : " + str(LeaderID))
    print("Battery threshold is : " + str(Threshold))
    print("Current battery: " + str(BatteryUsage))
    time.sleep(10)



if __name__ == "__main__":
  asyncio.run(main())