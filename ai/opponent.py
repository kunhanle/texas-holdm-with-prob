"""
AI Opponent Logic for Texas Hold'em
AI 對手決策邏輯
"""

import random
from enum import Enum, auto
from typing import List, Tuple, Optional, Dict, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from game.card import Card
    from game.player import Player
    from game.table import Table, GameStage


class AIDifficulty(Enum):
    """AI 難度等級"""
    EASY = "easy"       # 初級：隨機決策
    MEDIUM = "medium"   # 中級：基於手牌強度
    HARD = "hard"       # 高級：考慮機率和對手


class AIPersonality(Enum):
    """AI 個性類型"""
    TIGHT = "tight"           # 保守型：只玩強牌
    AGGRESSIVE = "aggressive" # 激進型：常加注
    BALANCED = "balanced"     # 平衡型：混合策略
    LOOSE = "loose"           # 鬆弛型：玩很多手牌


@dataclass
class AIDecision:
    """AI 決策結果"""
    action: str
    amount: int
    reasoning: str  # 決策理由（用於教學）
    confidence: float  # 信心程度 0-1


class AIOpponent:
    """
    AI 對手類別
    
    根據難度和個性做出決策
    """
    
    # 起手牌強度評分（Chen formula 簡化版）
    PREFLOP_HAND_RANKINGS = {
        # 頂級起手牌 (Tier 1)
        ("A", "A"): 20, ("K", "K"): 17, ("Q", "Q"): 14, ("J", "J"): 12,
        ("A", "K", True): 11,  # 同花
        ("A", "K", False): 10,
        ("A", "Q", True): 10,
        ("10", "10"): 10,
        # 強牌 (Tier 2)
        ("A", "Q", False): 9, ("A", "J", True): 9, ("K", "Q", True): 9,
        ("9", "9"): 9,
        ("A", "10", True): 8, ("K", "Q", False): 8, ("K", "J", True): 8,
        ("8", "8"): 8,
        # 中等牌 (Tier 3)
        ("A", "J", False): 7, ("A", "10", False): 7,
        ("K", "J", False): 7, ("Q", "J", True): 7,
        ("7", "7"): 7, ("6", "6"): 6, ("5", "5"): 5,
        # 其他對子
        ("4", "4"): 4, ("3", "3"): 3, ("2", "2"): 2,
    }
    
    def __init__(self, difficulty: AIDifficulty = AIDifficulty.MEDIUM,
                 personality: AIPersonality = AIPersonality.BALANCED):
        self.difficulty = difficulty
        self.personality = personality
        
        # 個性參數
        self._setup_personality()
    
    def _setup_personality(self) -> None:
        """根據個性設置參數"""
        if self.personality == AIPersonality.TIGHT:
            self.min_hand_strength_to_play = 0.4  # 只玩較強的牌
            self.bluff_frequency = 0.05  # 很少詐唬
            self.aggression_factor = 0.3
        elif self.personality == AIPersonality.AGGRESSIVE:
            self.min_hand_strength_to_play = 0.2
            self.bluff_frequency = 0.25  # 經常詐唬
            self.aggression_factor = 0.8
        elif self.personality == AIPersonality.LOOSE:
            self.min_hand_strength_to_play = 0.15  # 玩很多手牌
            self.bluff_frequency = 0.15
            self.aggression_factor = 0.5
        else:  # BALANCED
            self.min_hand_strength_to_play = 0.25
            self.bluff_frequency = 0.12
            self.aggression_factor = 0.5
    
    def make_decision(self, player: 'Player', table: 'Table',
                     win_probability: float = 0.5,
                     pot_odds: float = 0.0) -> AIDecision:
        """
        做出決策
        
        Args:
            player: AI 玩家
            table: 牌桌狀態
            win_probability: 勝率（由機率引擎計算）
            pot_odds: 底池賠率
            
        Returns:
            AIDecision 決策結果
        """
        if self.difficulty == AIDifficulty.EASY:
            return self._easy_decision(player, table)
        elif self.difficulty == AIDifficulty.MEDIUM:
            return self._medium_decision(player, table, win_probability)
        else:
            return self._hard_decision(player, table, win_probability, pot_odds)
    
    def _easy_decision(self, player: 'Player', table: 'Table') -> AIDecision:
        """
        初級 AI：幾乎隨機決策
        """
        actions = table.get_available_actions()
        
        # 隨機選擇動作，但稍微偏向合理選擇
        action_weights = {
            "fold": 20,
            "check": 40,
            "call": 30,
            "bet": 15,
            "raise": 10,
            "all_in": 2
        }
        
        weighted_actions = []
        for action, amount in actions:
            weight = action_weights.get(action, 10)
            weighted_actions.append((action, amount, weight))
        
        total_weight = sum(w for _, _, w in weighted_actions)
        r = random.random() * total_weight
        
        cumulative = 0
        for action, amount, weight in weighted_actions:
            cumulative += weight
            if r <= cumulative:
                return AIDecision(
                    action=action,
                    amount=amount,
                    reasoning="隨機選擇",
                    confidence=0.3
                )
        
        # 預設棄牌
        return AIDecision("fold", 0, "無法決定", 0.1)
    
    def _medium_decision(self, player: 'Player', table: 'Table',
                        win_probability: float) -> AIDecision:
        """
        中級 AI：基於手牌強度和勝率決策
        """
        actions = table.get_available_actions()
        actions_dict = {a: amt for a, amt in actions}
        
        amount_to_call = actions_dict.get("call", 0)
        
        # 根據勝率決策
        if win_probability >= 0.7:
            # 強牌：加注
            if "raise" in actions_dict:
                raise_amount = self._calculate_raise_amount(player, table, "large")
                return AIDecision("raise", raise_amount, 
                                f"勝率高 ({win_probability:.0%})，加注", 0.8)
            elif "bet" in actions_dict:
                bet_amount = self._calculate_bet_amount(player, table, "large")
                return AIDecision("bet", bet_amount,
                                f"勝率高 ({win_probability:.0%})，下注", 0.8)
            elif "call" in actions_dict:
                return AIDecision("call", amount_to_call,
                                f"勝率高，跟注", 0.7)
            else:
                return AIDecision("check", 0, "過牌觀察", 0.6)
        
        elif win_probability >= 0.45:
            # 中等：跟注或過牌
            if amount_to_call == 0 and "check" in actions_dict:
                return AIDecision("check", 0, "勝率中等，過牌", 0.5)
            elif amount_to_call > 0 and amount_to_call <= player.chips * 0.2:
                return AIDecision("call", amount_to_call,
                                f"勝率中等 ({win_probability:.0%})，跟注小額", 0.5)
            elif "bet" in actions_dict and random.random() < self.aggression_factor:
                bet_amount = self._calculate_bet_amount(player, table, "small")
                return AIDecision("bet", bet_amount, "試探性下注", 0.4)
            else:
                return AIDecision("fold", 0, "跟注太大，棄牌", 0.4)
        
        elif win_probability >= 0.25:
            # 弱牌：謹慎行事
            if "check" in actions_dict:
                return AIDecision("check", 0, "勝率偏低，過牌", 0.4)
            elif amount_to_call <= table.big_blind:
                return AIDecision("call", amount_to_call, "便宜跟注", 0.3)
            elif random.random() < self.bluff_frequency:
                if "raise" in actions_dict:
                    return AIDecision("raise", actions_dict.get("raise", 0),
                                    "詐唬", 0.2)
            return AIDecision("fold", 0, f"勝率低 ({win_probability:.0%})，棄牌", 0.5)
        
        else:
            # 很弱：棄牌
            if "check" in actions_dict:
                return AIDecision("check", 0, "免費看牌", 0.3)
            return AIDecision("fold", 0, f"勝率太低 ({win_probability:.0%})，棄牌", 0.7)
    
    def _hard_decision(self, player: 'Player', table: 'Table',
                      win_probability: float, pot_odds: float) -> AIDecision:
        """
        高級 AI：考慮機率、底池賠率和對手行為
        """
        actions = table.get_available_actions()
        actions_dict = {a: amt for a, amt in actions}
        
        amount_to_call = actions_dict.get("call", 0)
        pot = table.pot.total
        
        # 計算期望值
        if amount_to_call > 0:
            ev = (win_probability * (pot + amount_to_call)) - ((1 - win_probability) * amount_to_call)
        else:
            ev = 0
        
        # 判斷是否有正 EV
        positive_ev = ev > 0 or win_probability > pot_odds
        
        # 根據 EV 和勝率決策
        if win_probability >= 0.65 and positive_ev:
            # 非常有利：價值下注/加注
            if "raise" in actions_dict:
                # 根據勝率調整加注大小
                size = "large" if win_probability >= 0.75 else "medium"
                raise_amount = self._calculate_raise_amount(player, table, size)
                return AIDecision("raise", raise_amount,
                                f"正EV (勝率{win_probability:.0%} > 底池賠率{pot_odds:.0%})，價值加注",
                                0.85)
            elif "bet" in actions_dict:
                size = "large" if win_probability >= 0.75 else "medium"
                bet_amount = self._calculate_bet_amount(player, table, size)
                return AIDecision("bet", bet_amount,
                                f"有利位置，價值下注", 0.8)
            elif "call" in actions_dict:
                return AIDecision("call", amount_to_call, "強牌跟注", 0.8)
            else:
                return AIDecision("check", 0, "陷阱過牌", 0.7)
        
        elif positive_ev and win_probability >= 0.4:
            # 有正 EV：可以跟注
            if "check" in actions_dict:
                # 有時下注，有時過牌
                if random.random() < 0.4:
                    if "bet" in actions_dict:
                        bet_amount = self._calculate_bet_amount(player, table, "small")
                        return AIDecision("bet", bet_amount, "平衡策略，下注", 0.5)
                return AIDecision("check", 0, "過牌觀察", 0.5)
            elif "call" in actions_dict:
                return AIDecision("call", amount_to_call,
                                f"正EV ({ev:.0f})，跟注", 0.6)
            else:
                return AIDecision("fold", 0, "無法跟注", 0.5)
        
        elif not positive_ev and win_probability < 0.35:
            # 負 EV 且弱牌
            if "check" in actions_dict:
                return AIDecision("check", 0, "負EV，過牌", 0.6)
            
            # 考慮詐唬
            if random.random() < self.bluff_frequency:
                active_count = len([p for p in table.players if p.is_active and p != player])
                if active_count <= 2 and "raise" in actions_dict:
                    bluff_amount = self._calculate_raise_amount(player, table, "medium")
                    return AIDecision("raise", bluff_amount,
                                    "對手少，嘗試詐唬", 0.3)
            
            return AIDecision("fold", 0,
                            f"負EV (勝率{win_probability:.0%} < 底池賠率{pot_odds:.0%})，棄牌",
                            0.7)
        
        else:
            # 邊緣情況
            if "check" in actions_dict:
                return AIDecision("check", 0, "邊緣牌，過牌", 0.5)
            elif amount_to_call <= table.big_blind * 2:
                return AIDecision("call", amount_to_call, "小額跟注", 0.4)
            else:
                return AIDecision("fold", 0, "邊緣情況，保守棄牌", 0.5)
    
    def _calculate_bet_amount(self, player: 'Player', table: 'Table', 
                             size: str = "medium") -> int:
        """計算下注金額"""
        pot = table.pot.total
        
        if size == "small":
            amount = int(pot * 0.33)
        elif size == "large":
            amount = int(pot * 0.75)
        else:  # medium
            amount = int(pot * 0.5)
        
        # 確保至少是大盲注
        amount = max(amount, table.big_blind)
        # 確保不超過籌碼
        amount = min(amount, player.chips)
        
        return amount
    
    def _calculate_raise_amount(self, player: 'Player', table: 'Table',
                               size: str = "medium") -> int:
        """計算加注金額"""
        current_bet = table.betting_round.current_bet if table.betting_round else 0
        pot = table.pot.total
        
        if size == "small":
            raise_to = current_bet + int(pot * 0.33)
        elif size == "large":
            raise_to = current_bet + int(pot * 0.75)
        else:  # medium
            raise_to = current_bet + int(pot * 0.5)
        
        # 確保符合最小加注
        min_raise = table.betting_round.get_min_raise_to() if table.betting_round else current_bet * 2
        raise_to = max(raise_to, min_raise)
        
        # 確保不超過籌碼
        raise_to = min(raise_to, player.chips + player.current_bet)
        
        return raise_to
    
    @staticmethod
    def evaluate_preflop_hand(card1_rank: str, card2_rank: str, suited: bool) -> int:
        """
        評估起手牌強度
        
        Returns:
            強度分數 (0-20)
        """
        # 標準化點數
        r1, r2 = card1_rank.upper(), card2_rank.upper()
        if r1 == "T":
            r1 = "10"
        if r2 == "T":
            r2 = "10"
        
        # 確保 r1 >= r2
        rank_order = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        if rank_order.index(r1) < rank_order.index(r2):
            r1, r2 = r2, r1
        
        # 對子
        if r1 == r2:
            key = (r1, r2)
            return AIOpponent.PREFLOP_HAND_RANKINGS.get(key, 5)
        
        # 非對子
        key = (r1, r2, suited)
        score = AIOpponent.PREFLOP_HAND_RANKINGS.get(key, 0)
        
        if score == 0:
            # 使用簡化評分
            idx1 = rank_order.index(r1)
            idx2 = rank_order.index(r2)
            score = (idx1 + idx2) / 4
            if suited:
                score += 2
            if abs(idx1 - idx2) == 1:  # 連張
                score += 1
        
        return int(score)


