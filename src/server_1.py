import operator
from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterable

from twisted.internet.error import ConnectionDone
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver

from deck import Card, deal_deck


class PlayerState(Enum):
    GET_NAME = auto()
    QUEUE = auto()
    START = auto()
    GET_PLAY = auto()

class Player(LineReceiver):
    def __init__(self, table: 'Table'):
        self.name = None
        self.state = PlayerState.GET_NAME
        self.table = table

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return (self.name, self.state) == (other.name, other.state)

    def connectionMade(self):
        self.sendLine(b"What's your name?")

    def connectionLost(self, reason = ConnectionDone):
        if self.name in self.users:
            del self.users[self.name]
        

    def lineReceived(self, line):
        line = line.decode()
        if line == 'exit':
            self.transport.loseConnection()
            return
        if self.state is PlayerState.GET_NAME:
            self.handle_GET_NAME(line)
        elif self.state is PlayerState.QUEUE:
            self.sendLine('Waiting on players...'.encode())
        elif self.state is PlayerState.START:
            self.sendLine('Not your turn yet. Waiting on other player...'.encode())
        elif self.state is PlayerState.GET_PLAY:
            self.table.

    def handle_GET_NAME(self, name):
        if any(name == player.name for player in self.table.players):
            self.sendLine(b"Name taken, please choose another.")
            return
        self.sendLine(f"Welcome, {name}!".encode())
        self.name = name
        self.users[name.lower()] = self
        self.state = PlayerState.QUEUE
        self.table.join_queue(self)

class PlayerFactory(Factory):
    def __init__(self):
        self.table = Table()

    def buildProtocol(self, addr):
        return Player(self.table)


@dataclass(slots=True)
class Seat:
    player: Player
    hand: set[Card]


class TableState(Enum):
    LOBBY = auto()
    STARTED = auto()


class Table:
    max_players = 4

    def __init__(self):
        self.players = []
        self.state = TableState.LOBBY
        self.host = None
        self.game = None

    def join(self, player):
        if self.state is not TableState.LOBBY:
            raise RuntimeError('Cannot join table: table is in game.')
        if len(self.players) == self.max_players:
            raise RuntimeError('Cannot join table: table is full.')
        if self.host is None:
            self.host = player
        self.players.append(player)

    def leave(self, player):
        try:
            self.players.remove(player)
        except ValueError:
            return  # player is not in table
        # appoint new host if same player
        if player is self.host:
            if self.players:
                self.host = self.players[0]
            else:
                self.host = None

    def start(self):
        if self.state is TableState.STARTED:
            raise RuntimeError('Cannot start game: game is already started.')
        self.state = TableState.STARTED
        self.game = Game(self.players)

class Game:
    def __init__(self, players: Iterable[Player]):
        self.seats = [Seat(player, hand) for player, hand in zip(players, deal_deck())]
        self.winners = []
        first, min_card = min(((i, min(seat.hand)) for i, seat in enumerate(self.seats)), key=operator.itemgetter(1))


class Round:
    def __init__(self, ordered_seats, min_card = None):
        self.ordered_seats = deque()
        self.ordered_seats.extendleft(ordered_seats)
        self.min_card = min_card
        self.winner = None
