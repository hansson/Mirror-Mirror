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

  def do_GET(self):
    """Handler for GET request."""
    print '\nNEW REQUEST, Path: %s' % (self.path)
    print 'Headers: %s' % self.headers

    # To use this server, you first visit
    # http://localhost:8080/?user=<some_user_name>. You can use any name you
    # like for the user. It's only used as a key to store credentials,
    # and has no relationship with real user names. In a real system, you would
    # only use logged-in users for your system.
    if self.path.startswith('/?user='):
      # Initial page entered by user
      self.handle_initial_url()

    # When you redirect to the authorization server below, it redirects back
    # to to http://localhost:8080/?code=<some_code> after the user grants access
    # permission for your application.
    elif self.path.startswith('/?code='):
      # Page redirected back from auth server
      self.handle_redirected_url()
    # Only the two URL patterns above are accepted by this server.
    else:
      # Either an error from auth server or bad user entered URL.
      self.respond_ignore()

  def handle_initial_url(self):
    """Handles the initial path."""
    # The fake user name should be in the URL query parameters.
    user = self.get_user_from_url_param()

    # Call a helper function defined below to get the credentials for this user.
    credentials = self.get_credentials(user)

    # If there are no credentials for this fake user or they are invalid,
    # we need to get new credentials.
    if credentials is None or credentials.invalid:
      # Call a helper function defined below to respond to this GET request
      # with a response that redirects the browser to the authorization server.
      self.respond_redirect_to_auth_server(user)
    else:
      try:
        # Call a helper function defined below to get calendar data for this
        # user.
        calendar_output = self.get_calendar_data(credentials)

        # Call a helper function defined below which responds to this
        # GET request with data from the calendar.
        self.respond_calendar_data(calendar_output)
      except AccessTokenRefreshError:
        # This may happen when access tokens expire. Redirect the browser to
        # the authorization server
        self.respond_redirect_to_auth_server(user)

  def handle_redirected_url(self):
    """Handles the redirection back from the authorization server."""
    # The server should have responded with a "code" URL query parameter. This
    # is needed to acquire credentials.
    code = self.get_code_from_url_param()

    # Before we redirected to the authorization server, we set a cookie to save
    # the fake user for retrieval when handling the redirection back to this
    # server. This is only needed because we are using this fake user
    # name as a key to access credentials.
    user = self.get_user_from_cookie()

    #
    # This is an important step.
    #
    # We take the code provided by the authorization server and pass it to the
    # flow.step2_exchange() function. This function contacts the authorization
    # server and exchanges the "code" for credentials.
    credentials = RequestHandler.flow.step2_exchange(code)

    # Call a helper function defined below to save these credentials.
    self.save_credentials(user, credentials)

    # Call a helper function defined below to get calendar data for this user.
    calendar_output = self.get_calendar_data(credentials)

    # Call a helper function defined below which responds to this GET request
    # with data from the calendar.
    self.respond_calendar_data(calendar_output)

  def respond_redirect_to_auth_server(self, user):
    """Respond to the current request by redirecting to the auth server."""
    #
    # This is an important step.
    #
    # We use the flow object to get an authorization server URL that we should
    # redirect the browser to. We also supply the function with a redirect_uri.
    # When the auth server has finished requesting access, it redirects
    # back to this address. Here is pseudocode describing what the auth server
    # does:
    #   if (user has already granted access):
    #     Do not ask the user again.
    #     Redirect back to redirect_uri with an authorization code.
    #   else:
    #     Ask the user to grant your app access to the scope and service.
    #     if (the user accepts):
    #       Redirect back to redirect_uri with an authorization code.
    #     else:
    #       Redirect back to redirect_uri with an error code.
    uri = RequestHandler.flow.step1_get_authorize_url()

    # Set the necessary headers to respond with the redirect. Also set a cookie
    # to store our user name. We will need this when the auth server
    # redirects back to this server.
    print 'Redirecting %s to %s' % (user, uri)
    self.send_response(301)
    self.send_header('Cache-Control', 'no-cache')
    self.send_header('Location', uri)
    self.send_header('Set-Cookie', 'user=%s' % user)
    self.end_headers()

  def respond_ignore(self):
    """Responds to the current request that has an unknown path."""
    self.send_response(200)
    self.send_header('Content-type', 'text/plain')
    self.send_header('Cache-Control', 'no-cache')
    self.end_headers()
    self.wfile.write(
      'This path is invalid or user denied access:\n%s\n\n' % self.path)
    self.wfile.write(
      'User entered URL should look like: http://mirroronthewall.se:8080/?user=johndoe')

  def respond_calendar_data(self, calendar_output):
    """Responds to the current request by writing calendar data to stream."""
    self.send_response(200)
    self.send_header('Content-type', 'text/plain; charset=utf-8')
    self.send_header('Cache-Control', 'no-cache')
    self.end_headers()
    self.wfile.write(calendar_output)

  def get_calendar_data(self, credentials):
    """Given the credentials, returns calendar data."""
    output = StringIO.StringIO()

    http = httplib2.Http()
    http = credentials.authorize(http)

    service = build('calendar', 'v3', http=http)

    calendars = get_calendars(service)

    request = service.calendarList().list()
    while request != None:
      response = request.execute()
      for calendar in response.get('items',[]):
        currentCalendar = calendar.get('id','') + '\n'
        output.write(currentCalendar.encode('utf-8'))
      request = service.calendarList().list_next(request,response)
   
    request = service.events().list(calendarId='primary')
    
    while request != None:
      response = request.execute()
      for event in response.get('items', []):
        currentEvent = event.get('summary') + '  - ' + event.get('start').get('dateTime',event.get('start').get('date')) + '\n'
        output.write(currentEvent.encode('utf-8'))
      
      request = service.events().list_next(request, response)

    return output.getvalue()

  def get_calendars(service):
    
  def get_credentials(self, user):
    """Using the fake user name as a key, retrieve the credentials."""
    storage = Storage('credentials-%s.dat' % (user))
    return storage.get()

  def save_credentials(self, user, credentials):
    """Using the fake user name as a key, save the credentials."""
    storage = Storage('credentials-%s.dat' % (user))
    storage.put(credentials)

  def get_user_from_url_param(self):
    """Get the user query parameter from the current request."""
    parsed = urlparse.urlparse(self.path)
    user = urlparse.parse_qs(parsed.query)['user'][0]
    print 'Fake user from URL: %s' % user
    return user

  def get_user_from_cookie(self):
    """Get the user from cookies."""
    cookies = Cookie.SimpleCookie()
    cookies.load(self.headers.get('Cookie'))
    user = cookies['fake_user'].value
    print 'Fake user from cookie: %s' % user
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
