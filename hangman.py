# [START imports]
import os
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb

# front end framework imports
import jinja2
import webapp2

# api imports
import endpoints
from protorpc import messages
from protorpc import message_types
from protorpc import remote

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)
# [END imports]

WEB_CLIENT_ID = '184527909534-l7tkareovn1t8v3v766933933hhausng.apps.googleusercontent.com'
API_EXPLORER_CLIENT_ID = endpoints.API_EXPLORER_CLIENT_ID

# [START api]

#CONF_GET_REQUEST = endpoints.ResourceContainer(
#    message_types.VoidMessage,
#    websafeConferenceKey=messages.StringField(1),
#)

#CONF_POST_REQUEST = endpoints.ResourceContainer(
#    ConferenceForm,
#    websafeConferenceKey=messages.StringField(1),
#)


# If the request contains path or querystring arguments,
# you cannot use a simple Message class.
# Instead, you must use a ResourceContainer class
REQUEST_CONTAINER = endpoints.ResourceContainer(
    message_types.VoidMessage,
    name=messages.StringField(1),
)

REQUEST_GREETING_CONTAINER = endpoints.ResourceContainer(
    period=messages.StringField(1),
    name=messages.StringField(2),
)

package = 'Hello'


class Hello(messages.Message):
    """String that stores a message."""
    greeting = messages.StringField(1)


@endpoints.api(name='helloworldendpoints', version='v1')
class HelloWorldApi(remote.Service):
    """Helloworld API v1."""

    @endpoints.method(message_types.VoidMessage, Hello,
      path = "sayHello", http_method='GET', name = "sayHello")
    def say_hello(self, request):
      return Hello(greeting="Hello World")

    @endpoints.method(REQUEST_CONTAINER, Hello,
      path = "sayHelloByName", http_method='GET', name = "sayHelloByName")
    def say_hello_by_name(self, request):
      greet = "Hello {}".format(request.name)
      return Hello(greeting=greet)

    @endpoints.method(REQUEST_GREETING_CONTAINER, Hello,
      path = "greetByPeriod", http_method='GET', name = "greetByPeriod")
    def greet_by_period(self, request):
      greet = "Good {} {}".format(request.period, request.name)
      return Hello(greeting=greet)


api = endpoints.api_server([HelloWorldApi])

# [END api]


# [START main_page]
class MainPage(webapp2.RequestHandler):

    def get(self):

        user = users.get_current_user()

        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
            player_name = self.request.get('player_name',
                                              user.nickname())
            guesses_query = Guesses.query(
                ancestor=hangman_key(player_name)).order(Guesses.date)
            guesses = guesses_query.fetch()

            letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K',
                       'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V',
                       'W', 'X', 'Y', 'Z']

            original_length = len(letters)

            for guess in guesses:
                if guess.content in letters:
                    letters.remove(guess.content)

            current_length = len(letters)

            hangman_progress = ''

            template_values = {
                'user': user,
                'guesses': guesses,
                'player_name': urllib.quote_plus(player_name),
                'letters': letters,
                'url': url,
                'url_linktext': url_linktext,
            }
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'

            template_values = {
                'user': user,
                'url': url,
                'url_linktext': url_linktext,
            }



        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))
# [END main_page]


# [START game_play]
class GamePlay(webapp2.RequestHandler):

    def post(self):
        # We set the same parent key on the 'GamePlay' to ensure each
        # GamePlay is in the same entity group. Queries across the
        # single entity group will be consistent. However, the write
        # rate to a single entity group should be limited to
        # ~1/second.

        if users.get_current_user():

            player_name = self.request.get('player_name',
                                              users.get_current_user().nickname())
            guesses = Guesses(parent=hangman_key(player_name))


            guesses.player = Player(
                    identity=users.get_current_user().user_id(),
                    email=users.get_current_user().email())
            guesses.content = self.request.get('content')
            
            guesses.put()

            query_params = {'player_name': player_name}

        self.redirect('/')


app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/sign', GamePlay),
], debug=True)
# [END game_play]


# [START models]
def hangman_key(player_name):
    """Constructs a Datastore key for a GamePlay entity.

    We use player_name as the key.
    """
    return ndb.Key('GamePlay', player_name)


class Player(ndb.Model):
    """Sub model for representing an player."""
    identity = ndb.StringProperty(indexed=False)
    email = ndb.StringProperty(indexed=False)


class Guesses(ndb.Model):
    """A main model for representing an individual Game entry."""
    player = ndb.StructuredProperty(Player)
    content = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)
# [END models]