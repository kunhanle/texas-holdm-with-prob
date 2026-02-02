"""
Hand Evaluator for Texas Hold'em
手牌評估器 - 判斷牌型與比較大小
"""

from enum import IntEnum
from typing import List, Tuple, Optional
from collections import Counter
from .card import Card, Rank, Suit


class HandRank(IntEnum):
    """
    手牌等級枚舉（數值越大越強）
    """
    HIGH_CARD = 1       # 高牌
    ONE_PAIR = 2        # 一對
    TWO_PAIR = 3        # 兩對
    THREE_OF_A_KIND = 4 # 三條
    STRAIGHT = 5        # 順子
    FLUSH = 6           # 同花
    FULL_HOUSE = 7      # 葫蘆
    FOUR_OF_A_KIND = 8  # 四條
    STRAIGHT_FLUSH = 9  # 同花順
    ROYAL_FLUSH = 10    # 皇家同花順
    
    @property
    def chinese_name(self) -> str:
        names = {
            HandRank.HIGH_CARD: "高牌",
            HandRank.ONE_PAIR: "一對",
            HandRank.TWO_PAIR: "兩對",
            HandRank.THREE_OF_A_KIND: "三條",
            HandRank.STRAIGHT: "順子",
            HandRank.FLUSH: "同花",
            HandRank.FULL_HOUSE: "葫蘆",
            HandRank.FOUR_OF_A_KIND: "四條",
            HandRank.STRAIGHT_FLUSH: "同花順",
            HandRank.ROYAL_FLUSH: "皇家同花順"
        }
        return names[self]


class HandResult:
    """
    手牌評估結果
    
    Attributes:
        rank: 牌型等級
        best_five: 最佳5張牌
        kickers: 用於比較的踢腳牌值（降序排列）
        description: 牌型描述
    """
    
    def __init__(self, rank: HandRank, best_five: List[Card], kickers: List[int], description: str = ""):
        self.rank = rank
        self.best_five = best_five
        self.kickers = kickers
        self.description = description or rank.chinese_name
    
    def __str__(self) -> str:
        cards_str = ' '.join(c.display for c in self.best_five)
        return f"{self.description}: {cards_str}"
    
    def __repr__(self) -> str:
        return f"HandResult({self.rank.name}, kickers={self.kickers})"
    
    def compare_to(self, other: 'HandResult') -> int:
        """
        比較兩手牌
        Returns:
            1  if self > other
            -1 if self < other
            0  if equal
        """
        if self.rank != other.rank:
            return 1 if self.rank > other.rank else -1
        
        # 相同牌型，比較 kickers
        for k1, k2 in zip(self.kickers, other.kickers):
            if k1 != k2:
                return 1 if k1 > k2 else -1
        
        return 0  # 完全相同
    
    def __lt__(self, other: 'HandResult') -> bool:
        return self.compare_to(other) < 0
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HandResult):
            return False
        return self.compare_to(other) == 0
    
    def __gt__(self, other: 'HandResult') -> bool:
        return self.compare_to(other) > 0


