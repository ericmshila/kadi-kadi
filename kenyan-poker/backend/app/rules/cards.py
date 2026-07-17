"""
Card models for Kenyan Poker / Kadi.

This module contains only card-related concepts:
- Suits
- Ranks
- Card model
- Deck creation
- Deck shuffling

No game rules should live here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import random


class Suit(str, Enum):
    SPADES = "spades"
    HEARTS = "hearts"
    DIAMONDS = "diamonds"
    CLUBS = "clubs"


class Rank(str, Enum):
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    TEN = "10"
    JACK = "J"
    QUEEN = "Q"
    KING = "K"
    ACE = "A"
    JOKER = "JOKER"


@dataclass(frozen=True)
class Card:
    """
    A playing card.

    Jokers do not have a suit.
    Normal cards always have a suit.
    """

    rank: Rank
    suit: Optional[Suit] = None

    @property
    def is_joker(self) -> bool:
        return self.rank == Rank.JOKER

    @property
    def is_number_card(self) -> bool:
        return self.rank in {
            Rank.TWO,
            Rank.THREE,
            Rank.FOUR,
            Rank.FIVE,
            Rank.SIX,
            Rank.SEVEN,
            Rank.EIGHT,
            Rank.NINE,
            Rank.TEN,
        }

    def label(self) -> str:
        if self.is_joker:
            return "JOKER"

        if self.suit is None:
            return self.rank.value

        return f"{self.rank.value}{self.suit.value[0].upper()}"

    def __str__(self) -> str:
        return self.label()


def build_deck(
    seed: Optional[int] = None,
    include_jokers: int = 2,
) -> list[Card]:
    """
    Build a standard 52-card deck plus optional jokers.

    Args:
        include_jokers:
            Number of jokers to include. Default is 2.

    Returns:
        A list of Card objects.
    """

    deck: list[Card] = []

    for suit in Suit:
        for rank in Rank:
            if rank == Rank.JOKER:
                continue

            deck.append(Card(rank=rank, suit=suit))

    for _ in range(include_jokers):
        deck.append(Card(rank=Rank.JOKER, suit=None))

    return deck


def shuffled_deck(
    seed: Optional[int] = None,
    include_jokers: int = 2) -> list:
    """
    Build and shuffle a deck.

    A seed can be supplied for deterministic tests.
    """

    deck = build_deck(include_jokers=include_jokers)
    rng = random.Random(seed)
    rng.shuffle(deck)
    return deck