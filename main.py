import json, os
import random
import logging
import requests
import threading
import websocket
from rich.console import Console

import time
import delorean
from datetime import datetime, timedelta, timezone

logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s -> %(message)s",
  datefmt="%H:%M:%S",
)


class Discord(object):

  def __init__(self):
    self.tokens = []
    self.songStart = 0
    self.songEnd = 0
    self.songFinish = 0
    self.isNext = False

    with open("data/spotify songs.json", encoding="utf8") as f:
      self.songs = json.loads(f.read())
    with open("data/config.json") as f:
      self.config = json.loads(f.read())
    with open("data/custom status.txt", encoding="utf-8") as f:
      self.status = [i.strip() for i in f]
    with open("data/user bios.txt", encoding="utf-8") as f:
      self.bios = [i.strip() for i in f]
    for line in open("data/tokens.txt"):
      if ":" in line.replace("\n", ""):
        token = line.replace("\n", "").split(":")[0]
      else:
        token = line.replace("\n", "")
      self.tokens.append(token)

    self.ack = json.dumps({"op": 1, "d": None})

    self.activities = {}
    self.spotifyActivities = {}
    self.vcs = []

  def nonce(self):
    date = datetime.now()
    unixts = time.mktime(date.timetuple())
    return str((int(unixts) * 1000 - 1420070400000) * 4194304)

  def random_time(self):
    return (int(
      delorean.Delorean(datetime.now(timezone.utc), timezone="UTC").epoch) *
            1000) - random.randint(100000, 10000000)

  def random(self, data: dict):
    val_sum = sum(data.values())
    d_pct = {k: v / val_sum for k, v in data.items()}
    return next(
      iter(random.choices(population=list(d_pct), weights=d_pct.values(),
                          k=1)))

  def update_bio(self, token: str, bio: any):
    r = requests.patch("https://discord.com/api/v9/users/@me",
                       json={"bio": bio},
                       headers={"authorization": token})
    if r.status_code == 200 or r.status_code == 201:
      logging.info("Updated %s's bio (%s)" % (token[:20], bio))

  def next_song(self, ctoken: str):
    try:
      if self.spotifyActivities.get(token):
        currentActivity = self.spotifyActivities[ctoken]
        songStarting = currentActivity['songStart']
        songEnding = currentActivity['songEnd']
        currentTime = (
          int(delorean.Delorean(datetime.utcnow(), timezone="UTC").epoch) *
          1000)
        songDiff = round(int(songEnding - currentTime) / 1000)
        # print(f'currentTime: {currentTime} | songStart: {songStarting} songEnd: {songEnding} songFinish: {self.songFinish} - diff: {songDiff}')
        if songDiff <= 0:
          # logging.info(f"Updated %s's song {ctoken[:20]}")
          self.isNext = True
          return True
        else:
          self.isNext = False
          return False
    except Exception:
      return True

  def spotifyPayload(self, token: str):
    song = random.choice(self.songs)
    song = song["track"]
    artistIds = []
    for artist in song["artists"]:
      artistIds.append(artist["id"])
    songStart = (
      int(delorean.Delorean(datetime.utcnow(), timezone="UTC").epoch) * 1000)
    songEnd = (int(delorean.Delorean(datetime.utcnow(), timezone="UTC").epoch)
               * 1000) + song["duration_ms"]
    self.spotifyActivities[token] = {
      'songStart': songStart,
      'songEnd': songEnd
    }
    activities = [{
      "type":
      2,
      "name":
      "Spotify",
      "assets": {
        "large_image":
        "spotify:%s" %
        (song["album"]["images"][0]["url"].split("https://i.scdn.co/image/")[1]
         ),
        "large_text":
        song["album"]["name"]
      },
      "details":
      song["name"],
      "state":
      song["artists"][0]["name"],
      "timestamps": {
        "start": songStart,
        "end": songEnd
      },
      "party": {
        "id": "spotify:%s" % (self.nonce())
      },
      "sync_id":
      song["external_urls"]["spotify"].split("https://open.spotify.com/track/")
      [1],
      "flags":
      48,
      "metadata": {
        "album_id": song["album"]["id"],
        "artist_ids": artistIds
      }
    }]

    payload = json.loads(self.activities[token])
    payload["d"]["activities"] = activities

    self.activities[token] = (json.dumps(payload))
    return json.dumps(payload)

  def payload(self, token: str):
    type = self.random(self.config["status"])
    if type == "normal":
      activities = []
    if type == "playing":
      activities = [{
        "type": 0,
        "timestamps": {
          "start": self.random_time()
        },
        "name": self.random(self.config["games"]),
      }]
    if type == "spotify":
      song = random.choice(self.songs)
      song = song["track"]
      artistIds = []
      for artist in song["artists"]:
        artistIds.append(artist["id"])
      songStart = (
        int(delorean.Delorean(datetime.utcnow(), timezone="UTC").epoch) * 1000)
      songEnd = (
        int(delorean.Delorean(datetime.utcnow(), timezone="UTC").epoch) *
        1000) + song["duration_ms"]
      self.spotifyActivities[token] = {
        'songStart': songStart,
        'songEnd': songEnd
      }
      activities = [{
        "type":
        2,
        "name":
        "Spotify",
        "assets": {
          "large_image":
          "spotify:%s" % (song["album"]["images"][0]["url"].split(
            "https://i.scdn.co/image/")[1]),
          "large_text":
          song["album"]["name"]
        },
        "details":
        song["name"],
        "state":
        song["artists"][0]["name"],
        "timestamps": {
          "start": songStart,
          "end": songEnd
        },
        "party": {
          "id": "spotify:%s" % (self.nonce())
        },
        "sync_id":
        song["external_urls"]["spotify"].split(
          "https://open.spotify.com/track/")[1],
        "flags":
        48,
        "metadata": {
          "album_id": song["album"]["id"],
          "artist_ids": artistIds
        }
      }]
    if type == "visual_studio":
      workspace = random.choice(self.config["visual_studio"]["workspaces"])
      filename = random.choice(self.config["visual_studio"]["names"])
      activities = [{
        "type": 0,
        "name": "Visual Studio Code",
        "state": "Workspace: %s" % (workspace),
        "details": "Editing %s" % (filename),
        "application_id": "383226320970055681",
        "timestamps": {
          "start": self.random_time()
        },
        "assets": {
          "small_text":
          "Visual Studio Code",
          "small_image":
          "565945770067623946",
          "large_image":
          self.config["visual_studio"]["images"][filename.split(".")[1]]
        },
      }]

    # logging.info("Updated %s's status (%s)" % (token[:20], type))

    if self.config["update_status"]:
      if self.random(self.config["custom_status"]) == "yes":
        user_status = random.choice(self.status)
        activities.append({
          "type": 4,
          "state": user_status,
          "name": "Custom Status",
          "id": "custom",
          "emoji": {
            "id": None,
            "name": "ð",
            "animated": False
          }
        })

    payload = json.dumps({
      "op": 3,
      "d": {
        "since": 0,
        "activities": activities,
        "status": random.choice(["online", "dnd", "idle"]),
        "afk": False
      }
    })

    self.activities[token] = (payload)
    return payload

  def connect(self, token: str):
    try:
      token = token.split(":")[2]
    except IndexError:
      pass

    try:
      ws = websocket.WebSocket()
      ws.connect("wss://gateway.discord.gg/?v=6&encoding=json")

      data = json.loads(ws.recv())
      heartbeat_interval = data["d"]["heartbeat_interval"]

      device = self.random({"Discord iOS": 25, "Windows": 75})

      ws.send(
        json.dumps({
          "op": 2,
          "d": {
            "token": token,
            "properties": {
              "$os": device,
              "$browser": device,
              "$device": device
            }
          },
          "s": None,
          "t": None
        }))

      ws.send(self.payload(token))

      if self.config["voice"]:
        if self.random(self.config["join_voice"]) == "yes":
          channel = random.choice(self.config["vcs"])
          ws.send(
            json.dumps({
              "op": 4,
              "d": {
                "guild_id": self.config["guild"],
                "channel_id": channel,
                "self_mute": random.choice([True, False]),
                "self_deaf": random.choice([True, False])
              }
            }))
          if self.random(self.config["livestream"]) == "yes":
            ws.send(
              json.dumps({
                "op": 18,
                "d": {
                  "type": "guild",
                  "guild_id": self.config["guild"],
                  "channel_id": channel,
                  "preferred_region": "singapore"
                }
              }))

      if self.config["update_bio"]:
        if self.random(self.config["random_bio"]) == "yes":
          user_bio = random.choice(self.bios)
          self.update_bio(token, user_bio)
        else:
          self.update_bio(token, "")

      while True:
        time.sleep(heartbeat_interval / 1000)
        try:
          self.next_song(token)
          ws.send(self.ack)
          ws.send(self.activities[token])
          if self.isNext == True:
            ws.send(self.spotifyPayload(token))
        except Exception as e:
          trace = []
          tb = e.__traceback__
          while tb is not None:
            trace.append({
              "filename": tb.tb_frame.f_code.co_filename,
              "name": tb.tb_frame.f_code.co_name,
              "lineno": tb.tb_lineno
            })
            tb = tb.tb_next
          print(
            str({
              'type': type(e).__name__,
              'message': str(e),
              'trace': trace
            }))
          return self.connect(token)
    except Exception as e:
      logging.info("Failed to connect (%s)" % (e))
      trace = []
      tb = e.__traceback__
      while tb is not None:
        trace.append({
          "filename": tb.tb_frame.f_code.co_filename,
          "name": tb.tb_frame.f_code.co_name,
          "lineno": tb.tb_lineno
        })
        tb = tb.tb_next
      print(str({'type': type(e).__name__, 'message': str(e), 'trace': trace}))
      return self.connect(token)


if __name__ == "__main__":
  discord = Discord()
  tkc = 0 
  for token in discord.tokens:
    tkc += 1
    print(tkc)
    threading.Thread(target=discord.connect, args=(token, )).start()
  logging.info("All tokens are online!")
  time.sleep(1000)
  os.system("kill 1")
