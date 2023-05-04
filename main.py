import random
import threading
import time
import os
import asyncio
import OpenSSL

from bleak import BleakScanner
from advertisement import advertise

UNKNOWN_LEADER = 256
SLEEP_TIME = 10

def on_device_discovery_callback(device, advertisement_data):
  print(str(device) + ' ' + str(advertisement_data))

def sign_message(message):
  key_file = open("./privkey.pem", "r")
  key = key_file.read()
  key_file.close()
  passphrase = bytearray().extend(map(ord, "toto"))

  privateKey = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, key, b'toto')
  m = OpenSSL.crypto.sign(privateKey, message, "SHA256")
  return m

def verify_signature(signature, message):
  cert_file = open("./monCertif.pem", "r")
  cert = cert_file.read()
  cert_file.close()

  certif = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)

  return OpenSSL.crypto.verify(certif, signature, message, "SHA256")

def send_data(id, batteryUsage):
  data = [id, batteryUsage]
  signature = sign_message(bytes(data))
  data = data + list(signature)
  print(data)
  start = 0
  end = len(data)
  step = 22
  for i in range(start, end, step):
      x = i
      chunk = data[x:x+step]
      chunk_bytes = bytes(chunk)
      print(chunk_bytes)
      advertise(chunk_bytes)


def reconstruction_message():
  print("Reconstruction message")

async def main():
  myID = 0
  PreviousLeader = -1
  LeaderName = "ME"
  Threshold = 80
  BatteryUsage = 80
  okay = False

  send_data(myID, BatteryUsage)
  if okay:
    while True:
      emit = threading.Thread(target=advertise, args=(myID, BatteryUsage, Threshold, 10,))
      print("Start emitting...")
      emit.daemon = True
      emit.start()

      print("Start discovering...")
      scanner = BleakScanner(detection_callback=device_found, )
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
                print("Threshold is: " + str(Threshold))
      
      if LeaderID == UNKNOWN_LEADER:
        LeaderID = PreviousLeader
        Threshold -= 10
      
      if LeaderID == myID:
        BatteryUsage -= 10

      PreviousLeader = LeaderID

      print("The Leader address is : " + str(LeaderName) + " and it's  Id : " + str(LeaderID))
      print("Battery threshold is : " + str(Threshold))
      print("Current battery: " + str(BatteryUsage))
      time.sleep(10)



if __name__ == "__main__":
  asyncio.run(main())