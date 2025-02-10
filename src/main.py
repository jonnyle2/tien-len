from collections import deque
from dataclasses import dataclass
from typing import Iterable

import rule
from deck import Card, Rank, Suit, deal_deck


@dataclass(slots=True)
class Player:
    name: str
    balance: int


@dataclass(slots=True)
class Seat:
    player: Player
    hand: set[Card]


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
            print(f'Hand: {winner[0].hand}')
        first_place = [w[0].player for w in instant_winners]
        print(f'1st place: {", ".join(first_place)}')
        print(f'4th place: {", ".join((seat.player for seat in seats if seat.player not in first_place))}')
        return  # instant win, game ends

    winners = []
    first = next((i, seat) for i, seat in enumerate(seats) if Card(Rank.THREE, Suit.SPADES) in seat.hand)
    round_order = deque()
    round_order.extendleft(seats[first[0]:])
    round_order.extendleft(seats[:first[0]])
    while len(winners) < 3:
        while len(round_order > 1):
        


if __name__ == '__main__':
    print('Press "Crtl + C" to exit at any time.')
    p1 = input('Player 1: ')
    p2 = input('Player 2: ')
    p3 = input('Player 3: ')
    p4 = input('Player 4: ')
    while True:
        start_game((p1, p2, p3, p4))
        ans = input('Play again (y/n)? ')
        if ans.lower() == 'n':
            break
