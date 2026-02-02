"""
Probability Calculator for Texas Hold'em
機率計算引擎 - 計算勝率、Outs、底池賠率和期望值
"""

import random
from typing import List, Tuple, Dict, Set, Optional
from dataclasses import dataclass
from itertools import combinations
from collections import Counter
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.card import Card, Deck, Suit, Rank
from game.hand_evaluator import HandEvaluator, HandResult, HandRank


@dataclass
class Outs:
    """
    Outs 計算結果
    
    Outs = 能改善你手牌的剩餘牌數
    """
    count: int              # Outs 數量
    cards: List[Card]       # 具體的 Outs 牌
    target_hand: str        # 目標牌型
    probability: float      # 成牌機率
    
    def __str__(self) -> str:
        return f"{self.target_hand}: {self.count} outs ({self.probability:.1%})"


@dataclass
class OddsResult:
    """
    完整的機率分析結果
    """
    win_rate: float         # 勝率
    tie_rate: float         # 平局率
    lose_rate: float        # 敗率
    
    outs_list: List[Outs]   # 各種成牌的 Outs
    total_outs: int         # 總 Outs 數
    
    pot_odds: float         # 底池賠率（需要額外輸入）
    expected_value: float   # 期望值
    
    hand_strength: float    # 當前手牌強度 (0-1)
    
    def __str__(self) -> str:
        lines = [
            f"勝率: {self.win_rate:.1%} | 平局: {self.tie_rate:.1%} | 敗率: {self.lose_rate:.1%}",
            f"手牌強度: {self.hand_strength:.2f}",
        ]
        if self.outs_list:
            lines.append("Outs 分析:")
            for outs in self.outs_list:
                lines.append(f"  {outs}")
        if self.pot_odds > 0:
            lines.append(f"底池賠率: {self.pot_odds:.1%}")
            ev_str = f"+${self.expected_value:.0f}" if self.expected_value >= 0 else f"-${abs(self.expected_value):.0f}"
            lines.append(f"期望值: {ev_str}")
        return '\n'.join(lines)


