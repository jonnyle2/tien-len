import operator
from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterable

from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver

from deck import Card, deal_deck


class ProtocolState(Enum):
    GET_NAME = auto()
    QUEUE = auto()
    START = auto()
    GET_PLAY = auto()

class Player(LineReceiver):
    def __init__(self, table: 'Table'):
        self.name = None
        self.state = ProtocolState.GET_NAME
        self.table = table

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return (self.name, self.state) == (other.name, other.state)

    def connectionMade(self):
        self.sendLine(b"What's your name?")

    def connectionLost(self, reason):
        if self.name in self.users:
            del self.users[self.name]

    def lineReceived(self, line):
        line = line.decode()
        if line == 'exit':
            self.transport.loseConnection()
            return
        if self.state is ProtocolState.GET_NAME:
            self.handle_GET_NAME(line)
        elif self.state is ProtocolState.QUEUE:
            self.sendLine('Waiting on players...'.encode())
        elif self.state is ProtocolState.START:
            self.sendLine('Not your turn yet. Waiting on other player...'.encode())
        elif self.state is ProtocolState.GET_PLAY:
            self.table.

    def handle_GET_NAME(self, name):
        if any(name == player.name for player in self.table.players):
            self.sendLine(b"Name taken, please choose another.")
            return
        self.sendLine(f"Welcome, {name}!".encode())
        self.name = name
        self.users[name.lower()] = self
        self.state = ProtocolState.QUEUE
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

class Table:
    max_players = 4

    def __init__(self, players: Iterable[Player] | None = None):
        if players is None:
            self.players = []
        else:
            if len(players) > self.max_players:
                raise ValueError(f'Too many players: max number of players is {self.max_players}.')
            self.players = [player for player in players]


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
