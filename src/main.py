import os
from collections import deque
from dataclasses import dataclass
from typing import Iterable

from tabulate import tabulate

import rule
from deck import Card, deal_deck
from rule import Pair, Quad, SequentialPairs, Single, Straight, Triple


@dataclass(slots=True)
class Seat:
    player: str
    hand: set[Card]


def print_and_get_card_selection(seat: Seat,
                                 to_beat: Single | Pair | Straight | Triple | Quad | SequentialPairs | None = None,
                                 min_card: Card | None = None) -> Single | Pair | Straight | Triple | Quad | SequentialPairs | None:
    os.system('cls||clear')
    print(f'Pass the keyboard to {seat.player}.')
    input("Press Enter to continue...")
    sorted_hand = sorted(seat.hand)
    hand_str = [f'{card.rank.label} {card.suit.label}' for card in sorted_hand]
    print(tabulate([hand_str, range(1, len(hand_str)+1)], tablefmt='rounded_grid'))  # print hand and indexes
    while True:
        if to_beat:
            print(f'{type(to_beat).__name__.capitalize()}s round.')
            print(f'Current: {to_beat}')
        elif not min_card:
            print('New round. Play any combination to start.')
        else:
            print(f'First play of game. Play a combination with your lowest card: {min_card.rank.label} of {min_card.suit.name.lower()}.')
        play_input = input(f'{seat.player} - select cards separated by spaces or "pass": ').split()
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
        if min_card is not None:
            if min_card not in cards:
                print(f'First play of game requires your lowest card: {min_card.rank.label} of {min_card.suit.name.lower()}.')
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


def start_game(players: Iterable[str]):
    seats = [Seat(player, hand) for player, hand in zip(players, deal_deck())]

    # check for instant wins
    instant_winners = []
    for seat in seats:
        instant_win = rule.has_instant_win(seat.hand)
        if instant_win:
            instant_winners.append((seat, instant_win))
    if instant_winners:
        for winner in instant_winners:
            print(f'{winner[0].player} got an instant win by {winner[1]}!')
            print(f'Hand: {sorted(winner[0].hand)}')
        first_place = [w[0].player for w in instant_winners]
        print(f'1st place: {", ".join(first_place)}')
        print(f'4th place: {", ".join((seat.player for seat in seats if seat.player not in first_place))}')
        return  # instant win, game ends

    winners = []
    # find player with lowest card
    first = 0
    min_card = min(seats[first].hand)
    for i in range(1, len(seats)):
        curr_min = min(seats[i].hand)
        if curr_min < min_card:
            min_card = curr_min
            first = i
    first_round = True
    round_order = deque()
    round_order.extendleft(seats[first:] + seats[:first])  # append in reverse order so pop() works properly
    while len(winners) < len(seats) - 1:
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
            # first round requires lowest card
            play = print_and_get_card_selection(seat_turn, min_card=min_card)
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
            if len(winners) == len(seats) - 1:
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

    # print placements
    prefixes = ['1st place: ', '2nd place: ', '3rd place: ', '4th place: ']
    winners.append(seats[0])
    for prefix, seat in zip(prefixes, winners):
        print(prefix + seat.player)


if __name__ == '__main__':
    print('Press "Crtl + C" to exit at any time.')
    while True:
        try:
            num_players = int(input('Enter number of players (2-4): '))
        except ValueError:
            print('Please enter only numbers 2-4.')
            continue
        if num_players not in (2, 3 ,4):
            print('Please enter only numbers 2-4.')
            continue
        break
    print('Enter player names.')
    players = [input(f'Player {i}: ') for i in range(1, num_players+1)]
    while True:
        start_game(players)
        ans = input('Play again (y/n)? ')
        if ans.lower() == 'n':
            break