class ProbabilityCalculator:
    """
    德州撲克機率計算器
    
    提供各種機率計算功能，用於教學和 AI 決策
    """
    
    def __init__(self, simulation_count: int = 1000):
        """
        Args:
            simulation_count: 蒙地卡羅模擬次數（越多越準確，但越慢）
        """
        self.simulation_count = simulation_count
    
    def calculate_win_rate(self, hole_cards: List[Card], 
                          community_cards: List[Card],
                          num_opponents: int = 1) -> Tuple[float, float, float]:
        """
        使用蒙地卡羅模擬計算勝率
        
        Args:
            hole_cards: 玩家手牌 (2張)
            community_cards: 公共牌 (0-5張)
            num_opponents: 對手數量
            
        Returns:
            (win_rate, tie_rate, lose_rate)
        """
        wins = 0
        ties = 0
        losses = 0
        
        # 建立剩餘牌組
        used_cards = set(hole_cards + community_cards)
        remaining_deck = [
            Card(suit, rank)
            for suit in Suit
            for rank in Rank
            if Card(suit, rank) not in used_cards
        ]
        
        cards_to_deal = 5 - len(community_cards)
        
        for _ in range(self.simulation_count):
            # 洗牌
            random.shuffle(remaining_deck)
            deck_index = 0
            
            # 完成公共牌
            simulated_community = community_cards.copy()
            for _ in range(cards_to_deal):
                simulated_community.append(remaining_deck[deck_index])
                deck_index += 1
            
            # 發對手手牌並評估
            player_hand = HandEvaluator.evaluate(hole_cards + simulated_community)
            
            player_wins = True
            any_tie = False
            
            for _ in range(num_opponents):
                opponent_hole = [remaining_deck[deck_index], remaining_deck[deck_index + 1]]
                deck_index += 2
                opponent_hand = HandEvaluator.evaluate(opponent_hole + simulated_community)
                
                comparison = player_hand.compare_to(opponent_hand)
                if comparison < 0:
                    player_wins = False
                    break
                elif comparison == 0:
                    any_tie = True
            
            if not player_wins:
                losses += 1
            elif any_tie:
                ties += 1
            else:
                wins += 1
        
        total = self.simulation_count
        return wins / total, ties / total, losses / total
    
    def calculate_outs(self, hole_cards: List[Card], 
                      community_cards: List[Card]) -> List[Outs]:
        """
        計算各種成牌的 Outs
        
        Args:
            hole_cards: 玩家手牌
            community_cards: 公共牌
            
        Returns:
            各種成牌機會的 Outs 列表
        """
        # Pre-flop (no community cards) or River (5 community cards) - no outs to calculate
        if len(community_cards) == 0 or len(community_cards) >= 5:
            return []
        
        outs_list = []
        all_cards = hole_cards + community_cards
        
        # Need at least 5 cards to evaluate current hand
        if len(all_cards) < 5:
            current_result = None
        else:
            current_result = HandEvaluator.evaluate(all_cards)
        
        # 建立剩餘牌組
        used_cards = set(all_cards)
        remaining = [
            Card(suit, rank)
            for suit in Suit
            for rank in Rank
            if Card(suit, rank) not in used_cards
        ]
        
        # 檢查各種成牌可能
        
        # 1. 同花 Outs
        flush_outs = self._find_flush_outs(all_cards, remaining)
        if flush_outs:
            outs_list.append(flush_outs)
        
        # 2. 順子 Outs
        straight_outs = self._find_straight_outs(all_cards, remaining)
        if straight_outs:
            outs_list.append(straight_outs)
        
        # 3. 三條 / 葫蘆 Outs
        set_outs = self._find_set_outs(all_cards, remaining, current_result)
        if set_outs:
            outs_list.append(set_outs)
        
        # 4. 對子改進 Outs
        pair_outs = self._find_pair_outs(all_cards, remaining, current_result)
        if pair_outs:
            outs_list.append(pair_outs)
        
        return outs_list
    
    def _find_flush_outs(self, all_cards: List[Card], 
                        remaining: List[Card]) -> Optional[Outs]:
        """找同花 Outs"""
        suits = [c.suit for c in all_cards]
        suit_counts = Counter(suits)
        
        for suit, count in suit_counts.items():
            if count == 4:
                # 4張同花，需要1張
                flush_cards = [c for c in remaining if c.suit == suit]
                cards_left = 52 - len(all_cards)
                # 使用 4-2 法則
                prob = len(flush_cards) * 4 / 100 if len(all_cards) == 5 else len(flush_cards) * 2 / 100
                return Outs(len(flush_cards), flush_cards, "同花", min(prob, 1.0))
            elif count == 3 and len(all_cards) == 5:
                # Flop 階段，3張同花，需要2張
                flush_cards = [c for c in remaining if c.suit == suit]
                # 後門同花機率約 4%
                return Outs(len(flush_cards), flush_cards, "後門同花", 0.04)
        
        return None
    
    def _find_straight_outs(self, all_cards: List[Card],
                           remaining: List[Card]) -> Optional[Outs]:
        """找順子 Outs"""
        values = sorted(set(c.rank.value for c in all_cards))
        
        # 尋找缺口
        outs_cards = []
        
        # 檢查各種順子可能
        for start in range(1, 11):  # 順子可以從 A(1) 到 10 開始
            straight_values = set(range(start, start + 5))
            if start == 1:
                straight_values = {14, 2, 3, 4, 5}  # A-2-3-4-5
            elif start == 10:
                straight_values = {10, 11, 12, 13, 14}  # 10-J-Q-K-A
            
            current_values = set(values)
            if 14 in current_values:
                current_values.add(1)  # A 可以當 1
            
            overlap = current_values & straight_values
            missing = straight_values - current_values
            
            if len(overlap) == 4 and len(missing) == 1:
                # 開放式 or 卡張順子聽牌
                needed_value = missing.pop()
                if needed_value == 1:
                    needed_value = 14  # 需要 A
                needed_rank = Rank(needed_value)
                outs_cards.extend([c for c in remaining if c.rank == needed_rank])
        
        if outs_cards:
            # 去重
            unique_outs = list(set(outs_cards))
            cards_left = 52 - len(all_cards)
            # 使用 4-2 法則
            prob = len(unique_outs) * 4 / 100 if len(all_cards) == 5 else len(unique_outs) * 2 / 100
            
            # 判斷是開放式還是卡張
            is_open_ended = len(unique_outs) >= 8
            name = "雙面順子聽牌" if is_open_ended else "卡張順子聽牌"
            
            return Outs(len(unique_outs), unique_outs, name, min(prob, 1.0))
        
        return None
    
    def _find_set_outs(self, all_cards: List[Card], remaining: List[Card],
                      current_result: Optional[HandResult]) -> Optional[Outs]:
        """找三條/葫蘆 Outs"""
        if current_result is None:
            return None
        
        ranks = [c.rank for c in all_cards]
        rank_counts = Counter(ranks)
        
        # 如果已經是兩對，找葫蘆 outs
        if current_result.rank == HandRank.TWO_PAIR:
            outs_cards = []
            for rank, count in rank_counts.items():
                if count == 2:
                    outs_cards.extend([c for c in remaining if c.rank == rank])
            if outs_cards:
                prob = len(outs_cards) * 4 / 100 if len(all_cards) == 5 else len(outs_cards) * 2 / 100
                return Outs(len(outs_cards), outs_cards, "葫蘆", min(prob, 1.0))
        
        # 如果是一對，找三條 outs
        elif current_result.rank == HandRank.ONE_PAIR:
            for rank, count in rank_counts.items():
                if count == 2:
                    outs_cards = [c for c in remaining if c.rank == rank]
                    if outs_cards:
                        prob = len(outs_cards) * 4 / 100 if len(all_cards) == 5 else len(outs_cards) * 2 / 100
                        return Outs(len(outs_cards), outs_cards, "三條", min(prob, 1.0))
        
        return None
    
    def _find_pair_outs(self, all_cards: List[Card], remaining: List[Card],
                       current_result: Optional[HandResult]) -> Optional[Outs]:
        """找配對 Outs（改進高牌到一對）"""
        if current_result is None or current_result.rank != HandRank.HIGH_CARD:
            return None
        
        # 只考慮手牌配對（overcards）
        hole_ranks = set(c.rank for c in all_cards[:2])  # 假設前2張是手牌
        outs_cards = [c for c in remaining if c.rank in hole_ranks]
        
        if outs_cards:
            prob = len(outs_cards) * 4 / 100 if len(all_cards) == 5 else len(outs_cards) * 2 / 100
            return Outs(len(outs_cards), outs_cards, "配對", min(prob, 1.0))
        
        return None
    
    def calculate_pot_odds(self, pot: int, call_amount: int) -> float:
        """
        計算底池賠率
        
        底池賠率 = 跟注金額 / (底池 + 跟注金額)
        
        例如：底池 $100，跟注 $20
        底池賠率 = 20 / (100 + 20) = 16.7%
        
        如果你的勝率 > 底池賠率，則跟注是有利的
        """
        if call_amount == 0:
            return 0.0
        return call_amount / (pot + call_amount)
    
    def calculate_expected_value(self, win_rate: float, pot: int, 
                                call_amount: int) -> float:
        """
        計算期望值 (EV)
        
        EV = (勝率 × 可贏金額) - (敗率 × 需投入金額)
        
        正 EV = 長期有利
        負 EV = 長期不利
        """
        win_amount = pot + call_amount
        ev = (win_rate * win_amount) - ((1 - win_rate) * call_amount)
        return ev
    
    def full_analysis(self, hole_cards: List[Card], community_cards: List[Card],
                     num_opponents: int = 1, pot: int = 0, 
                     call_amount: int = 0) -> OddsResult:
        """
        完整的機率分析
        
        Returns:
            OddsResult 包含所有分析結果
        """
        # 計算勝率
        win_rate, tie_rate, lose_rate = self.calculate_win_rate(
            hole_cards, community_cards, num_opponents
        )
        
        # 計算 Outs
        outs_list = self.calculate_outs(hole_cards, community_cards)
        total_outs = sum(o.count for o in outs_list)
        
        # 計算底池賠率和 EV
        pot_odds = self.calculate_pot_odds(pot, call_amount)
        ev = self.calculate_expected_value(win_rate, pot, call_amount) if call_amount > 0 else 0
        
        # 計算當前手牌強度
        if community_cards:
            all_cards = hole_cards + community_cards
            result = HandEvaluator.evaluate(all_cards)
            hand_strength = HandEvaluator.get_hand_strength(result)
        else:
            # Pre-flop 使用簡化評估
            r1 = hole_cards[0].rank.symbol
            r2 = hole_cards[1].rank.symbol
            suited = hole_cards[0].suit == hole_cards[1].suit
            from ai.opponent import AIOpponent
            score = AIOpponent.evaluate_preflop_hand(r1, r2, suited)
            hand_strength = score / 20  # 標準化到 0-1
        
        return OddsResult(
            win_rate=win_rate,
            tie_rate=tie_rate,
            lose_rate=lose_rate,
            outs_list=outs_list,
            total_outs=total_outs,
            pot_odds=pot_odds,
            expected_value=ev,
            hand_strength=hand_strength
        )
    
    @staticmethod
    def apply_rule_of_4_2(outs: int, stage: str) -> float:
        """
        4-2 法則快速計算成牌機率
        
        Flop 階段（還有 2 張牌要發）: outs × 4
        Turn 階段（還有 1 張牌要發）: outs × 2
        
        這是一個快速估算，精確度約在 1-2% 內
        """
        if stage.lower() == "flop":
            return min(outs * 4 / 100, 1.0)
        else:  # turn or river
            return min(outs * 2 / 100, 1.0)


