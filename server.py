# Copyright 2012 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
    elif os.path == "excuse.json":
      url = "http://programmingexcuses.com/"
      page = html.fromstring(urllib.urlopen(url).read())

      for link in page.xpath("//a"):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write('{"excuse":"%s"' % link.text)
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
