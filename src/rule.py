from collections import Counter
from typing import Iterable

from deck import Card, Rank, Suit

DRAGON_SEQUENCE = frozenset((Rank(i) for i in range(3, 15)))
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


class Pair(Card):
    def __new__(cls, card_1: Card, card_2: Card):
        if card_1.rank != card_2.rank:
            raise ValueError(f'Pairs must be the same rank: {card_1.rank} does not match {card_2.rank}.')
        return super().__new__(cls, card_1.rank, max(card_1.suit, card_2.suit))


class Triple(Card):
    def __new__(cls, card_1: Card, card_2: Card, card_3: Card):
        if card_1.rank != card_2.rank or card_2.rank != card_3.rank:
            raise ValueError(f'Triples must all be the same rank: {card_1.rank}, {card_2.rank}, {card_3.rank}.')
        return super().__new__(cls, card_1.rank, Suit.HEARTS)


class Quad(Card):
    def __new__(cls, card_1: Card, card_2: Card, card_3: Card, card_4: Card):
        if any(card != card_1 for card in (card_2, card_3, card_4)):
            raise ValueError(f'Quads must all be the same rank: {card_1}, {card_2}, {card_3}, {card_4}.')
        return super().__new__(cls, card_1.rank, Suit.HEARTS)


class Straight(Card):
    def __new__(cls, cards: Iterable[Card]):
        if len(cards) < 3:
            raise ValueError('Straights must have at least 3 cards.')
        sorted_cards = sorted(cards)
        next_card = sorted_cards[0].rank + 1
        for i in range(1, len(sorted_cards)):
            if next_card != sorted_cards[i]:
                ranks = (card.rank for card in sorted_cards)
                raise ValueError(f'Straights must be sequential in rank. Current cards: {", ".join(ranks)}')
            next_card += 1
        return super().__new__(cls, sorted_cards[-1].rank, sorted_cards[-1].suit)


def get_combination(cards: Iterable[Card]):
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
            except ValueError:
                raise ValueError('Cards are not a valid straight or triple combination.')
    if len(cards) == 4:
        try:
            return Straight(cards)
        except ValueError:
            try:
                return Quad(*cards)
            except ValueError:
                raise ValueError('Cards are not a valid straight or quad combination.')
    if len(cards) > 4:
        return Straight(cards)
    raise ValueError('Cards are not a valid combination.')
