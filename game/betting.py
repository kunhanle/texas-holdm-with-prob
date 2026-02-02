"""
Betting System for Texas Hold'em
下注系統 - 管理底池與下注輪
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from .player import Player


@dataclass
class SidePot:
    """邊池"""
    amount: int
    eligible_players: List[Player]
    
    def __str__(self) -> str:
        names = ', '.join(p.name for p in self.eligible_players)
        return f"邊池 ${self.amount} (參與者: {names})"


class Pot:
    """
    底池管理器
    
    處理主池和邊池的計算與分配
    """
    
    def __init__(self):
        self.total: int = 0
        self.contributions: Dict[Player, int] = {}
        self.side_pots: List[SidePot] = []
    
    def add_bet(self, player: Player, amount: int) -> None:
        """添加下注到底池"""
        self.total += amount
        self.contributions[player] = self.contributions.get(player, 0) + amount
    
    def reset(self) -> None:
        """重置底池"""
        self.total = 0
        self.contributions = {}
        self.side_pots = []
    
    def calculate_side_pots(self, active_players: List[Player]) -> None:
        """
        計算邊池
        
        當有玩家 All-in 時需要計算邊池
        """
        if not self.contributions:
            return
        
        self.side_pots = []
        
        # 獲取所有不同的投注金額（排序）
        bet_levels = sorted(set(self.contributions.values()))
        
        previous_level = 0
        remaining_players = list(active_players)
        
        for level in bet_levels:
            if not remaining_players:
                break
            
            # 計算這個層級的底池
            increment = level - previous_level
            pot_amount = 0
            eligible = []
            
            for player, contribution in self.contributions.items():
                if contribution >= level:
                    pot_amount += increment
                    if player in remaining_players or player.is_all_in:
                        eligible.append(player)
            
            if pot_amount > 0 and eligible:
                self.side_pots.append(SidePot(pot_amount, eligible))
            
            previous_level = level
            # 移除已經 All-in 且無法參與更高層級的玩家
            remaining_players = [p for p in remaining_players 
                               if self.contributions.get(p, 0) > level]
    
    def get_total_for_player(self, player: Player) -> int:
        """獲取玩家可贏得的最大金額"""
        player_contribution = self.contributions.get(player, 0)
        winnable = 0
        
        for p, contribution in self.contributions.items():
            winnable += min(contribution, player_contribution)
        
        return winnable
    
    def distribute_to_winners(self, winners: List[Player]) -> Dict[Player, int]:
        """
        將底池分配給贏家
        
        Args:
            winners: 贏家列表（可能有多個平局）
            
        Returns:
            每個贏家獲得的金額
        """
        payouts: Dict[Player, int] = {w: 0 for w in winners}
        
        if not self.side_pots:
            # 沒有邊池，簡單分配
            share = self.total // len(winners)
            for winner in winners:
                payouts[winner] = share
        else:
            # 處理邊池
            for side_pot in self.side_pots:
                # 找出這個邊池的贏家（必須是eligible的）
                pot_winners = [w for w in winners if w in side_pot.eligible_players]
                if pot_winners:
                    share = side_pot.amount // len(pot_winners)
                    for winner in pot_winners:
                        payouts[winner] += share
        
        return payouts
    
    def __str__(self) -> str:
        if self.side_pots:
            pots_str = '\n  '.join(str(sp) for sp in self.side_pots)
            return f"底池總計: ${self.total}\n  {pots_str}"
        return f"底池: ${self.total}"


class BettingRound:
    """
    下注輪管理器
    
    管理一輪下注的流程
    """
    
    def __init__(self, players: List[Player], small_blind: int = 10, big_blind: int = 20):
        self.players = players
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.current_bet: int = 0
        self.min_raise: int = big_blind
        self.last_raiser: Optional[Player] = None
        self.actions_this_round: List[Tuple[Player, str, int]] = []
    
    def reset_for_new_round(self) -> None:
        """為新的下注輪重置"""
        self.current_bet = 0
        self.last_raiser = None
        self.actions_this_round = []
        for player in self.players:
            player.reset_for_new_round()
    
    def post_blinds(self, dealer_position: int, pot: Pot) -> Tuple[int, int]:
        """
        收取大小盲注
        
        Args:
            dealer_position: 莊家位置
            pot: 底池
            
        Returns:
            (small_blind_amount, big_blind_amount) 實際收取的金額
        """
        active_players = [p for p in self.players if p.chips > 0]
        num_players = len(active_players)
        
        if num_players < 2:
            return 0, 0
        
        # 小盲注位置（莊家的下一位）
        sb_pos = (dealer_position + 1) % num_players
        # 大盲注位置（小盲注的下一位）
        bb_pos = (dealer_position + 2) % num_players
        
        # 收取小盲注
        sb_player = active_players[sb_pos]
        sb_amount = min(self.small_blind, sb_player.chips)
        sb_player.bet(sb_amount)
        pot.add_bet(sb_player, sb_amount)
        self.actions_this_round.append((sb_player, "小盲注", sb_amount))
        
        # 收取大盲注
        bb_player = active_players[bb_pos]
        bb_amount = min(self.big_blind, bb_player.chips)
        bb_player.bet(bb_amount)
        pot.add_bet(bb_player, bb_amount)
        self.actions_this_round.append((bb_player, "大盲注", bb_amount))
        
        self.current_bet = self.big_blind
        
        return sb_amount, bb_amount
    
    def get_amount_to_call(self, player: Player) -> int:
        """獲取玩家需要跟注的金額"""
        return max(0, self.current_bet - player.current_bet)
    
    def get_min_raise_to(self) -> int:
        """獲取最小加注目標金額"""
        return self.current_bet + self.min_raise
    
    def process_action(self, player: Player, action: str, amount: int = 0) -> bool:
        """
        處理玩家動作
        
        Args:
            player: 執行動作的玩家
            action: 動作類型 (fold, check, call, bet, raise, all_in)
            amount: 動作金額（如適用）
            
        Returns:
            動作是否有效
        """
        action = action.lower()
        
        if action == "fold":
            player.fold()
            self.actions_this_round.append((player, "棄牌", 0))
            return True
        
        if action == "check":
            if self.get_amount_to_call(player) > 0:
                return False  # 有人下注時不能過牌
            player.check()
            self.actions_this_round.append((player, "過牌", 0))
            return True
        
        if action == "call":
            call_amount = self.get_amount_to_call(player)
            if call_amount == 0:
                return False  # 沒有可跟注的金額
            result = player.call(call_amount)
            self.actions_this_round.append((player, "跟注", result.amount))
            return True
        
        if action == "bet":
            if self.current_bet > 0:
                return False  # 已有人下注，應該用 raise
            if amount < self.big_blind:
                amount = self.big_blind
            result = player.bet(amount)
            self.current_bet = player.current_bet
            self.min_raise = amount
            self.last_raiser = player
            self.actions_this_round.append((player, "下注", result.amount))
            return True
        
        if action == "raise":
            min_raise_to = self.get_min_raise_to()
            if amount < min_raise_to and amount < player.chips + player.current_bet:
                amount = min_raise_to
            
            raise_amount = amount - player.current_bet
            if raise_amount > player.chips:
                raise_amount = player.chips
            
            result = player.raise_bet(player.current_bet + raise_amount)
            self.min_raise = result.amount - self.current_bet
            self.current_bet = result.amount
            self.last_raiser = player
            self.actions_this_round.append((player, "加注", result.amount))
            return True
        
        if action == "all_in":
            result = player.all_in()
            if player.current_bet > self.current_bet:
                self.min_raise = max(self.min_raise, player.current_bet - self.current_bet)
                self.current_bet = player.current_bet
                self.last_raiser = player
            self.actions_this_round.append((player, "全押", result.amount))
            return True
        
        return False
    
    def is_round_complete(self) -> bool:
        """
        檢查下注輪是否結束
        
        條件：
        1. 只剩一個活躍玩家
        2. 所有可行動的玩家都已行動，且下注金額相等
        """
        active_players = [p for p in self.players if p.is_active]
        
        if len(active_players) <= 1:
            return True
        
        # 可以行動的玩家（未棄牌且未全押）
        actionable = [p for p in active_players if p.can_act()]
        
        if not actionable:
            return True  # 所有人都全押或棄牌
        
        # 1. 檢查所有可行動玩家的下注額是否等於當前下注額
        for p in actionable:
            if p.current_bet != self.current_bet:
                return False
        
        # 2. 檢查所有可行動玩家是否都有「主動」行動（排除盲注）
        # 貼盲注在 actions_this_round 中，但不算主動行動
        # 除非該玩家隨後又有其他動作（如 Check/Call/Raise）
        voluntary_acted_players = set()
        for player, action_name, _ in self.actions_this_round:
            if action_name not in ["小盲注", "大盲注"]:
                voluntary_acted_players.add(player)
        
        # 所有 actionable 玩家都必須有主動行動
        if not all(p in voluntary_acted_players for p in actionable):
            return False
            
        return True
    
    def get_next_player(self, current_position: int) -> Optional[Player]:
        """獲取下一個行動的玩家"""
        num_players = len(self.players)
        
        for i in range(1, num_players + 1):
            pos = (current_position + i) % num_players
            player = self.players[pos]
            if player.can_act():
                return player
        
        return None


if __name__ == "__main__":
    from .player import HumanPlayer, AIPlayer
    
    # 測試
    players = [
        HumanPlayer("玩家", 1000, 0),
        AIPlayer("AI-1", 1000, 1),
        AIPlayer("AI-2", 1000, 2),
    ]
    
    pot = Pot()
    betting = BettingRound(players)
    
    # 收取盲注
    sb, bb = betting.post_blinds(0, pot)
    print(f"小盲注: ${sb}, 大盲注: ${bb}")
    print(pot)
    
    # 模擬下注
    betting.process_action(players[0], "call")
    pot.add_bet(players[0], betting.current_bet - players[0].current_bet)
    
    print("\n下注後:")
    for p in players:
        print(f"  {p}")
    print(pot)
