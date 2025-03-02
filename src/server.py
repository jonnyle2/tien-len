import operator
from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterable

from tabulate import tabulate
from twisted.internet import reactor
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
        elif self.state is PlayerState.READY:
            self.handle_READY(line)
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
        try:
            self.table.join(self)
        except RuntimeError as e:
            self.sendLine(str(e).encode())
            self.transport.loseConnection()
            return
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
            self.sendLine('You are now ready. Waiting on others to be ready and host to start.'.encode())
        else:
            self.sendLine('Type "ready" to get ready. The host will start when everyone is ready.'.encode())

    def handle_READY(self, line):
        msg = line.lower()
        if msg in ['ur', 'unready']:
            self.state = PlayerState.LOBBY
            self.sendLine('You are now unready. Type "ready" to get ready.'.encode())
        else:
            self.sendLine('You are ready. Waiting on others to be ready and host to start.'.encode())

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
        self.state = TableState.STARTED
        self.game = Game(self.players)
        instant_winners = self.game.start()
        if instant_winners:
            messages = []
            first_place_names = []
            for winner in instant_winners:
                messages.append(f'{winner[0].player.name} got an instant win by {winner[1]}!')
                messages.append(f'Hand: {sorted(winner[0].hand)}')
                first_place_names.append(winner[0].player.name)
            messages.append(f'1st place: {", ".join(first_place_names)}')
            messages.append(f'4th place: {", ".join((seat.player.name for seat in self.seats if seat.player.name not in first_place_names))}')
            announce(self.players, messages)
            self.reset()

    def play(self, player, line):
        # propagate to game
        msg = self.game.play(player, line)
        if msg:
            announce(self.players, [msg])
            self.reset()

    def reset(self):
        for player in self.players:
            player.state = PlayerState.LOBBY
        self.state = TableState.LOBBY
        self.game = None

class Game:
    def __init__(self, players: Iterable[Player]):
        self.seats = [Seat(player, hand) for player, hand in zip(players, deal_deck())]
        # later initialized in start() if no instant winners
        self.winners = None
        self.total_players = None
        self.round = None

    def instant_win_phase(self):
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
        return instant_winners

    def start(self):
        instant_winners = self.instant_win_phase()
        if instant_winners:
            return instant_winners
        self.winners = []
        self.total_players = len(self.seats)
        first, min_card = min(((i, min(seat.hand)) for i, seat in enumerate(self.seats)), key=operator.itemgetter(1))
        ordered_seats = self.seats[first:] + self.seats[:first]
        self.round = Round(ordered_seats, self, min_card)

    def play(self, player, line):
        # propagate to round
        round_winner = self.round.play(player, line)
        if len(self.winners) >= self.total_players - 1:
            prefixes = ['1st place: ', '2nd place: ', '3rd place: ', '4th place: ']
            self.winners.append(next(seat for seat in self.seats if seat not in self.winners))
            msg = ', '.join(prefix + seat.player.name for prefix, seat in zip(prefixes, self.winners))
            return msg
        if round_winner:
            if len(round_winner.hand) == 0:
                # loop through seats that aren't done, starting with
                i = self.seats.index(round_winner)
                round_winner = next(seat for seat in self.seats[i+1:] + self.seats[:i] if len(seat.hand) != 0)
            # remove finished players before next round
            for seat in self.seats:
                if len(seat.hand) == 0:
                    self.seats.remove(seat)
            index = self.seats.index(round_winner)
            self.round = Round(self.seats[index:] + self.seats[:index], self)


class Round:
    def __init__(self, ordered_seats, game, min_card = None):
        self.game = game
        self.players = [seat.player for seat in ordered_seats]
        self.ordered_seats = deque()
        self.ordered_seats.extendleft(ordered_seats)
        self.ordered_seats[-1].player.state = PlayerState.GET_PLAY
        self.min_card = min_card
        if not self.min_card:
            self.ordered_seats[-1].player.sendLine('New round. Play any combination to start.'.encode())
            self.ordered_seats[-1].player.sendLine('Your hand:'.encode())
            hand_str = [f'{card.rank.label} {card.suit.label}' for card in sorted(self.ordered_seats[-1].hand)]
            self.ordered_seats[-1].player.sendLine(tabulate([hand_str, range(1, len(hand_str)+1)], tablefmt='rounded_grid').encode())
        else:
            self.ordered_seats[-1].player.sendLine('You are first to start the game!'.encode())
            self.ordered_seats[-1].player.sendLine(f'Play a combination with your lowest card: {self.min_card.rank.label} of {self.min_card.suit.name.lower()}.'.encode())
        for seat in list(self.ordered_seats)[:-1]:
            seat.player.sendLine(f'New round! Player {self.ordered_seats[-1].player.name} is going first.'.encode())
            seat.player.state = PlayerState.PLAYING
        self.winning_card = None
        self.winning_seat = None  # track for specific case

    def handle_next_player(self, seat):
        seat.player.state = PlayerState.GET_PLAY
        msgs = ['It is your turn!']
        msgs.append('Your hand:')
        hand_str = [f'{card.rank.label} {card.suit.label}' for card in sorted(seat.hand)]
        msgs.append(tabulate([hand_str, range(1, len(hand_str)+1)], tablefmt='rounded_grid'))
        for msg in msgs:
            seat.player.sendLine(msg.encode())

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
                if len(self.ordered_seats) == 1:
                    return self.handle_special_case()
                if len(self.ordered_seats) == 0:
                    return self.winning_seat
                self.handle_next_player(self.ordered_seats[-1])
            elif self.winning_card:
                player.sendLine('Please enter only numbers or "pass".'.encode())
            else:
                player.sendLine('Please enter only numbers.'.encode())
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
        self.winning_seat = self.ordered_seats[-1]
        self.winning_card = play
        self.ordered_seats[-1].player.state = PlayerState.PLAYING
        announce(self.players, [f'Player {player.name} played: {play}'])
        if len(self.ordered_seats[-1].hand) == 0:
            self.game.winners.append(self.ordered_seats.pop())
            announce(self.players, [f'Player {player.name} is finished!'])
        else:
            self.ordered_seats.rotate()
        if len(self.ordered_seats) <= 1:
            return self.handle_special_case()
        self.handle_next_player(self.ordered_seats[-1])

    def handle_special_case(self):
        # check special case
        if self.winning_seat != self.ordered_seats[0]:
            # round winner was done, check if next player can pickup
            self.handle_next_player(self.ordered_seats[-1])
        else:
            return self.winning_seat

if __name__ == '__main__':
    factory = PlayerFactory()
    reactor.listenTCP(8123, factory)
    reactor.run()
