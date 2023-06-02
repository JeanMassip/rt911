import threading
import time
import asyncio
import OpenSSL
import itertools

from math import ceil
from bleak import BleakScanner
from advertisement import advertise

"""
Structure d'un fragment de message :
| fragment courant (1o) | total fragments (1o) |    payload du fragment ( xxx o)    |

Liste des fonctions:
  - sign_message -> signe les messages
  - verify_signature -> vérifie la validité de la signature d'un message
  - send_data -> fonction d'envoi de message
  - on_device_discovery_callback -> callback de lecture des devices BLE
  - main -> contient le code du concensus
"""

UNKNOWN_LEADER = 256
SLEEP_TIME = 10

# Buffer pour les messages en cours de reconstruction
messages_buffer = {}

# Contients les messages complètement reconstruit
messages_reconstruit = {}


# Fonction qui permet de signer les messages
def sign_message(message):
  # Ouverture de la clé
  key_file = open("./privkey.pem", "r")
  key = key_file.read()
  key_file.close()

  # signature du message
  privateKey = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, key, b'toto')
  m = OpenSSL.crypto.sign(privateKey, message, "SHA256")
  return m


# Fonction de vérification des signatures
def verify_signature(signature, message):
  # Récupération du certificat dans son fichier
  cert_file = open("./monCertif.pem", "r")
  cert = cert_file.read()
  cert_file.close()

  # Chargement du certificat
  certif = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
  
  # Vérification de la signature du message
  return OpenSSL.crypto.verify(certif, signature, message, "SHA256")


# Fonction de découpage et d'advertising des fragments de messages
def send_data(id, batteryUsage):
  # Récupération des données à envoyer ainsi que la signature correspondante
  data = [id, batteryUsage]
  signature = sign_message(bytes(data))
  data = data + list(signature)

  start = 0
  end = len(data)
  step = 10

  # Calcul du nombre de fragment
  max_message = ceil(len(data) / step)
  counter = 1

  # Boucle qui régit le nombre d'envoi pour une émission de message
  for j in range(1,10):
    counter = 1
    # Boucle pour l'envoie des fragments de messages dans l'ordre
    for i in range(start, end, step):
        x = i

        # Découpage du fragment
        message = [counter, max_message] + data[x:x+step]

        # Conversion du fragment en bytes
        chunk_bytes = bytes(message)
        counter += 1

        # Lancement de l'advertising
        advertise(chunk_bytes, 0.1)


# Fonction Call-back si changement des propriétés d'un device lors du scan
# S'occupe également de la reconstitution des messages
def on_device_discovery_callback(device, advertisement_data):
  # Entre dans la fonction uniquement si l'appareil qui a déclancher le call-back possède notre ID en nom d'affichage
  if device.name == 'BJPT':
    # Extraction d'une partie du message dans l'UUID du device
    data = list(advertisement_data.service_data['00009999-0000-1000-8000-00805f9b34fb'])
    
    # Récupération de l'adresse pour savoir quel device envoie ses fragments
    addr = device.address

    # Récupération du numéro du fragment courant et du total pour le message de ce device
    fragment_number = data[0]
    fragment_total = data[1]

    # Remplacement du fragment du message dans le buffer
    if not addr in messages_buffer:
        messages_buffer[addr] = [-1] * fragment_total
    messages_buffer[addr][fragment_number-1] = data[2:]

    # Si tous les fragments sont récupérés
    if all(i!= -1 for i in messages_buffer[addr][0:fragment_total]) :
      # Concaténation des fragments du message
      msg_tmp = list(itertools.chain.from_iterable(messages_buffer[addr][0:fragment_total]))

      print("message reconstruit ! ~ ", messages_reconstruit[addr], " @ ", addr )
      messages_buffer[addr] = [-1] * fragment_total

      # Vérification de la signature du message
      if verify_signature(messages_reconstruit[:1],messages_reconstruit[2:]):
        messages_reconstruit[addr] = msg_tmp
      else :
        print("Signature message invalide", addr)


# Fonction main, lance les fonction d'envoi, de réception.
# Contient le code de l'algorithme de concensus
async def main():
  # Déclarations
  myID = 0
  PreviousLeader = -1
  LeaderName = "ME"
  Threshold = 80
  BatteryUsage = 80
  
  while True:
    # Création du thread d'émission avec la fonction send_data
    emit = threading.Thread(target=send_data, args=(myID, BatteryUsage,))
    print("Start emitting...")
    emit.daemon = True
    emit.start()

    # Démarrage du scanner avec appel de la fonction callback si changement d'un device
    print("Start discovering...")
    scanner = BleakScanner(on_device_discovery_callback)
    
    # On redémarrage le scanner toutes les 10 seconde à cause du timeout forcé
    i = 0
    while (i < 6):
      scanner.start()
      time.sleep(10)
      scanner.stop()
      i += 1


    # --- Début de l'algorithme de concencus ---

    # Si batterie courante sous le seuil, 
    if BatteryUsage < Threshold:
      LeaderID = UNKNOWN_LEADER
    else :
      LeaderID = myID

    # On boucle sur les différents messages reçus pour choisir le leader
    for addr, data in messages_reconstruit:
      id = data[0]
      battery = data[1]

      # Vérification du niveau de batterie
      if battery >= Threshold:
        # Choix 
        if id < LeaderID:
          LeaderID = id
          LeaderName = addr
          print("Threshold is: " + str(Threshold))
    
    # Si aucun candidat au dessus du seuil de batterie
    # reprise de l'ancien leader ainsi que descente du seuil.
    if LeaderID == UNKNOWN_LEADER:
      LeaderID = PreviousLeader
      Threshold -= 10
    
    # Si élu, simulation de la descente du niveau de batterie 
    if LeaderID == myID:
      BatteryUsage -= 10

    # Mise en mémoire du nouveau leader
    PreviousLeader = LeaderID

    # Affichage du résultat
    print("The Leader address is : " + str(LeaderName) + " and it's  Id : " + str(LeaderID))
    print("Battery threshold is : " + str(Threshold))
    print("Current battery: " + str(BatteryUsage))
    
    # Attente avant le prochain tour
    time.sleep(60)


if __name__ == "__main__":
  asyncio.run(main())