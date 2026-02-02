"""
Player class for Texas Hold'em
玩家類別
"""

from typing import List, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum, auto

if TYPE_CHECKING:
    from .card import Card


class PlayerAction(Enum):
    """玩家可執行的動作"""
    FOLD = auto()       # 棄牌
    CHECK = auto()      # 過牌
    CALL = auto()       # 跟注
    BET = auto()        # 下注
    RAISE = auto()      # 加注
    ALL_IN = auto()     # 全押


@dataclass
class ActionResult:
    """動作結果"""
    action: PlayerAction
    amount: int = 0
    message: str = ""
    
    def __str__(self) -> str:
        if self.amount > 0:
            return f"{self.action.name} ${self.amount}"
        return self.action.name


class Player:
    """
    玩家類別
    
    Attributes:
        name: 玩家名稱
        chips: 籌碼數量
        hole_cards: 手牌（2張）
        is_human: 是否為人類玩家
        is_active: 是否仍在本局（未棄牌）
        is_all_in: 是否已全押
        current_bet: 當前輪的下注金額
        total_bet: 本局總下注金額
        position: 座位位置
    """
    
    def __init__(self, name: str, chips: int = 1000, is_human: bool = False, position: int = 0):
        self.name = name
        self.chips = chips
        self.is_human = is_human
        self.position = position
        
        # 每局重置的狀態
        self.hole_cards: List['Card'] = []
        self.is_active: bool = True
        self.is_all_in: bool = False
        self.current_bet: int = 0
        self.total_bet: int = 0
        
        # 動作記錄
        self.last_action: Optional[str] = None
        self.last_action_amount: int = 0
        
        # 統計數據（用於教學）
        self.hands_played: int = 0
        self.hands_won: int = 0
        self.total_winnings: int = 0
        self.correct_decisions: int = 0
        self.total_decisions: int = 0
    
    def reset_for_new_hand(self) -> None:
        """為新的一局重置狀態"""
        self.hole_cards = []
        self.is_active = True
        self.is_all_in = False
        self.current_bet = 0
        self.current_bet = 0
        self.total_bet = 0
        self.last_action = None
        self.last_action_amount = 0
    
    def reset_for_new_round(self) -> None:
        """為新的下注輪重置"""
        self.current_bet = 0
        self.last_action = None
        self.last_action_amount = 0
    
    def receive_cards(self, cards: List['Card']) -> None:
        """接收手牌"""
        self.hole_cards = cards
    
    def bet(self, amount: int) -> ActionResult:
        """
        下注指定金額
        
        Returns:
            ActionResult 包含實際下注金額
        """
        actual_amount = min(amount, self.chips)
        self.chips -= actual_amount
        self.current_bet += actual_amount
        self.total_bet += actual_amount
        
        if self.chips == 0:
            self.is_all_in = True
            return ActionResult(PlayerAction.ALL_IN, actual_amount, 
                              f"{self.name} 全押 ${actual_amount}")
        
        return ActionResult(PlayerAction.BET, actual_amount,
                          f"{self.name} 下注 ${actual_amount}")
    
    def call(self, amount_to_call: int) -> ActionResult:
        """
        跟注
        
        Args:
            amount_to_call: 需要跟注的金額
        """
        actual_amount = min(amount_to_call, self.chips)
        self.chips -= actual_amount
        self.current_bet += actual_amount
        self.total_bet += actual_amount
        
        if self.chips == 0:
            self.is_all_in = True
            return ActionResult(PlayerAction.ALL_IN, actual_amount,
                              f"{self.name} 全押跟注 ${actual_amount}")
        
        return ActionResult(PlayerAction.CALL, actual_amount,
                          f"{self.name} 跟注 ${actual_amount}")
    
    def raise_bet(self, total_amount: int) -> ActionResult:
        """
        加注到指定總額
        
        Args:
            total_amount: 本輪下注的總額（包括之前的下注）
        """
        additional = total_amount - self.current_bet
        actual_additional = min(additional, self.chips)
        
        self.chips -= actual_additional
        self.current_bet += actual_additional
        self.total_bet += actual_additional
        
        if self.chips == 0:
            self.is_all_in = True
            return ActionResult(PlayerAction.ALL_IN, self.current_bet,
                              f"{self.name} 全押加注到 ${self.current_bet}")
        
        return ActionResult(PlayerAction.RAISE, self.current_bet,
                          f"{self.name} 加注到 ${self.current_bet}")
    
    def fold(self) -> ActionResult:
        """棄牌"""
        self.is_active = False
        return ActionResult(PlayerAction.FOLD, 0, f"{self.name} 棄牌")
    
    def check(self) -> ActionResult:
        """過牌"""
        return ActionResult(PlayerAction.CHECK, 0, f"{self.name} 過牌")
    
    def all_in(self) -> ActionResult:
        """全押"""
        amount = self.chips
        self.current_bet += amount
        self.total_bet += amount
        self.chips = 0
        self.is_all_in = True
        return ActionResult(PlayerAction.ALL_IN, amount,
                          f"{self.name} 全押 ${amount}")
    
    def win_pot(self, amount: int) -> None:
        """贏得底池"""
        self.chips += amount
        self.total_winnings += amount
        self.hands_won += 1
    
    def can_act(self) -> bool:
        """玩家是否可以行動"""
        return self.is_active and not self.is_all_in
    
    def get_available_actions(self, current_bet: int, min_raise: int) -> List[PlayerAction]:
        """
        獲取可用的動作列表
        
        Args:
            current_bet: 當前需要跟注的金額
            min_raise: 最小加注額
        """
        actions = [PlayerAction.FOLD]
        
        amount_to_call = current_bet - self.current_bet
        
        if amount_to_call == 0:
            actions.append(PlayerAction.CHECK)
        elif self.chips >= amount_to_call:
            actions.append(PlayerAction.CALL)
        
        if self.chips > amount_to_call:
            if current_bet == 0:
                actions.append(PlayerAction.BET)
            else:
                actions.append(PlayerAction.RAISE)
        
        actions.append(PlayerAction.ALL_IN)
        
        return actions
    
    @property
    def win_rate(self) -> float:
        """勝率"""
        if self.hands_played == 0:
            return 0.0
        return self.hands_won / self.hands_played
    
    @property
    def decision_accuracy(self) -> float:
        """決策正確率（用於教學統計）"""
        if self.total_decisions == 0:
            return 0.0
        return self.correct_decisions / self.total_decisions
    
    def __str__(self) -> str:
        status = "活躍" if self.is_active else "已棄牌"
        if self.is_all_in:
            status = "全押"
        cards = ' '.join(c.display for c in self.hole_cards) if self.hole_cards else "未發牌"
        return f"{self.name} (${self.chips}) - {cards} [{status}]"
    
    def __repr__(self) -> str:
        return f"Player(name='{self.name}', chips={self.chips}, is_human={self.is_human})"


