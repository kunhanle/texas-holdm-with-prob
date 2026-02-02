"""
Card and Deck classes for Texas Hold'em
撲克牌與牌組類別
"""

from enum import Enum
from dataclasses import dataclass
from typing import List
import random


class Suit(Enum):
    """花色枚舉"""
    SPADES = ("♠", "黑桃")
    HEARTS = ("♥", "紅心")
    DIAMONDS = ("♦", "方塊")
    CLUBS = ("♣", "梅花")
    
    def __init__(self, symbol: str, chinese: str):
        self.symbol = symbol
        self.chinese = chinese
    
    def __str__(self) -> str:
        return self.symbol


class Rank(Enum):
    """點數枚舉"""
    TWO = (2, "2")
    THREE = (3, "3")
    FOUR = (4, "4")
    FIVE = (5, "5")
    SIX = (6, "6")
    SEVEN = (7, "7")
    EIGHT = (8, "8")
    NINE = (9, "9")
    TEN = (10, "10")
    JACK = (11, "J")
    QUEEN = (12, "Q")
    KING = (13, "K")
    ACE = (14, "A")
    
    def __init__(self, value: int, symbol: str):
        self._value = value
        self.symbol = symbol
    
    @property
    def value(self) -> int:
        return self._value
    
    def __str__(self) -> str:
        return self.symbol
    
    def __lt__(self, other: 'Rank') -> bool:
        return self._value < other._value
    
    def __le__(self, other: 'Rank') -> bool:
        return self._value <= other._value
    
    def __gt__(self, other: 'Rank') -> bool:
        return self._value > other._value
    
    def __ge__(self, other: 'Rank') -> bool:
        return self._value >= other._value


@dataclass
class Card:
    """
    撲克牌類別
    
    Attributes:
        suit: 花色
        rank: 點數
    """
    suit: Suit
    rank: Rank
    
    def __str__(self) -> str:
        return f"[{self.rank}{self.suit}]"
    
    def __repr__(self) -> str:
        return f"Card({self.suit.name}, {self.rank.name})"
    
    def __lt__(self, other: 'Card') -> bool:
        return self.rank < other.rank
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Card):
            return False
        return self.suit == other.suit and self.rank == other.rank
    
    def __hash__(self) -> int:
        return hash((self.suit, self.rank))
    
    @property
    def display(self) -> str:
        """美觀顯示格式"""
        return f"[{self.rank.symbol}{self.suit.symbol}]"
    
    @property
    def value(self) -> int:
        """取得牌的數值（用於比較）"""
        return self.rank.value


class Deck:
    """
    牌組類別 - 標準52張撲克牌
    
    Methods:
        shuffle: 洗牌
        deal: 發一張牌
        deal_multiple: 發多張牌
        reset: 重置牌組
    """
    
    def __init__(self):
        self.cards: List[Card] = []
        self.reset()
    
    def reset(self) -> None:
        """重置牌組為完整52張牌"""
        self.cards = [
            Card(suit, rank)
            for suit in Suit
            for rank in Rank
        ]
    
    def shuffle(self) -> None:
        """洗牌"""
        random.shuffle(self.cards)
    
    def deal(self) -> Card:
        """發一張牌"""
        if not self.cards:
            raise ValueError("牌組已空，無法發牌")
        return self.cards.pop()
    
    def deal_multiple(self, count: int) -> List[Card]:
        """發多張牌"""
        if len(self.cards) < count:
            raise ValueError(f"牌組剩餘 {len(self.cards)} 張，無法發 {count} 張")
        return [self.deal() for _ in range(count)]
    
    def __len__(self) -> int:
        return len(self.cards)
    
    def __str__(self) -> str:
        return f"Deck({len(self.cards)} cards remaining)"


# 便利函數
def card_from_string(card_str: str) -> Card:
    """
    從字串解析牌
    
    Examples:
        card_from_string("A♠") -> Card(SPADES, ACE)
        card_from_string("10♥") -> Card(HEARTS, TEN)
        card_from_string("Ks") -> Card(SPADES, KING)
    """
    card_str = card_str.strip().upper()
    
    # 解析花色
    suit_map = {
        '♠': Suit.SPADES, 'S': Suit.SPADES,
        '♥': Suit.HEARTS, 'H': Suit.HEARTS,
        '♦': Suit.DIAMONDS, 'D': Suit.DIAMONDS,
        '♣': Suit.CLUBS, 'C': Suit.CLUBS
    }
    
    # 解析點數
    rank_map = {
        '2': Rank.TWO, '3': Rank.THREE, '4': Rank.FOUR,
        '5': Rank.FIVE, '6': Rank.SIX, '7': Rank.SEVEN,
        '8': Rank.EIGHT, '9': Rank.NINE, '10': Rank.TEN,
        'T': Rank.TEN, 'J': Rank.JACK, 'Q': Rank.QUEEN,
        'K': Rank.KING, 'A': Rank.ACE
    }
    
    # 嘗試解析
    suit_char = card_str[-1]
    rank_str = card_str[:-1]
    
    if suit_char not in suit_map:
        raise ValueError(f"無法識別花色: {suit_char}")
    if rank_str not in rank_map:
        raise ValueError(f"無法識別點數: {rank_str}")
    
    return Card(suit_map[suit_char], rank_map[rank_str])


def cards_from_string(cards_str: str) -> List[Card]:
    """
    從字串解析多張牌（空格分隔）
    
    Example:
        cards_from_string("A♠ K♠ Q♠ J♠ 10♠")
    """
    return [card_from_string(s) for s in cards_str.split()]


if __name__ == "__main__":
    # 測試
    deck = Deck()
    print(f"新牌組: {deck}")
    
    deck.shuffle()
    print("已洗牌")
    
    cards = deck.deal_multiple(5)
    print(f"發5張牌: {' '.join(c.display for c in cards)}")
    print(f"剩餘: {deck}")
    
    # 測試字串解析
    test_cards = cards_from_string("As Kh Qd Jc 10s")
    print(f"解析測試: {' '.join(c.display for c in test_cards)}")
