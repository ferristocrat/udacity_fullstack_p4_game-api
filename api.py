# -*- coding: utf-8 -*-`
"""api.py - Create and configure the Game API exposing the resources.
This can also contain game logic. For more complex games it would be wise to
move game logic to another file. Ideally the API will be simple, concerned
primarily with communication to/from the API's users."""

import operator
import re
import logging
import endpoints
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue

from models import User, Game, Score
from models import StringMessage, NewGameForm, GameForm, GameForms, \
    MakeMoveForm, ScoreForm, ScoreForms, UserForm, UserForms
from utils import get_by_urlsafe

NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
        urlsafe_game_key=messages.StringField(1),)
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key=messages.StringField(1),)
USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1),
                                           email=messages.StringField(2))

MEMCACHE_GAMES_ACTIVE = 'GAMES_ACTIVE'

alphabet = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
            'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']


@endpoints.api(name='hangman_api', version='v1')
class HangmanApi(remote.Service):
    """Hangman API"""

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a User. Requires a unique username"""
        if User.query(User.name == request.user_name).get():
            raise endpoints.ConflictException(
                    'A User with that name already exists!')
        user = User(name=request.user_name, email=request.email)
        user.put()
        return StringMessage(message='User {} created!'.format(
                request.user_name))

    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Creates new game"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        try:
            game = Game.new_game(user.key, request.word_length)
        except ValueError:
            raise endpoints.BadRequestException('Word must be between '
                                                '10 and 20!')

        # Use a task queue to update the average attempts remaining.
        # This operation is not needed to complete the creation of a new game
        # so it is performed out of sequence.
        taskqueue.add(url='/tasks/cache_average_attempts')
        return game.to_form('Hangman game started!')

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game state."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            if game.game_over:
                return game.to_form('The game is already over!')
            elif game.cancelled:
                return game.to_form('This game was cancelled!')
            else:
                return game.to_form('Time to make a move!')
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='make_move',
                      http_method='PUT')
    def make_move(self, request):
        """Makes a move. Returns a game state with message"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        guess = (request.guess).upper()
        if game.game_over:
            return game.to_form('Game already over!')

        if game.cancelled:
            return game.to_form('This game was cancelled!')

        if len(guess) > 1:
            return game.to_form('Invalid guess! You can only guess \
                                one letter at a time!')

        if guess not in alphabet:
            return game.to_form('You need to enter a letter (A-Z)!')

        letter_list = []
        for m in re.finditer(guess, game.word):
            letter_list.append(m.start())
        number_matched = len(letter_list)

        if guess in game.letters_guessed_correct:
            msg = "You've already guessed " + guess + \
                ", which is a correct letter."

        elif guess in game.letters_guessed_wrong:
            msg = "You've already guessed " + guess + \
                ", which is an incorrect letter."

        elif number_matched > 0:
            game.add_correct_guess(guess)
            correct_letters = set(''.join(game.letters_guessed_correct))
            word_letters = set(game.word)
            if len(correct_letters) == len(word_letters):
                game.end_game(True)

                rankings = {}
                users = User.query().fetch()
                for user in users:
                    scores = Score.query(Score.user == user.key)
                    number_of_games = scores.count()
                    total_guesses = 0
                    for score in scores:
                        total_guesses += score.guesses
                    rankings[user.key] = (total_guesses/number_of_games)
                sorted_rankings = sorted(rankings.items(), key=operator.itemgetter(1))
                for index, item in enumerate(sorted_rankings):
                    rankings[sorted_rankings[index][0]] = index + 1
                for user in users:
                    for rank in rankings:
                        if user.key == rank:
                            user.ranking = rankings[rank]
                            user.put()

                return game.to_form('You win!')

            if number_matched > 1:
                msg = "You guessed correct. There are " + \
                    str(number_matched) + " " + guess + "'s"
            else:
                msg = "You guessed correct. There is " + \
                    str(number_matched) + " " + guess + "'s"
        else:
            game.attempts_remaining -= 1
            game.add_wrong_guess(guess)
            msg = "Wrong! There are no " + guess + "'s" + \
                " in this word."

        if game.attempts_remaining < 1:
            game.end_game(False)
            rankings = {}
            users = User.query().fetch()
            for user in users:
                scores = Score.query(Score.user == user.key)
                number_of_games = scores.count()
                total_guesses = 0
                for score in scores:
                    total_guesses += score.guesses
                rankings[user.key] = (total_guesses/number_of_games)
            sorted_rankings = sorted(rankings.items(), key=operator.itemgetter(1))
            for index, item in enumerate(sorted_rankings):
                rankings[sorted_rankings[index][0]] = index + 1
            for user in users:
                for rank in rankings:
                    if user.key == rank:
                        user.ranking = rankings[rank]
                        user.put()

            return game.to_form(msg + ' Game over!')
        else:
            game.put()
            return game.to_form(msg)

    @endpoints.method(response_message=ScoreForms,
                      path='scores',
                      name='get_scores',
                      http_method='GET')
    def get_scores(self, request):
        """Return all scores"""
        return ScoreForms(items=[score.to_form() for score in Score.query()])

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=ScoreForms,
                      path='scores/user/{user_name}',
                      name='get_user_scores',
                      http_method='GET')
    def get_user_scores(self, request):
        """Returns all of an individual User's scores"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A User with that name does not exist!')
        scores = Score.query(Score.user == user.key)
        return ScoreForms(items=[score.to_form() for score in scores])


    @endpoints.method(request_message=USER_REQUEST,
                      response_message=GameForms,
                      path='games/user/{user_name}',
                      name='get_user_games',
                      http_method='GET')
    def get_user_games(self, request):
        """Returns all of a User's games (both active and inactive)"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                'A User with that name does not exist!')
        games = Game.query(Game.user == user.key)
        null_message = None
        return GameForms(games=[game.to_form(null_message) for game in games])

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}/cancel',
                      name='cancel_game',
                      http_method='PUT')
    def cancel_game(self, request):
        """Cancel's the game"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            if game.game_over:
                return game.to_form('The game is already over, and cannot be deleted')
            else:
                game.cancel_game()
                game.put()
                return game.to_form("Game has been cancelled!")
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=endpoints.ResourceContainer(number_of_records=messages.IntegerField(1, default=3)),
                      response_message=ScoreForms,
                      path='highscores',
                      name='get_high_scores',
                      http_method='GET')
    def get_high_scores(self, request):
        """Return high scores"""
        scores = Score.query(Score.won == True).order(Score.guesses).fetch(request.number_of_records)
        return ScoreForms(items=[score.to_form() for score in scores])

    @endpoints.method(response_message=UserForms,
                      path='rankings',
                      name='get_user_rankings',
                      http_method='GET')
    def get_user_rankings(self, request):
        """Return a list of ranked players scores"""
        users = User.query().order(User.ranking).fetch()
        return UserForms(rankings=[user.to_form() for user in users])


    @staticmethod
    def cache_active_games():
        """Populates memcache with the average moves remaining of Games"""
        games = Game.query().fetch()
        if games:
            count_games = games.count()
            memcache.set(MEMCACHE_GAMES_ACTIVE,
                         'The number of active games is {:.2f}'
                         .format(count_games))


    @endpoints.method(response_message=StringMessage,
                      path='games/average_attempts',
                      name='get_active_game_count',
                      http_method='GET')
    def get_active_game_count(self, request):
        """Get the cached number of active games"""
        return StringMessage(message=memcache.get(MEMCACHE_GAMES_ACTIVE) or
                             'There are no active games at the moment')


api = endpoints.api_server([HangmanApi])
