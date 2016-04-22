# [START imports]
import os
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb

import jinja2
import webapp2

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)
# [END imports]


# We set a parent key on the 'Guesses' to ensure that they are all
# in the same entity group. Queries across the single entity group
# will be consistent. However, the write rate should be limited to
# ~1/second.

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

            for guess in guesses:
                if guess.content in letters:
                    letters.remove(guess.content)

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
            self.redirect('/?' + urllib.urlencode(query_params))
        else:
            self.redirect('/')


app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/sign', GamePlay),
], debug=True)