class HandEvaluator:
    """
    手牌評估器
    
    提供靜態方法評估德州撲克手牌
    """
    
    @staticmethod
    def evaluate(cards: List[Card]) -> HandResult:
        """
        評估7張牌（2張手牌+5張公共牌）中的最佳5張牌組合
        
        Args:
            cards: 7張牌的列表
            
        Returns:
            HandResult 物件，包含牌型、最佳5張牌和比較資訊
        """
        if len(cards) < 5:
            raise ValueError("至少需要5張牌進行評估")
        
        # 嘗試所有5張牌組合，找出最佳
        from itertools import combinations
        
        best_result: Optional[HandResult] = None
        
        for five_cards in combinations(cards, 5):
            result = HandEvaluator._evaluate_five(list(five_cards))
            if best_result is None or result > best_result:
                best_result = result
        
        return best_result
    
    @staticmethod
    def _evaluate_five(cards: List[Card]) -> HandResult:
        """評估正好5張牌"""
        assert len(cards) == 5
        
        # 排序（降序）
        sorted_cards = sorted(cards, key=lambda c: c.rank.value, reverse=True)
        
        # 獲取基本資訊
        ranks = [c.rank for c in sorted_cards]
        suits = [c.suit for c in sorted_cards]
        rank_values = [c.rank.value for c in sorted_cards]
        
        is_flush = len(set(suits)) == 1
        is_straight, straight_high = HandEvaluator._check_straight(rank_values)
        
        rank_counts = Counter(ranks)
        count_values = sorted(rank_counts.values(), reverse=True)
        
        # 判斷牌型
        if is_straight and is_flush:
            if straight_high == 14:  # A-high straight flush
                return HandResult(HandRank.ROYAL_FLUSH, sorted_cards, [14], "皇家同花順")
            high_symbol = HandEvaluator._value_to_symbol(straight_high)
            return HandResult(HandRank.STRAIGHT_FLUSH, sorted_cards, [straight_high], 
                            f"同花順 (最高 {high_symbol})")
        
        if count_values == [4, 1]:  # 四條
            quad_rank = [r for r, c in rank_counts.items() if c == 4][0]
            kicker = [r for r, c in rank_counts.items() if c == 1][0]
            return HandResult(HandRank.FOUR_OF_A_KIND, sorted_cards, 
                            [quad_rank.value, kicker.value],
                            f"四條 {quad_rank.symbol}")
        
        if count_values == [3, 2]:  # 葫蘆
            trip_rank = [r for r, c in rank_counts.items() if c == 3][0]
            pair_rank = [r for r, c in rank_counts.items() if c == 2][0]
            return HandResult(HandRank.FULL_HOUSE, sorted_cards,
                            [trip_rank.value, pair_rank.value],
                            f"葫蘆 ({trip_rank.symbol} over {pair_rank.symbol})")
        
        if is_flush:
            return HandResult(HandRank.FLUSH, sorted_cards, rank_values,
                            f"同花 (最高 {ranks[0].symbol})")
        
        if is_straight:
            high_symbol = HandEvaluator._value_to_symbol(straight_high)
            return HandResult(HandRank.STRAIGHT, sorted_cards, [straight_high],
                            f"順子 (最高 {high_symbol})")
        
        if count_values == [3, 1, 1]:  # 三條
            trip_rank = [r for r, c in rank_counts.items() if c == 3][0]
            kickers = sorted([r.value for r, c in rank_counts.items() if c == 1], reverse=True)
            return HandResult(HandRank.THREE_OF_A_KIND, sorted_cards,
                            [trip_rank.value] + kickers,
                            f"三條 {trip_rank.symbol}")
        
        if count_values == [2, 2, 1]:  # 兩對
            pairs = sorted([r for r, c in rank_counts.items() if c == 2], 
                          key=lambda r: r.value, reverse=True)
            kicker = [r for r, c in rank_counts.items() if c == 1][0]
            return HandResult(HandRank.TWO_PAIR, sorted_cards,
                            [pairs[0].value, pairs[1].value, kicker.value],
                            f"兩對 ({pairs[0].symbol} 和 {pairs[1].symbol})")
        
        if count_values == [2, 1, 1, 1]:  # 一對
            pair_rank = [r for r, c in rank_counts.items() if c == 2][0]
            kickers = sorted([r.value for r, c in rank_counts.items() if c == 1], reverse=True)
            return HandResult(HandRank.ONE_PAIR, sorted_cards,
                            [pair_rank.value] + kickers,
                            f"一對 {pair_rank.symbol}")
        
        # 高牌
        return HandResult(HandRank.HIGH_CARD, sorted_cards, rank_values,
                        f"高牌 {ranks[0].symbol}")
    
    @staticmethod
    def _value_to_symbol(value: int) -> str:
        """Convert rank value to symbol"""
        symbols = {2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7',
                   8: '8', 9: '9', 10: '10', 11: 'J', 12: 'Q', 13: 'K', 14: 'A'}
        return symbols.get(value, str(value))
    
    @staticmethod
    def _check_straight(rank_values: List[int]) -> Tuple[bool, int]:
        """
        檢查是否為順子
        
        Returns:
            (is_straight, highest_card_value)
        """
        sorted_values = sorted(set(rank_values), reverse=True)
        
        if len(sorted_values) != 5:
            return False, 0
        
        # 一般順子檢查
        if sorted_values[0] - sorted_values[4] == 4:
            return True, sorted_values[0]
        
        # A-2-3-4-5 (wheel/bicycle) 特殊順子
        if sorted_values == [14, 5, 4, 3, 2]:
            return True, 5  # 5-high straight
        
        return False, 0
    
    @staticmethod
    def get_hand_strength(result: HandResult) -> float:
        """
        計算手牌強度（0-1範圍）
        用於AI決策和教學顯示
        """
        # 基礎分數（根據牌型）
        base_scores = {
            HandRank.HIGH_CARD: 0.0,
            HandRank.ONE_PAIR: 0.15,
            HandRank.TWO_PAIR: 0.30,
            HandRank.THREE_OF_A_KIND: 0.45,
            HandRank.STRAIGHT: 0.55,
            HandRank.FLUSH: 0.65,
            HandRank.FULL_HOUSE: 0.75,
            HandRank.FOUR_OF_A_KIND: 0.88,
            HandRank.STRAIGHT_FLUSH: 0.95,
            HandRank.ROYAL_FLUSH: 1.0
        }
        
        base = base_scores[result.rank]
        
        # 根據踢腳牌調整（每個等級內的微調）
        kicker_bonus = 0.0
        if result.kickers:
            # 將最高踢腳牌映射到 0-0.14 的額外分數
            kicker_bonus = (result.kickers[0] - 2) / 12 * 0.14
        
        # 確保在等級範圍內
        next_base = base_scores.get(HandRank(result.rank + 1), 1.0) if result.rank < HandRank.ROYAL_FLUSH else 1.0
        max_bonus = (next_base - base) * 0.99
        
        return min(base + min(kicker_bonus, max_bonus), 0.999)
    
    @staticmethod
    def compare_hands(hand1: List[Card], hand2: List[Card]) -> int:
        """
        比較兩手牌
        
        Returns:
            1 if hand1 wins
            -1 if hand2 wins
            0 if tie
        """
        result1 = HandEvaluator.evaluate(hand1)
        result2 = HandEvaluator.evaluate(hand2)
        return result1.compare_to(result2)


if __name__ == "__main__":
    from .card import cards_from_string
    
    # 測試各種牌型
    test_cases = [
        ("As Ks Qs Js 10s 2h 3d", "皇家同花順"),
        ("9s 8s 7s 6s 5s 2h 3d", "同花順"),
        ("As Ah Ad Ac Ks 2h 3d", "四條"),
        ("As Ah Ad Ks Kh 2h 3d", "葫蘆"),
        ("As 3s 5s 7s 9s 2h 3d", "同花"),
        ("As Kh Qd Js 10c 2h 3d", "順子"),
        ("As Ah Ad Ks Qh 2h 3d", "三條"),
        ("As Ah Ks Kh Qd 2h 3d", "兩對"),
        ("As Ah Ks Qh Jd 2h 3d", "一對"),
        ("As Kh Qd Js 9c 2h 3d", "高牌"),
    ]
    
    for cards_str, expected in test_cases:
        cards = cards_from_string(cards_str)
        result = HandEvaluator.evaluate(cards)
        print(f"{expected}: {result}")
        print(f"  強度: {HandEvaluator.get_hand_strength(result):.3f}")
