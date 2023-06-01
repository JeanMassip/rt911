import random
import threading
import time
import os
import asyncio
import OpenSSL

from math import ceil
from bleak import BleakScanner
from advertisement import advertise

UNKNOWN_LEADER = 256
SLEEP_TIME = 10

messages_buffer = []
messages_reconstruits = []

def on_device_discovery_callback(device, advertisement_data):
  print(str(device) + ' ' + str(advertisement_data))

def generate_keys():
  keypair = OpenSSL.crypto.PKey()
  keypair.generate_key(type=OpenSSL.crypto.TYPE_RSA, bits=2048)
  print("toto", keypair)

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
  max_message = ceil(len(data) / step)
  counter = 1
  for i in range(start, end, step):
      x = i
      chunk = [counter, max_message] + data[x:x+step]
      print("chunk en cours ~ ", chunk)
      chunk_bytes = bytes(chunk)
      print(chunk_bytes)
      counter += 1
      advertise(chunk_bytes, 1)


def reconstruction_message(device, advertisement_data):
  if device.name == 'BJPT':
    print("Reconstruction message")
    data = advertisement_data['ManufacturerData'][0xffff]
    addr = device.address
    fragment_number = data[0]
    fragment_total = data[1]

    # Remplacement du fragment du message 
    messages_buffer[addr][fragment_number] = data[2:]

    # Test si message complet
    if all(messages_buffer[0:fragment_total]):
      messages_reconstruits[addr] = messages_buffer[addr][0:fragment_total].concatenate()
      print("message reconstruit ! ~ ", messages_reconstruits[addr], " @ ", addr )
      # Nettoyage buffer si message complet
      messages_buffer[addr] = []

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
      emit = threading.Thread(target=send_data, args=(myID, BatteryUsage,))
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