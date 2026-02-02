"""
Table class for Texas Hold'em
牌桌與遊戲流程管理
"""

from enum import Enum, auto
from typing import List, Optional, Dict, Tuple, Callable
from dataclasses import dataclass
import time

from .card import Card, Deck
from .player import Player, HumanPlayer, AIPlayer, PlayerAction
from .hand_evaluator import HandEvaluator, HandResult
from .betting import Pot, BettingRound


class GameStage(Enum):
    """遊戲階段"""
    WAITING = auto()      # 等待開始
    PRE_FLOP = auto()     # 翻牌前
    FLOP = auto()         # 翻牌（3張公共牌）
    TURN = auto()        # 轉牌（第4張）
    RIVER = auto()        # 河牌（第5張）
    SHOWDOWN = auto()     # 攤牌
    FINISHED = auto()     # 本局結束


@dataclass
class HandHistory:
    """一局遊戲的記錄"""
    hand_number: int
    players: List[str]
    community_cards: List[Card]
    winner: str
    pot_amount: int
    actions: List[Tuple[str, str, int]]
    
    def __str__(self) -> str:
        community = ' '.join(c.display for c in self.community_cards)
        return f"Hand #{self.hand_number}: {self.winner} 贏得 ${self.pot_amount} ({community})"


class Table:
    """
    德州撲克牌桌
    
    管理遊戲流程、玩家、底池和公共牌
    """
    
    def __init__(self, small_blind: int = 10, big_blind: int = 20):
        self.players: List[Player] = []
        self.deck: Deck = Deck()
        self.community_cards: List[Card] = []
        self.pot: Pot = Pot()
        
        self.small_blind = small_blind
        self.big_blind = big_blind
        
        self.dealer_position: int = 0
        self.current_player_index: int = 0
        self.stage: GameStage = GameStage.WAITING
        
        self.betting_round: Optional[BettingRound] = None
        self.hand_number: int = 0
        self.history: List[HandHistory] = []
        
        # 回調函數（用於UI通知）
        self.on_stage_change: Optional[Callable[[GameStage], None]] = None
        self.on_player_action: Optional[Callable[[Player, str, int], None]] = None
        self.on_cards_dealt: Optional[Callable[[str, List[Card]], None]] = None
    
    def add_player(self, player: Player) -> bool:
        """添加玩家到牌桌"""
        if len(self.players) >= 9:
            return False
        player.position = len(self.players)
        self.players.append(player)
        return True
    
    def remove_player(self, player: Player) -> bool:
        """移除玩家"""
        if player in self.players:
            self.players.remove(player)
            # 重新分配位置
            for i, p in enumerate(self.players):
                p.position = i
            return True
        return False
    
    def get_active_players(self) -> List[Player]:
        """獲取活躍玩家（未棄牌）"""
        return [p for p in self.players if p.is_active]
    
    def get_actionable_players(self) -> List[Player]:
        """獲取可行動的玩家（未棄牌且未全押）"""
        return [p for p in self.players if p.can_act()]
    
    def start_new_hand(self) -> None:
        """開始新的一局"""
        self.hand_number += 1
        
        # 重置牌組和公共牌
        self.deck.reset()
        self.deck.shuffle()
        self.community_cards = []
        
        # 重置底池
        self.pot.reset()
        
        # 重置所有玩家狀態
        for player in self.players:
            player.reset_for_new_hand()
            player.hands_played += 1
        
        # 移除沒有籌碼的玩家
        self.players = [p for p in self.players if p.chips > 0]
        
        if len(self.players) < 2:
            self.stage = GameStage.FINISHED
            return
        
        # 創建下注輪
        self.betting_round = BettingRound(self.players, self.small_blind, self.big_blind)
        
        # 收取盲注
        self.betting_round.post_blinds(self.dealer_position, self.pot)
        
        # 發手牌
        self._deal_hole_cards()
        
        # 設置階段
        self.stage = GameStage.PRE_FLOP
        if self.on_stage_change:
            self.on_stage_change(self.stage)
        
        # 設置第一個行動者（大盲注後面的玩家）
        self.current_player_index = (self.dealer_position + 3) % len(self.players)
    
    def _deal_hole_cards(self) -> None:
        """發手牌給所有玩家"""
        for player in self.players:
            cards = self.deck.deal_multiple(2)
            player.receive_cards(cards)
            if self.on_cards_dealt:
                self.on_cards_dealt("hole", cards)
    
    def _deal_community_cards(self, count: int) -> List[Card]:
        """發公共牌"""
        # 燒一張牌
        self.deck.deal()
        # 發公共牌
        cards = self.deck.deal_multiple(count)
        self.community_cards.extend(cards)
        if self.on_cards_dealt:
            self.on_cards_dealt("community", cards)
        return cards
    
    def advance_stage(self) -> None:
        """進入下一階段"""
        active = self.get_active_players()
        
        # 只剩一個玩家，直接結束
        if len(active) <= 1:
            self._end_hand()
            return
        
        # 重置下注輪
        if self.betting_round:
            self.betting_round.reset_for_new_round()
        
        if self.stage == GameStage.PRE_FLOP:
            self.stage = GameStage.FLOP
            self._deal_community_cards(3)
        elif self.stage == GameStage.FLOP:
            self.stage = GameStage.TURN
            self._deal_community_cards(1)
        elif self.stage == GameStage.TURN:
            self.stage = GameStage.RIVER
            self._deal_community_cards(1)
        elif self.stage == GameStage.RIVER:
            self.stage = GameStage.SHOWDOWN
            self._showdown()
            return
        
        if self.on_stage_change:
            self.on_stage_change(self.stage)
        
        # 設置下一個行動者（莊家後面的第一個活躍玩家）
        self.current_player_index = self._find_next_active_player(self.dealer_position)
    
    def _find_next_active_player(self, from_position: int) -> int:
        """找到下一個可行動的玩家位置"""
        num_players = len(self.players)
        for i in range(1, num_players + 1):
            pos = (from_position + i) % num_players
            if self.players[pos].can_act():
                return pos
        return from_position
    
    def get_current_player(self) -> Optional[Player]:
        """獲取當前行動的玩家"""
        if self.stage in [GameStage.WAITING, GameStage.SHOWDOWN, GameStage.FINISHED]:
            return None
        if 0 <= self.current_player_index < len(self.players):
            player = self.players[self.current_player_index]
            if player.can_act():
                return player
        return None
    
    def process_player_action(self, action: str, amount: int = 0) -> bool:
        """
        處理當前玩家的動作
        
        Args:
            action: 動作類型
            amount: 金額（如適用）
            
        Returns:
            動作是否成功
        """
        player = self.get_current_player()
        if not player or not self.betting_round:
            return False
        
        # 記錄下注前的籌碼
        old_bet = player.current_bet
        
        # 處理動作
        success = self.betting_round.process_action(player, action, amount)
        
        if success:
            # 記錄動作
            player.last_action = action
            player.last_action_amount = amount

            # 更新底池
            bet_diff = player.current_bet - old_bet
            if bet_diff > 0:
                self.pot.add_bet(player, bet_diff)
            
            if self.on_player_action:
                self.on_player_action(player, action, amount)
            
            # 移動到下一個玩家
            self._advance_to_next_player()
        
        return success
    
    def _advance_to_next_player(self) -> None:
        """移動到下一個行動的玩家"""
        if not self.betting_round:
            return
        
        # 檢查下注輪是否結束
        if self.betting_round.is_round_complete():
            self.advance_stage()
            return
        
        # 找下一個可行動的玩家
        self.current_player_index = self._find_next_active_player(self.current_player_index)
        
    def process_ai_turn(self) -> bool:
        """
        處理 AI 玩家的回合
        
        Returns:
            bool: AI 是否執行了動作
        """
        # 避免循環導入，局部導入
        from ai.opponent import AIOpponent, AIDifficulty, AIPersonality
        from game.player import AIPlayer
        
        player = self.get_current_player()
        if not player or player.is_human:
            return False
            
        # 簡單的一步到位 AI 邏輯
        if not hasattr(self, 'ai_logic_cache'):
            self.ai_logic_cache = {}
            
        if player.name not in self.ai_logic_cache:
            # 默認難度
            try:
                diff = AIDifficulty(getattr(player, 'difficulty', 'medium'))
                pers = AIPersonality(getattr(player, 'personality', 'balanced'))
            except:
                diff = AIDifficulty.MEDIUM
                pers = AIPersonality.BALANCED
            self.ai_logic_cache[player.name] = AIOpponent(diff, pers)
            
        ai = self.ai_logic_cache[player.name]
        
        # 簡單估算勝率
        win_rate = 0.5 
        if player.hole_cards and len(player.hole_cards) == 2:
            if player.hole_cards[0].rank == player.hole_cards[1].rank:
                win_rate = 0.7
                
        decision = ai.make_decision(player, self, win_rate)
        
        print(f"AI {player.name} decides: {decision.action} {decision.amount}")
        return self.process_player_action(decision.action, decision.amount)
    
    def _showdown(self) -> None:
        """攤牌階段"""
        active_players = self.get_active_players()
        
        if len(active_players) == 1:
            # 只剩一人，直接獲勝
            winner = active_players[0]
            winner.win_pot(self.pot.total)
            self._record_hand([winner])
            self._end_hand()
            return
        
        # 評估所有玩家的手牌
        results: List[Tuple[Player, HandResult]] = []
        for player in active_players:
            all_cards = player.hole_cards + self.community_cards
            result = HandEvaluator.evaluate(all_cards)
            results.append((player, result))
        
        # 找出最強的手牌
        results.sort(key=lambda x: x[1], reverse=True)
        best_result = results[0][1]
        
        # 找出所有贏家（可能平局）
        winners = [player for player, result in results if result == best_result]
        
        # 計算邊池並分配
        self.pot.calculate_side_pots(active_players)
        payouts = self.pot.distribute_to_winners(winners)
        
        for winner, amount in payouts.items():
            winner.win_pot(amount)
        
        self._record_hand(winners)
        self._end_hand()
    
    def _end_hand(self) -> None:
        """結束本局"""
        self.stage = GameStage.FINISHED
        
        # 移動莊家位置
        self.dealer_position = (self.dealer_position + 1) % len(self.players)
        
        if self.on_stage_change:
            self.on_stage_change(self.stage)
    
    def _record_hand(self, winners: List[Player]) -> None:
        """記錄本局歷史"""
        if self.betting_round:
            history = HandHistory(
                hand_number=self.hand_number,
                players=[p.name for p in self.players],
                community_cards=self.community_cards.copy(),
                winner=', '.join(w.name for w in winners),
                pot_amount=self.pot.total,
                actions=self.betting_round.actions_this_round.copy()
            )
            self.history.append(history)
    
    def get_game_state(self) -> Dict:
        """
        獲取當前遊戲狀態（用於UI顯示和AI決策）
        """
        # 計算當前輪的下注總額（避免UI重複顯示）
        current_bets_sum = sum(p.current_bet for p in self.players)
        display_pot = max(0, self.pot.total - current_bets_sum)

        return {
            "stage": self.stage.name,
            "community_cards": [c.display for c in self.community_cards],
            "pot": display_pot,
            "current_bet": self.betting_round.current_bet if self.betting_round else 0,
            "players": [
                {
                    "name": p.name,
                    "chips": p.chips,
                    "current_bet": p.current_bet,
                    "is_active": p.is_active,
                    "is_all_in": p.is_all_in,
                    "is_current": p == self.get_current_player(),
                    "last_action": p.last_action if hasattr(p, 'last_action') else None
                }
                for p in self.players
            ],
            "dealer_position": self.dealer_position
        }
    
    def get_available_actions(self) -> List[Tuple[str, int]]:
        """
        獲取當前玩家可用的動作
        
        Returns:
            列表 of (動作名, 相關金額)
        """
        player = self.get_current_player()
        if not player or not self.betting_round:
            return []
        
        actions = []
        amount_to_call = self.betting_round.get_amount_to_call(player)
        min_raise = self.betting_round.get_min_raise_to()
        
        actions.append(("fold", 0))
        
        if amount_to_call == 0:
            actions.append(("check", 0))
            actions.append(("bet", self.big_blind))
        else:
            actions.append(("call", amount_to_call))
            if player.chips > amount_to_call:
                actions.append(("raise", min_raise))
        
        if player.chips > 0:
            actions.append(("all_in", player.chips))
        
        return actions
    
    def __str__(self) -> str:
        community = ' '.join(c.display for c in self.community_cards) or "無"
        return f"""
牌桌狀態: {self.stage.name}
公共牌: {community}
底池: ${self.pot.total}
莊家位置: {self.dealer_position}
玩家:
""" + '\n'.join(f"  {p}" for p in self.players)


if __name__ == "__main__":
    from .player import HumanPlayer, AIPlayer
    
    # 創建牌桌
    table = Table(small_blind=10, big_blind=20)
    
    # 添加玩家
    table.add_player(HumanPlayer("玩家", 1000))
    table.add_player(AIPlayer("AI-1", 1000))
    table.add_player(AIPlayer("AI-2", 1000))
    table.add_player(AIPlayer("AI-3", 1000))
    
    # 開始新局
    table.start_new_hand()
    print(table)
    
    # 顯示可用動作
    print("\n可用動作:")
    for action, amount in table.get_available_actions():
        print(f"  {action}: ${amount}")

