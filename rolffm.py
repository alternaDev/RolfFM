#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys, random, datetime
import argparse
import time
import logging
import logging.handlers
import signal
import RPi.GPIO as GPIO
from thread import start_new_thread
import SimpleHTTPServer
import SocketServer
import eyed3
import json
import subprocess

LOG_FILENAME = "./RolfFM.log"

BASE_FOLDER = "/media/network/wolfgang/USB2-0-FlashDisk-00"
FOLDER_A = BASE_FOLDER + "/Jean"
FOLDER_B = BASE_FOLDER + "/Chris"
FOLDER_SPEECH = BASE_FOLDER + "/Speech"
#RolfFM christmas
FOLDER_CHRISTMAS = BASE_FOLDER + "/Christmas"
SONG_REPEAT_TIME = 12*60*60

MODE_MIXED = 0
MODE_A = 1
MODE_B = 2

PLAYING_A = 0
PLAYING_B = 1
PLAYING_SPEECH = 2

root = logging.getLogger()
root.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)

stopped = False
mode = MODE_MIXED
mixed_playing_time = 0
current_playing = PLAYING_A
button_pressed = False

current_playback_process = None

current_playing_time = 0
current_song_name = ""
current_song_artist = ""
current_song_album = ""
current_song_length = -1

history = {} 

class ServerHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
  def do_GET(self):
    self.send_response(200)
    self.send_header('Content-Type', 'application/json')
    self.end_headers()
    
    #response = u"{ 'song_time': " + str(current_playing_time) + u", 'song_length': " + str(current_song_length) + u", 'song_name': '" + current_song_name + u"', 'song_artist': '" + current_song_artist + u"', 'song_album': '" + current_song_album + u"'}"
    response = { "song_time": current_playing_time, "song_length": current_song_length, "song_name": current_song_name, "song_artist": current_song_artist, "song_album": current_song_album}
    self.wfile.write(json.dumps(response))

def recursive_files(dir):
  for path, _, fnames in os.walk(dir, True):
    for fname in fnames:
      if not fname.startswith(".") and fname.endswith(".mp3") or fname.endswith(".wav") or fname.endswith(".m4a"):
        yield os.path.join(path, fname)

def random_choice(iterable):  
  l = list(iterable)
  pick = "" 
  picked = random.randrange(len(l))
  pick = l[picked]
  
  while current_playing != PLAYING_SPEECH and is_old_song(pick):
    
   picked = random.randrange(len(l))
   pick = l[picked]
  
  return pick  

def skip_song():
  global button_pressed

  if button_pressed and GPIO.input(4):
    button_pressed = False
    return False
  
  if not GPIO.input(4) and not button_pressed:
    button_pressed = True
    return True
  
  
  return False

def is_old_song(songname):
  if current_playing != PLAYING_SPEECH:    
    
    global history    
    if songname in history:
     
      last_played = time.time() - history[songname] 
     
      if(last_played < SONG_REPEAT_TIME):
        return True
      else:
        history[songname] = time.time();
        return False
        
    else:      
      history[songname] = time.time()
      return False
  
  

def play_audio(path, ignoreStopped=True):
  global stopped
  global current_playing
  global mixed_playing_time
  global current_playing_time
  global current_song_name
  global current_song_artist
  global current_song_album
  global current_song_length
  global current_playback_process
  
  myStopped = False
  if not ignoreStopped:
    myStopped = stopped  
  current_song_name = path
  current_song_artist = ""
  current_song_album = ""
  current_song_length = 0
  id3Data = eyed3.load(path)
  if id3Data.tag and id3Data.tag.title:
    current_song_name = id3Data.tag.title
    current_song_artist = id3Data.tag.artist
    current_song_album = id3Data.tag.album
    current_song_length = id3Data.info.time_secs

  nau = time.time()
  DEVNULL = open(os.devnull, 'wb')
  current_playback_process = subprocess.Popen(["play", path], stdout=DEVNULL, stderr=DEVNULL)

  while current_playback_process.poll() is None and not myStopped:
    current_playing_time = time.time() - nau
    
    if not ignoreStopped:
      myStopped = stopped
    
    if skip_song():
      current_playback_process.terminate()
      break
    time.sleep(.1)
    continue
  
  if current_playing == PLAYING_A:
    mixed_playing_time -= time.time() - nau
  elif current_playing == PLAYING_B:
    mixed_playing_time += time.time() - nau


