import operator
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterable

from tabulate import tabulate
from twisted.internet import reactor, task
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver

import rule
from deck import Card, deal_deck
from rule import Pair, Quad, SequentialPairs, Single, Straight, Triple


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
        self.current_play = None
        self.seat_turn: Seat = None
        self.min_card = None  # for first round

    def join_queue(self, player: Player):
        if len(self.players) >= self.max_players:
            raise ValueError('Table is full.')
        if player not in self.players:
            self.players.append(player)
        if len(self.players) == self.max_players:
            for player in self.players:
                player.state = ProtocolState.START
            self.start_game()

    def message_all(self, messages: Iterable[str]):
        for player in self.players:
            for message in messages:
                player.sendLine(message)

    def play(self, choices):
        pass

    def message_and_get_play(self):
        self.seat_turn.player.state = ProtocolState.GET_PLAY
        sorted_hand = sorted(self.seat_turn.hand)
        hand_str = [f'{card.rank.label} {card.suit.label}' for card in sorted_hand]
        self.seat_turn.player.sendLine(tabulate([hand_str, range(1, len(hand_str)+1)], tablefmt='rounded_grid').encode())  # print hand and indexes)
        if self.current_play:
            self.seat_turn.player.sendLine(f'{type(self.current_play).__name__.capitalize()}s round.')
            self.seat_turn.player.sendLine(f'Current: {self.current_play}')
        elif not self.min_card:
            self.seat_turn.player.sendLine('New round. Play any combination to start.')
        else:
            self.seat_turn.player.sendLine(f'First play of game. Play a combination with your lowest card: {self.min_card.rank.label} of {self.min_card.suit.name.lower()}.')
        self.seat_turn.player.sendLine('Select cards separated by spaces or "pass": ')
        while self.seat_turn.player.state is not ProtocolState.START:
            task.deferLater(reactor, 3, lambda: None)

    def start_game(self):
        seats = [Seat(player, hand) for player, hand in zip(self.players, deal_deck())]

        instant_winners = []  # track instant winners
        for seat in seats:
            # print game start and initial hand
            seat.player.sendLine('Game is starting!'.encode())
            seat.player.sendLine('Your hand:'.encode())
            sorted_hand = sorted(seat.hand)
            hand_str = [f'{card.rank.label} {card.suit.label}' for card in sorted_hand]
            seat.player.sendLine(tabulate([hand_str, range(1, len(hand_str)+1)], tablefmt='rounded_grid').encode())
            # check if instant win hand
            instant_win = rule.has_instant_win(seat.hand)
            if instant_win:
                instant_winners.append((seat, instant_win))

        # handle instant win scenario
        if instant_winners:
            messages = []
            first_place_names = []
            for winner in instant_winners:
                messages.append(f'{winner[0].player.name} got an instant win by {winner[1]}!')
                messages.append(f'Hand: {sorted(winner[0].hand)}')
                first_place_names.append(winner[0].player.name)
            messages.append(f'1st place: {", ".join(first_place_names)}')
            messages.append(f'4th place: {", ".join((seat.player.name for seat in seats if seat.player.name not in first_place_names))}')
            self.message_all(messages)
            for player in self.players:
                player.state = ProtocolState.QUEUE
            return

        # track winners and total player for game ends conditon
        winners = []
        total_players = len(seats)

        # first player is the player w/ the lowest card
        first, min_card = min(((i, min(seat.hand)) for i, seat in enumerate(seats)), key=operator.itemgetter(1))
        round_order = deque()
        round_order.extendleft(seats[first:] + seats[:first])  # append in reverse order so pop() works properly
        while len(winners) < total_players - 1:
            # Start round
            self.message_all([f'{self.seat_turn.player.name}\'s turn...'])
            self.seat_turn = round_order[-1]
            if not min_card:
                play = self.message_and_get_play()


if __name__ == '__main__':
    reactor.listenTCP(8123, PlayerFactory())
    reactor.run()
