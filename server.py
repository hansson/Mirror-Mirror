import BaseHTTPServer
import Cookie
import httplib2
import StringIO
import urlparse
import sys
import json
import datetime
import os.path
import urllib
import soco

from apiclient.discovery import build
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.file import Storage
from lxml import html

class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
  """Child class of BaseHTTPRequestHandler that only handles GET request."""
  runPath = sys.argv[0]
  runPath = runPath[:len(runPath)-9]

  def do_GET(self):
    """Handler for GET request."""
    print '\nNEW REQUEST, Path: %s' % (self.path)
    print 'Headers: %s' % self.headers

    self.respond_with_file()


  def respond_with_file(self):
    requestedFile = self.runPath + self.path[1:]
    if os.path.isfile(requestedFile):
      self.send_file(requestedFile)
    elif requestedFile.endswith('excuse.json'):
    #Get programming excuse
      url = "http://programmingexcuses.com/"
      page = html.fromstring(urllib.urlopen(url).read())

      for link in page.xpath("//a"):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write('{"excuse":"%s"}\n' % link.text)
        return
    elif requestedFile.endswith('sonos.json'):
    #Get information from sonos system
      speakers = soco.discover()
      sonos_info = None
      for speaker in speakers:
       tmp_sonos_info = speaker.get_current_track_info()
       transport_info = speaker.get_current_transport_info()
       if tmp_sonos_info['artist'] and transport_info['current_transport_state'] == 'PLAYING':
         sonos_info = tmp_sonos_info
         break
      if sonos_info:
        artist = sonos_info['artist']
        title = sonos_info['title']
        art = sonos_info['album_art']
        duration = sonos_info['duration']
        position = sonos_info['position']
      self.send_response(200)
      self.send_header('Content-type', 'application/json')
      self.send_header('Cache-Control', 'no-cache')
      self.end_headers()
      if sonos_info:
        self.wfile.write('{"status":"on", "artist":"%s","title":"%s","art":"%s","duration":"%s","position":"%s"}\n' % (artist, title, art, duration, position))
      else:
        self.wfile.write('{"status":"off"}')
    else:
      """Responds to the current request that has an unknown path."""
      self.send_response(404)
      self.send_header('Content-type', 'text/plain')
      self.send_header('Cache-Control', 'no-cache')
      self.end_headers()
      self.wfile.write(
        'This path is invalid %s\n\n' % requestedFile)

  def send_file(self,requestedFile):
    self.send_response(200)
    self.send_header('Content-type', self.resolve_content_type(requestedFile))
    self.send_header('Cache-control', 'no-cache')
    self.end_headers()
    f = open(requestedFile, 'r')
    #This is pretty unsafe! Never do this outside the mirror :D
    self.wfile.write(f.read())

  def resolve_content_type(self, requestedFile):
    if requestedFile.endswith('.html'):
      return 'text/html; charset=utf-8'
    elif requestedFile.endswith('.css'):
      return 'text/css; charset=utf-8'
    elif requestedFile.endswith('.js'):
      return 'application/javascript'
    elif requestedFile.endswith('.jpg'):
      return 'image/jpeg'
    else:
      return 'text/plain; charset=utf8'

def main():
  try:
    server = BaseHTTPServer.HTTPServer(('', 8080), RequestHandler)
    print 'Starting server. Use Control+C to stop.'
    server.serve_forever()
  except KeyboardInterrupt:
    print 'Shutting down server.'
    server.socket.close()

if __name__ == '__main__':
  main()
