from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterable

from tabulate import tabulate
from twisted.internet import reactor
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver

from deck import Card, deal_deck


class ProtocolState(Enum):
    GETNAME = auto()
    QUEUE = auto()
    START = auto()


class Player(LineReceiver):
    def __init__(self, users, factory):
        self.users = users
        self.name = None
        self.state = ProtocolState.GETNAME
        self.factory = factory

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
        if self.state is ProtocolState.GETNAME:
            self.handle_GETNAME(line)
        elif self.state is ProtocolState.QUEUE:
            self.handle_QUEUE()

    def handle_GETNAME(self, name):
        if name in self.users:
            self.sendLine(b"Name taken, please choose another.")
            return
        self.sendLine(f"Welcome, {name}!".encode())
        self.name = name
        self.users[name.lower()] = self
        self.state = ProtocolState.QUEUE
        self.factory.table.join_queue(self)

    def handle_QUEUE(self):
        self.sendLine('Waiting on players...'.encode())


class PlayerFactory(Factory):
    def __init__(self):
        self.users = {}  # maps user names to Chat instances
        self.table = Table()

    def buildProtocol(self, addr):
        return Player(self.users, self)


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

    def join_queue(self, player: Player):
        if len(self.players) >= self.max_players:
            raise ValueError('Table is full.')
        if player not in self.players:
            self.players.append(player)
        if len(self.players) == self.max_players:
            for player in self.players:
                player.state = ProtocolState.START
            self.start_game()

    def start_game(self):
        seats = [Seat(player, hand) for player, hand in zip(self.players, deal_deck())]

        for seat in seats:
            seat.player.sendLine('Game is starting!'.encode())
            seat.player.sendLine('Your hand:'.encode())
            sorted_hand = sorted(seat.hand)
            hand_str = [f'{card.rank.label} {card.suit.label}' for card in sorted_hand]
            seat.player.sendLine(tabulate([hand_str, range(1, len(hand_str)+1)], tablefmt='rounded_grid').encode())


if __name__ == '__main__':
    reactor.listenTCP(8123, PlayerFactory())
    reactor.run()
