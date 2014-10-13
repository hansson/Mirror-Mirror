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

from apiclient.discovery import build
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.file import Storage

class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
  """Child class of BaseHTTPRequestHandler that only handles GET request."""

  # Create a flow object. This object holds the client_id, client_secret, and
  # scope. It assists with OAuth 2.0 steps to get user authorization and
  # credentials. For this example, the client ID and secret are command-line
  # arguments.
  flow = OAuth2WebServerFlow(sys.argv[1],
                             sys.argv[2],
                             'https://www.googleapis.com/auth/calendar',
                             redirect_uri='http://mirroronthewall.se:8080/')
  runPath = sys.argv[0]
  runPath = runPath[:len(runPath)-9]
  credentialsPath = sys.argv[3]

  def do_GET(self):
    """Handler for GET request."""
    print '\nNEW REQUEST, Path: %s' % (self.path)
    print 'Headers: %s' % self.headers

    if self.path.startswith('/?user='):
      self.handle_initial_url()
    elif self.path.startswith('/?code='):
      self.handle_redirected_url()
    else:
      self.respond_with_file()

  def send_template(self, calendarData):
    """Build and send index.html template"""


  def handle_initial_url(self):
    """Handles the initial path."""
    user = self.get_user_from_url_param()
    credentials = self.get_credentials(user)

    if credentials is None or credentials.invalid:
      self.respond_redirect_to_auth_server(user)
    else:
      try:
        calendar_output = self.get_calendar_data(credentials)
        self.respond_calendar_data(calendar_output)
      except AccessTokenRefreshError:
        # This may happen when access tokens expire. Redirect the browser to
        # the authorization server
        self.respond_redirect_to_auth_server(user)

  def handle_redirected_url(self):
    """Handles the redirection back from the authorization server."""
    code = self.get_code_from_url_param()
    user = self.get_user_from_cookie()
    credentials = RequestHandler.flow.step2_exchange(code)
    self.save_credentials(user, credentials)
    calendar_output = self.get_calendar_data(credentials)
    self.respond_calendar_data(calendar_output)

  def respond_redirect_to_auth_server(self, user):
    """Respond to the current request by redirecting to the auth server."""
    uri = RequestHandler.flow.step1_get_authorize_url()
    print 'Redirecting %s to %s' % (user, uri)
    self.send_response(301)
    self.send_header('Cache-Control', 'no-cache')
    self.send_header('Location', uri)
    self.send_header('Set-Cookie', 'user=%s' % user)
    self.end_headers()

  def respond_with_file(self):
    requestedFile = self.runPath + self.path[1:]
    if os.path.isfile(requestedFile):
      self.send_file(requestedFile)
    else:
      """Responds to the current request that has an unknown path."""
      self.send_response(404)
      self.send_header('Content-type', 'text/plain')
      self.send_header('Cache-Control', 'no-cache')
      self.end_headers()
      self.wfile.write(
        'This path is invalid %s\n\n' % requestedFile)

  def respond_calendar_data(self, calendar_output):
    """Responds to the current request by writing calendar data to stream."""
    self.send_response(200)
    self.send_header('Content-type', 'text/plain; charset=utf-8')
    self.send_header('Cache-Control', 'no-cache')
    self.end_headers()
    self.wfile.write(calendar_output)

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

  def get_calendar_data(self, credentials):
    """Given the credentials, returns calendar data."""
    output = StringIO.StringIO()

    http = httplib2.Http()
    http = credentials.authorize(http)

    service = build('calendar', 'v3', http=http)

    calendars = self.get_calendars(service)
  
    today = datetime.datetime.now().isoformat() + '+02:00'
    inAWeek = (datetime.datetime.now() + datetime.timedelta(days=7)).isoformat() + '+01:00'
    eventList = []
    for calendar in calendars:
      eventList = self.get_events(service, calendar, eventList, today, inAWeek)

    output.write(json.dumps(eventList))
    return output.getvalue()
  
  def get_events(self, service, calendar, eventList, today, inAWeek):
    request = service.events().list(calendarId=calendar,timeMin=today,timeMax=inAWeek,singleEvents='true')
    while request != None:
      response = request.execute()
      for event in response.get('items', []):
        if event.get('status') != u'cancelled':
          date = event.get('start').get('dateTime',event.get('start').get('date'))
          currentEvent = {}
          currentEvent['summary'] = event.get('summary')
          currentEvent['date'] = date
          eventList.append(currentEvent)

      request = service.events().list_next(request, response)
    return eventList
  
  def get_calendars(self, service):
    calendars = []
    request = service.calendarList().list()
    while request != None:
      response = request.execute()
      for calendar in response.get('items',[]):
        calendars.append(calendar.get('id',''))
      request = service.calendarList().list_next(request,response)

    return calendars
  
  def get_credentials(self, user):
    """Using the fake user name as a key, retrieve the credentials."""
    storage = Storage(self.credentialsPath + 'credentials-%s.dat' % (user))
    return storage.get()

  def save_credentials(self, user, credentials):
    """Using the fake user name as a key, save the credentials."""
    storage = Storage(self.credentialsPath + 'credentials-%s.dat' % (user))
    storage.put(credentials)

  def get_user_from_url_param(self):
    """Get the user query parameter from the current request."""
    parsed = urlparse.urlparse(self.path)
    user = urlparse.parse_qs(parsed.query)['user'][0]
    return user

  def get_user_from_cookie(self):
    """Get the user from cookies."""
    cookies = Cookie.SimpleCookie()
    cookies.load(self.headers.get('Cookie'))
    user = cookies['fake_user'].value
    return user

  def get_code_from_url_param(self):
    """Get the code query parameter from the current request."""
    parsed = urlparse.urlparse(self.path)
    code = urlparse.parse_qs(parsed.query)['code'][0]
    print 'Code from URL: %s' % code
    return code

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
