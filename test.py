from PIL import Image 
import os 
import time 
import sys 
from rgbmatrix import RGBMatrix, RGBMatrixOptions 
from PIL import Image

from jellyfin_apiclient_python.client import JellyfinClient

def getCurrentPlayingImagePath():
    sessionInfo = client.jellyfin.get_sessions()
    #print (sessionInfo)
    imageInfoFromID = client.jellyfin.get_images(sessionInfo[0]["NowPlayingItem"]["AlbumId"])
    return imageInfoFromID[0]["Path"]

def convertImage(image):
    image1 = image.copy()
    image1 = image1.resize((128, 128))
    image1.save(r'poster_64.ppm')

def editDirectory(inputDir):
    newDir = "/home/pi/music/Artist" + inputDir[13:]
    #print(newDir)
    print(inputDir)
    return newDir
try:
   #Some client initialization
   client = JellyfinClient()
   client.config.app('LED Album Display', '0.0.1', 'BingBong', '2326')
   client.config.data["auth.ssl"] = True

   try:
      #Local Host
      client.auth.connect_to_address('http://192.168.254.125:8096')
      client.auth.login('http://192.168.254.125:8096', 'sebgra518', 'doogie1004')
   except:
      #Tailscale
      client.auth.connect_to_address('http://100.88.194.67:8096')
      client.auth.login('http://100.88.194.67:8096', 'sebgra518', 'doogie1004')

   #Configuration for the matrix
   options = RGBMatrixOptions()
   options.rows = 64
   options.cols = 64
   options.chain_length = 2
   options.parallel = 2
   options.brightness = 40
   options.hardware_mapping = 'regular'  # If you have an Adafruit HAT: 'adafruit-hat'
   options.limit_refresh_rate_hz = 60
   options.gpio_slowdown = 2
   options.multiplexing = 0

   print(getCurrentPlayingImagePath())

   try:
      #Get and edit image
      path = getCurrentPlayingImagePath()
   except:
      print("No song playing")
      time.sleep(5)
      sys.exit(0)
   newDir = editDirectory(path)
   print(newDir) #TMP
   image = Image.open(newDir.replace("\\", "/")) #Where the program has issues
   convertImage(image)

   matrix = RGBMatrix(options = options) #what seems to cause the issue

   #Display Image
   image.thumbnail((matrix.width, matrix.height))
   matrix.SetImage(image.convert('RGB'))
   time.sleep(60)
   image.close()
   matrix.Clear()
   sys.exit(0)
except KeyboardInterrupt:
    sys.exit(0)
