import operator
from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterable

from tabulate import tabulate
from twisted.internet.protocol import Factory, connectionDone
from twisted.protocols.basic import LineReceiver

import rule
from deck import Card, deal_deck


class PlayerState(Enum):
    GET_NAME = auto()
    LOBBY = auto()
    READY = auto()
    PLAYING = auto()
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

    def connectionLost(self, reason = connectionDone):
        self.table.leave(self)

    def lineReceived(self, line):
        line = line.decode()
        if line == 'exit':
            self.transport.loseConnection()
            return
        if self.state is PlayerState.GET_NAME:
            self.handle_GET_NAME(line)
        elif self.state is PlayerState.LOBBY:
            self.handle_LOBBY(line)
        elif self.state is PlayerState.PLAYING:
            self.sendLine('Not your turn yet. Waiting on other player...'.encode())
        elif self.state is PlayerState.GET_PLAY:
            self.table.play(self, line)

    def handle_GET_NAME(self, name):
        if any(name == player.name for player in self.table.players):
            self.sendLine(b"Name taken, please choose another.")
            return
        self.sendLine(f"Welcome, {name}!".encode())
        self.name = name
        self.state = PlayerState.LOBBY
        self.table.join(self)
        if self.table.host is self:
            self.sendLine('You are the lobby host. When everyone is ready, type "start" to start the game'.encode())
        else:
            self.sendLine('Type "ready" to get ready. The host will start when everyone is ready.'.encode())

    def handle_LOBBY(self, line):
        msg = line.lower()
        if self.table.host is self:
            if msg == 'start':
                unready = [player.name for player in self.table.players if player is not self and player.state is not PlayerState.READY]
                if not unready:
                    self.table.start()
                else:
                    self.sendLine(f'Cannot start game: {", ".join(unready)} are not ready.'.encode())
            else:
                self.sendLine('Type "start" when everyone is ready.'.encode())
        elif msg in ['r', 'rdy', 'ready']:
            self.state = PlayerState.READY
            self.sendLine('You are now ready. Waiting on others and host to start.')
        else:
            self.sendLine('Type "ready" to get ready. The host will start when everyone is ready.'.encode())


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


def announce(players, messages):
        for player in players:
            for message in messages:
                player.sendLine(message.encode())


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
            raise RuntimeError('Cannot start game: game has already started.')
        for player in self.players:
            player.state = PlayerState.PLAYING
        self.state = TableState.STARTED
        self.game = Game(self.players)

    def play(self, player, line):
        # propagate to game
        self.game.play(player, line)

class Game:
    def __init__(self, players: Iterable[Player]):
        self.seats = [Seat(player, hand) for player, hand in zip(players, deal_deck())]
        # check instant winners
        instant_winners = []
        for seat in self.seats:
            seat.player.sendLine('Game is starting!'.encode())
            seat.player.sendLine('Your hand:'.encode())
            hand_str = [f'{card.rank.label} {card.suit.label}' for card in sorted(seat.hand)]
            seat.player.sendLine(tabulate([hand_str, range(1, len(hand_str)+1)], tablefmt='rounded_grid').encode())
            instant_win = rule.has_instant_win(seat.hand)
            if instant_win:
                instant_winners.append((seat, instant_win))
        if instant_winners:
            messages = []
            first_place_names = []
            for winner in instant_winners:
                messages.append(f'{winner[0].player.name} got an instant win by {winner[1]}!')
                messages.append(f'Hand: {sorted(winner[0].hand)}')
                first_place_names.append(winner[0].player.name)
            messages.append(f'1st place: {", ".join(first_place_names)}')
            messages.append(f'4th place: {", ".join((seat.player.name for seat in self.seats if seat.player.name not in first_place_names))}')
            for seat in self.seats:
                for msg in messages:
                    seat.player.sendLine(msg.encode())
                seat.player.state = PlayerState.LOBBY
            return
        self.winners = []
        first, min_card = min(((i, min(seat.hand)) for i, seat in enumerate(self.seats)), key=operator.itemgetter(1))
        ordered_seats = self.seats[first:] + self.seats[:first]
        self.round = Round(ordered_seats, min_card)

    def play(self, player, line):
        # propagate to round
        self.round.play(player, line)

class Round:
    def __init__(self, ordered_seats, min_card = None):
        self.players = [seat.player for seat in ordered_seats]
        self.ordered_seats = deque()
        self.ordered_seats.extendleft(ordered_seats)
        self.min_card = min_card
        self.winning_card = None
        self.winner = None

    def play(self, player, line):
        line = line.lower().split()
        if player is not self.ordered_seats[-1].player:
            raise ValueError(f'It is not player {player.name}\'s turn to play.')
        sorted_hand = sorted(self.ordered_seats[-1].hand)
        try:
            cards = {sorted_hand[int(i)-1] for i in line}
        except ValueError:
            if self.winning_card and line[0] == 'pass':
                player.state = PlayerState.PLAYING
                announce(self.players, [f'Player {player.name} dropped out of the round.'])
                self.ordered_seats.pop()
                self.ordered_seats[-1].player.state = PlayerState.GET_PLAY
            else:
                player.sendLine('Please enter only numbers or "pass".'.encode())
            return
        except IndexError:
            player.sendLine(f'Please enter only numbers from 1-{len(sorted_hand)}.'.encode())
            return
        if self.min_card is not None:
            if self.min_card not in cards:
                player.sendLine(f'First play of game requires your lowest card: {self.min_card.rank.label} of {self.min_card.suit.name.lower()}.'.encode())
                return
        try:
            play = rule.get_combination(cards)
        except ValueError as e:
            player.sendLine(str(e).encode)
            return
        if self.min_card:
            self.min_card = None
        if self.winning_card:
            try:
                if not play > self.winning_card:  # not > (instead of <) to avoid implementing __lt__ in singles, pairs, and triples
                    player.sendLine(f'Combination must be higher than {self.winning_card}.'.encode())
                    return
            except TypeError:
                player.sendLine(f'Round is {type(self.winning_card).__name__.lower()}s. Play only this combination of cards.'.encode())
                return
            except ValueError as e:
                player.sendLine(str(e).encode)
                return
        self.ordered_seats[-1].hand.difference_update(cards)
        self.ordered_seats[-1].player.state = PlayerState.PLAYING
        announce(self.players, [f'Player {player.name} played: {play}'])
        self.winning_card = play
        self.ordered_seats.rotate()
