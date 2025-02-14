from collections import Counter
from dataclasses import dataclass
from itertools import pairwise
from typing import Collection

from deck import Card, Rank, Suit

THREE_SPADES = Card(Rank.THREE, Suit.SPADES)

DRAGON_SEQUENCE = frozenset(list(Rank)[:-1])
def _has_dragon_sequence(hand: set[Card]) -> bool:
    return DRAGON_SEQUENCE <= set(card.rank for card in hand)

FOUR_TWOS = frozenset((Card(Rank.TWO, suit) for suit in Suit))
def _has_four_twos(hand: set[Card]) -> bool:
    return FOUR_TWOS <= hand

def _has_three_quads(hand_count: Counter[Rank]) -> bool:
    return len(hand_count) == 3

def _has_four_triples(hand_count: Counter[Rank]) -> bool:
    return len(hand_count) == 4

def _has_six_pairs(hand_count: Counter[Rank]) -> bool:
    doubles = 0
    for count in hand_count.values():
        doubles += count//2  # count pairs, a quad counts as two pairs
    return doubles == 6

def has_instant_win(hand: set[Card]) -> str | None:
    if _has_dragon_sequence(hand):
        return 'dragon sequence'
    if _has_four_twos(hand):
        return 'four twos'
    hand_count = Counter(card.rank for card in hand)
    if _has_three_quads(hand_count):
        return 'three quads'
    if _has_four_triples(hand_count):
        return 'four triples'
    if _has_six_pairs(hand_count):
        return 'six pairs'


class Single(Card):
    def __new__(cls, card: Card):
        return super().__new__(cls, card.rank, card.suit)


@dataclass(slots=True)
class Pair:
    card_1: Card
    card_2: Card

    def __post_init__(self):
        if self.card_1.rank != self.card_2.rank:
            raise ValueError(f'Pairs must be the same rank: {self.card_1.rank} does not match {self.card_2.rank}.')

    def __str__(self):
        return ' '.join(str(card) for card in sorted((self.card_1, self.card_2)))

    def __gt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(f'Cannot compare {type(other)} to {type(self)}.')
        return max(self.card_1, self.card_2) > max(other.card_1, other.card_2)

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(f'Cannot compare {type(other)} to {type(self)}.')
        return max(self.card_1, self.card_2) < max(other.card_1, other.card_2)


@dataclass(slots=True)
class Triple:
    card_1: Card
    card_2: Card
    card_3: Card

    def __post_init__(self):
        if self.card_1.rank != self.card_2.rank or self.card_2.rank != self.card_3.rank:
            raise ValueError(f'Triples must all be the same rank: {self.card_1.rank}, {self.card_2.rank}, {self.card_3.rank}.')

    def __str__(self):
        return ' '.join(str(card) for card in sorted((self.card_1, self.card_2, self.card_3)))

    def __gt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(f'Cannot compare {type(other)} to {type(self)}.')
        return self.card_1.rank > other.card_1.rank

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(f'Cannot compare {type(other)} to {type(self)}.')
        return self.card_1.rank < other.card_1.rank


@dataclass(slots=True)
class Quad:
    card_1: Card
    card_2: Card
    card_3: Card
    card_4: Card

    def __post_init__(self):
        if any(card.rank != self.card_1.rank for card in (self.card_2, self.card_3, self.card_4)):
            raise ValueError(f'Quads must all be the same rank: {self.card_1}, {self.card_2}, {self.card_3}, {self.card_4}.')

    def __str__(self):
        return ' '.join(str(card) for card in sorted((self.card_1, self.card_2, self.card_3, self.card_4)))

    def __gt__(self, other):
        if isinstance(other, Single) and other.rank is Rank.TWO:
            return True
        if isinstance(other, Pair) and other.card_1 is Rank.TWO:
            return True
        if not isinstance(other, type(self)):
            raise TypeError(f'Cannot compare {type(other)} to {type(self)}.')
        return self.card_1.rank > other.card_1.rank

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(f'Cannot compare {type(other)} to {type(self)}.')
        return self.card_1.rank < other.card_1.rank


@dataclass(slots=True)
class Straight:
    cards: Collection[Card]

    def __post_init__(self):
        if len(self.cards) < 3:
            raise ValueError('Straights must have at least 3 cards.')
        if any(card in FOUR_TWOS for card in self.cards):
            raise ValueError('Straights cannot contain ranks of 2.')
        sorted_cards = sorted(self.cards)
        running_rank = sorted_cards[0].rank.value + 1
        for card in sorted_cards[1:]:
            if running_rank != card.rank:
                raise ValueError(f'Straights must be sequential in rank. Current cards: {", ".join((str(card.rank) for card in sorted_cards))}')
            running_rank += 1

    def __str__(self):
        return ' '.join(str(card) for card in sorted(self.cards))

    def __gt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(f'Cannot compare {type(other)} to {type(self)}.')
        return max(self.cards) > max(other.cards)

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(f'Cannot compare {type(other)} to {type(self)}.')
        return max(self.cards) < max(other.cards)


@dataclass(slots=True)
class SequentialPairs:
    cards: Collection[Card]

    def __post_init__(self):
        if len(self.cards) < 6:
            raise ValueError('Sequential pairs must have at least 6 cards.')
        if len(self.cards) % 2 != 0:
            raise ValueError('Sequential pairs must have an even number of cards.')
        if any(card in FOUR_TWOS for card in self.cards):
            raise ValueError('Sequential pairs cannot contain ranks of 2.')
        sorted_cards = sorted(self.cards)
        if any(first.rank != second.rank for first, second in pairwise(sorted_cards)):
            raise ValueError(f'Sequential pairs must have pairs. Current cards: {", ".join((str(card.rank) for card in sorted_cards))}')
        running_rank = sorted_cards[0].rank.value + 1
        for card in sorted_cards[2::2]:
            if running_rank != card.rank:
                raise ValueError(f'Sequential pairs must be sequential in rank. Current cards: {", ".join((str(card.rank) for card in sorted_cards))}')
            running_rank += 1

    def __str__(self):
        return ' '.join(str(card) for card in sorted(self.cards))

    def __gt__(self, other):
        if isinstance(other, Single) and other.rank is Rank.TWO:
            return True
        if isinstance(other, Pair) and other.card_1 is Rank.TWO and len(self.cards) > 6:
            return True
        if isinstance(other, Triple) and other.card_1 is Rank.TWO and len(self.cards) > 8:
            return True
        if not isinstance(other, type(self)):
            raise TypeError(f'Cannot compare {type(other)} to {type(self)}.')
        return max(self.cards) > max(other.cards)

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(f'Cannot compare {type(other)} to {type(self)}.')
        return max(self.cards) < max(other.cards)


def get_combination(cards: Collection[Card]):
    if len(cards) == 1:
        return Single(*cards)
    if len(cards) == 2:
        return Pair(*cards)
    if len(cards) == 3:
        try:
            return Straight(cards)
        except ValueError:
            try:
                return Triple(*cards)
            except ValueError as e:
                raise ValueError('Cards are not a valid straight or triple combination.') from e
    if len(cards) == 4:
        try:
            return Straight(cards)
        except ValueError:
            try:
                return Quad(*cards)
            except ValueError as e:
                raise ValueError('Cards are not a valid straight or quad combination.') from e
    if len(cards) > 4:
        try:
            return Straight(cards)
        except ValueError:
            try:
                return SequentialPairs(cards)
            except ValueError as e:
                print(str(e))
                raise ValueError('Cards are not a valid straight or sequential pairs.') from e
    raise ValueError('Cards are not a valid combination.')
