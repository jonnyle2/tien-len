from collections import deque
from dataclasses import dataclass
from typing import Iterable

from tabulate import tabulate

import rule
from rule import Single, Pair, SequentialPairs, Straight, Triple, Quad, THREE_SPADES
from deck import Card, Rank, Suit, deal_deck


@dataclass(slots=True)
class Player:
    name: str
    balance: int


@dataclass(slots=True)
class Seat:
    player: Player
    hand: set[Card]


def print_and_get_card_selection(seat: Seat,
                                 to_beat: Single | Pair | Straight | Triple | Quad | SequentialPairs | None = None,
                                 first_round: bool = False) -> Single | Pair | Straight | Triple | Quad | SequentialPairs | None:
    sorted_hand = sorted(seat.hand)
    hand_str = [f'{card.rank.label} {card.suit.label}' for card in sorted_hand]
    print(tabulate([hand_str, range(1, len(hand_str)+1)], tablefmt='rounded_grid'))  # print hand and indexes
    while True:
        if to_beat:
            print(f'{type(to_beat).__name__.capitalize()}s round.')
            print(f'Current: {to_beat}')
        elif not first_round:
            print('New round. Play any combination to start.')
        else:
            print('First round. Play any combination with the 3 of spades.')
        play_input = input(f'{seat.player.name} - select cards separated by spaces: ').split()
        try:
            cards = {sorted_hand[int(i)-1] for i in play_input}
        except ValueError:
            if to_beat and play_input[0].lower() == 'pass':
                return None
            print('Please enter only numbers or "pass".')
            continue
        except IndexError:
            print(f'Please enter only numbers from 1-{len(seat.hand)}.')
            continue
        if first_round:
            if THREE_SPADES not in cards:
                print('First round, first play requires 3 of spades.')
                continue
        try:
            play = rule.get_combination(cards)
        except ValueError as e:
            print(str(e))
            continue
        if to_beat:
            try:
                if not play > to_beat:  # not > (instead of <) to avoid implementing __lt__ in singles, pairs, and triples
                    print(f'Combination must be higher than {to_beat}.')
                    continue
            except TypeError:
                print(f'Round is {type(to_beat).__name__.lower()}s. Play only this combination of cards.')
                continue
            except ValueError as e:
                print(str(e))
                continue
        seat.hand.difference_update(cards)
        return play


def start_game(player_names: Iterable[str]):
    players = (Player(player, 0) for player in player_names)
    seats = [Seat(player, hand) for player, hand in zip(players, deal_deck())]

    # check for instant wins
    instant_winners = []
    for seat in seats:
        instant_win = rule.has_instant_win(seat.hand)
        if instant_win:
            instant_winners.append((seat, instant_win))
    if instant_winners:
        for winner in instant_winners:
            print(f'{winner[0].player.name} got an instant win by {winner[1]}!')
            print(f'Hand: {sorted(winner[0].hand)}')
        first_place = [w[0].player.name for w in instant_winners]
        print(f'1st place: {", ".join(first_place)}')
        print(f'4th place: {", ".join((seat.player.name for seat in seats if seat.player not in first_place))}')
        return  # instant win, game ends

    winners = []
    first = next(i for i in range(len(seats)) if Card(Rank.THREE, Suit.SPADES) in seats[i].hand)
    first_round = True
    round_order = deque()
    round_order.extendleft(seats[first:] + seats[:first])  # append in reverse order so pop() works properly
    while len(winners) < 3:
        # Start round
        seat_turn = round_order[-1]
        if not first_round:
            play = print_and_get_card_selection(seat_turn)
            if len(seat_turn.hand) == 0:
                winners.append(seat_turn)
                round_order.pop()
            else:
                round_order.rotate()
        else:
            # first round requires 3 spades
            play = print_and_get_card_selection(seat_turn, first_round=True)
            first_round = False  # set off after first round
            round_order.rotate()
        current_lead = seat_turn  # specifically to catch if player wins round and is done, the player to the left goes next, not last to pass in round.
        while len(round_order) > 1:
            seat_turn = round_order[-1]
            last_play = play
            play = print_and_get_card_selection(seat_turn, last_play)
            if play is None:
                play = last_play
                round_order.pop()
                continue
            current_lead = seat_turn
            if len(seat_turn.hand) == 0:
                winners.append(seat_turn)
                round_order.pop()
                continue
            round_order.rotate()
        next_player = round_order[0]
        if current_lead != next_player:
            if len(winners) == 3:
                break  # avoid last move of last player
            # round winner was done, check if they can play and re-correct order
            play = print_and_get_card_selection(next_player, play)
            if play:
                index = seats.index(next_player)
            else:
                # loop through seats that aren't done, starting with
                i = seats.index(current_lead)
                next_player = next(seat for seat in seats[i+1:] + seats[:i] if len(seat.hand) != 0)
        round_order.pop()  # remove last person in round
        for seat in seats:
            if len(seat.hand) == 0:
                seats.remove(seat)
        index = seats.index(next_player)
        round_order.extendleft(seats[index:] + seats[:index])
    print(f'1st place: {winners[0].player.name}')
    print(f'2nd place: {winners[1].player.name}')
    print(f'3rd place: {winners[2].player.name}')
    print(f'4th place: {seats[0].player.name}')


if __name__ == '__main__':
    print('Press "Crtl + C" to exit at any time.')
    print('Enter player names.')
    p1 = input('Player 1: ')
    p2 = input('Player 2: ')
    p3 = input('Player 3: ')
    p4 = input('Player 4: ')
    while True:
        start_game((p1, p2, p3, p4))
        ans = input('Play again (y/n)? ')
        if ans.lower() == 'n':
            break