# 便利函數
def quick_equity(hole_str: str, board_str: str = "", opponents: int = 1) -> float:
    """
    快速計算權益
    
    Example:
        quick_equity("As Kh", "Qs Jd 2c", 3)
    """
    from game.card import cards_from_string
    
    hole = cards_from_string(hole_str)
    board = cards_from_string(board_str) if board_str else []
    
    calc = ProbabilityCalculator(simulation_count=2000)
    win, tie, _ = calc.calculate_win_rate(hole, board, opponents)
    return win + tie * 0.5


if __name__ == "__main__":
    from game.card import cards_from_string
    
    # 測試機率計算
    calc = ProbabilityCalculator(simulation_count=3000)
    
    # 測試案例：同花聽牌
    hole = cards_from_string("Qs Js")
    board = cards_from_string("9s 2s 7h")
    
    print("=" * 50)
    print("測試案例: Q♠ J♠ vs 9♠ 2♠ 7♥")
    print("=" * 50)
    
    result = calc.full_analysis(hole, board, num_opponents=2, pot=200, call_amount=50)
    print(result)
    
    print("\n" + "=" * 50)
    print("4-2 法則測試:")
    print(f"9 outs 在 Flop: {ProbabilityCalculator.apply_rule_of_4_2(9, 'flop'):.1%}")
    print(f"9 outs 在 Turn: {ProbabilityCalculator.apply_rule_of_4_2(9, 'turn'):.1%}")
