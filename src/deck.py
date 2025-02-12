import random
from enum import IntEnum
from typing import NamedTuple


class Suit(IntEnum):
    SPADES = 1, '♠️'
    CLUBS = 2, '♣️'
    DIAMONDS = 3, '♦️'
    HEARTS = 4, '♥️'

    def __new__(cls, value, label):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.label = label  # assign new attribute label
        return obj

    @classmethod
    def _missing_(cls, value):
        # if we get here, simple value lookup has already failed
        for k, v in cls.__members__.items():
            if value in (k, v.label):
                return v


class Rank(IntEnum):
    THREE = 3, '3'
    FOUR = 4, '4'
    FIVE = 5, '5'
    SIX = 6, '6'
    SEVEN = 7, '7'
    EIGHT = 8, '8'
    NINE = 9, '9'
    TEN = 10, '10'
    JACK = 11, 'J'
    QUEEN = 12, 'Q'
    KING = 13, 'K'
    ACE = 14, 'A'
    TWO = 15, '2'

    def __new__(cls, value, label):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.label = label  # assign new attribute label
        return obj

    @classmethod
    def _missing_(cls, value):
        # if we get here, simple value lookup has already failed
        for k, v in cls.__members__.items():
            if value in (k, v.label):
                return v


class Card(NamedTuple):
    # order matters since it determines card values, e.g., 4 spades > 3 hearts
    rank: Rank
    suit: Suit

    def __str__(self):
        return f'[{self.rank.label} {self.suit.label}]'


DECK = frozenset(Card(rank=rank, suit=suit) for suit in Suit for rank in Rank)

def deal_deck(seed: int | float | str | bytes | bytearray | None = None) -> tuple[set[Card], set[Card], set[Card], set[Card]]:
    if seed is not None:
        random.seed(seed)
    deck_size = len(DECK)
    shuffled_deck = random.sample(sorted(DECK), k=deck_size)
    hand_size = deck_size//4
    return (set(shuffled_deck[:hand_size]),
            set(shuffled_deck[hand_size:hand_size*2]),
            set(shuffled_deck[hand_size*2:hand_size*3]),
            set(shuffled_deck[hand_size*3:]))