class HumanPlayer(Player):
    """人類玩家"""
    
    def __init__(self, name: str = "玩家", chips: int = 1000, position: int = 0):
        super().__init__(name, chips, is_human=True, position=position)


class AIPlayer(Player):
    """AI 玩家基類"""
    
    def __init__(self, name: str, chips: int = 1000, position: int = 0, 
                 difficulty: str = "medium", personality: str = "balanced"):
        super().__init__(name, chips, is_human=False, position=position)
        self.difficulty = difficulty  # easy, medium, hard
        self.personality = personality  # tight, aggressive, balanced
    
    def __repr__(self) -> str:
        return f"AIPlayer(name='{self.name}', difficulty='{self.difficulty}', personality='{self.personality}')"


if __name__ == "__main__":
    # 測試玩家類別
    from .card import cards_from_string
    
    player = HumanPlayer("測試玩家", 1000)
    print(f"創建玩家: {player}")
    
    # 發牌
    cards = cards_from_string("As Kh")
    player.receive_cards(cards)
    print(f"發牌後: {player}")
    
    # 下注
    result = player.bet(100)
    print(f"動作: {result}")
    print(f"下注後: {player}")
    
    # 加注
    result = player.raise_bet(300)
    print(f"動作: {result}")
    print(f"加注後: {player}")