# AI 名稱生成
AI_NAMES = [
    ("阿強", AIPersonality.AGGRESSIVE),
    ("小明", AIPersonality.BALANCED),
    ("老王", AIPersonality.TIGHT),
    ("阿花", AIPersonality.LOOSE),
    ("大雄", AIPersonality.BALANCED),
    ("靜香", AIPersonality.TIGHT),
    ("胖虎", AIPersonality.AGGRESSIVE),
    ("小夫", AIPersonality.LOOSE),
]


def create_ai_players(count: int, difficulty: AIDifficulty = AIDifficulty.MEDIUM,
                     starting_chips: int = 1000) -> List['Player']:
    """
    創建指定數量的 AI 玩家
    """
    from game.player import AIPlayer
    
    players = []
    available_names = AI_NAMES.copy()
    random.shuffle(available_names)
    
    for i in range(min(count, len(available_names))):
        name, personality = available_names[i]
        player = AIPlayer(
            name=name,
            chips=starting_chips,
            position=i + 1,
            difficulty=difficulty.value,
            personality=personality.value
        )
        players.append(player)
    
    return players


if __name__ == "__main__":
    # 測試 AI
    ai = AIOpponent(AIDifficulty.HARD, AIPersonality.AGGRESSIVE)
    
    # 測試起手牌評估
    test_hands = [
        ("A", "A", False),
        ("A", "K", True),
        ("Q", "J", True),
        ("7", "2", False),
    ]
    
    print("起手牌評估:")
    for r1, r2, suited in test_hands:
        score = AIOpponent.evaluate_preflop_hand(r1, r2, suited)
        suited_str = "同花" if suited else "雜色"
        print(f"  {r1}{r2} {suited_str}: {score}")