def signal_handler(signal, frame):
  global stopped
  global current_playback_process

  stopped = True
  if current_playback_process is not None:
    current_playback_process.terminate()
  play_audio(FOLDER_SPEECH + "/Speech 3.mp3", False)
  logging.info("Exiting RolfFM.")
  print "Peace out!"

def main(argv):

  global mode
  global current_playing
  global mixed_playing_time
  global stopped  
  
  parser = argparse.ArgumentParser(description="RolfFM Music Playback Service")
  parser.add_argument("-m", "--mode", help="Playback Mode (default 'mixed')")
  parser.add_argument("-l", "--logfile", help="file to write log to (default '" + LOG_FILENAME + "')")
  
  args = parser.parse_args()

  log_file = LOG_FILENAME

  if args.logfile:
    log_file = args.logfile

  fileHandler = logging.handlers.TimedRotatingFileHandler(log_file, when='midnight', backupCount=5)
  fileHandler.setFormatter(formatter)
  root.addHandler(fileHandler)

  logging.info("Starting RolfFM.")


  GPIO.setmode(GPIO.BCM)
  GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    
  signal.signal(signal.SIGTERM, signal_handler)
  signal.signal(signal.SIGINT, signal_handler)
  
  if args.mode == 'A' or args.mode == 'MODE_A':
    mode = MODE_A
    logging.info('Only playing music from %s', FOLDER_A)
  elif args.mode == 'B' or args.mode == 'MODE_B':
    mode = MODE_B
    logging.info('Only playing music from %s', FOLDER_B)
  else:
    logging.info('Playing mixed music.')
      
  folder = FOLDER_A  
  
  logging.info("Init Finished, entering Loop.")

  Handler = ServerHandler
  httpd = SocketServer.TCPServer(("", 8000), Handler)
  start_new_thread(httpd.serve_forever, ())
  date = datetime.date.today()

  while True and not stopped:
    try:
      if random.randrange(2) != -1:
        current_playing = PLAYING_SPEECH
        speech = random_choice(recursive_files(FOLDER_SPEECH))     
        logging.info("Playing Speech %s", speech)
        play_audio(speech)
    
      if stopped:
        break

      logging.info("Mixed Playing time: %s", str(mixed_playing_time))  
    
      if mode == MODE_A:
        folder = FOLDER_A
        current_playing = PLAYING_A
    
      elif mode == MODE_B:
        folder = FOLDER_B
        current_playing = PLAYING_B
    
      else: 
        if mixed_playing_time >= 180:
          current_playing = PLAYING_A
          folder = FOLDER_A        
        elif mixed_playing_time <= -180:
          current_playing = PLAYING_B
          folder = FOLDER_B        
        elif folder == FOLDER_A:
          current_playing = PLAYING_B
          folder = FOLDER_B
        elif folder == FOLDER_B:
          current_playing = PLAYING_A
          folder = FOLDER_A
     
      #rolffm christmas
      if(random.randint(0,4) == 1 and date.month == 12 and date.day <= 28):
        song = random_choice(recursive_files(FOLDER_CHRISTMAS))
        logging.info("Playing christmas song %s in mode %s", song, mode)
        play_audio(song)
      else: 
        song = random_choice(recursive_files(folder))
        logging.info("Playing song %s in mode %s", song, mode)
        play_audio(song)
    except Exception, e:
      logging.exception(e)
  print "Tschüss"
if __name__ == "__main__":
  main(sys.argv[1:]) 
 
