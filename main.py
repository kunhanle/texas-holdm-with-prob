"""
Texas Hold'em Educational Poker Game
德州撲克教學版 - 主程式入口

學習目標:
1. 用機率來輔助決策
2. 機率有利時下大注，不利時縮小下注

使用方法:
    python main.py
"""

import sys
import os
import random
import time

# 確保可以導入同目錄下的模組
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.card import Card, Deck
from game.player import Player, HumanPlayer, AIPlayer
from game.table import Table, GameStage
from game.hand_evaluator import HandEvaluator
from ai.opponent import AIOpponent, AIDifficulty, AIPersonality, create_ai_players
from probability.calculator import ProbabilityCalculator
from probability.advisor import DecisionAdvisor
from ui.console_ui import ConsoleUI, Colors, clear_screen, display_banner


class TexasHoldemGame:
    """
    德州撲克主遊戲類別
    
    管理整個遊戲流程
    """
    
    def __init__(self, num_opponents: int = 3, starting_chips: int = 1000,
                 small_blind: int = 10, big_blind: int = 20,
                 ai_difficulty: AIDifficulty = AIDifficulty.MEDIUM):
        """
        初始化遊戲
        
        Args:
            num_opponents: 電腦對手數量 (3-5)
            starting_chips: 起始籌碼
            small_blind: 小盲注
            big_blind: 大盲注
            ai_difficulty: AI 難度
        """
        # 驗證參數
        num_opponents = max(3, min(5, num_opponents))
        
        # 創建牌桌
        self.table = Table(small_blind, big_blind)
        
        # 創建人類玩家
        self.human_player = HumanPlayer("玩家", starting_chips)
        self.table.add_player(self.human_player)
        
        # 創建 AI 對手
        self.ai_opponents = []
        ai_players = create_ai_players(num_opponents, ai_difficulty, starting_chips)
        for ai_player in ai_players:
            self.table.add_player(ai_player)
            
            # 創建對應的 AI 決策器
            personality = AIPersonality(ai_player.personality)
            ai = AIOpponent(ai_difficulty, personality)
            self.ai_opponents.append((ai_player, ai))
        
        # 創建 UI
        self.ui = ConsoleUI(self.table)
        
        # 機率計算器
        self.calculator = ProbabilityCalculator(simulation_count=1500)
        self.advisor = DecisionAdvisor()
        
        # 遊戲設定
        self.ai_difficulty = ai_difficulty
        self.running = True
    
    def run(self):
        """運行遊戲主循環"""
        self._show_welcome_screen()
        
        while self.running:
            # 檢查是否還能繼續遊戲
            if self.human_player.chips <= 0:
                self._handle_player_bust()
                break
            
            active_players = [p for p in self.table.players if p.chips > 0]
            if len(active_players) < 2:
                self._handle_game_over()
                break
            
            # 開始新局
            self._play_hand()
            
            # 詢問是否繼續
            if not self._ask_continue():
                break
        
        self._show_final_stats()
    
    def _show_welcome_screen(self):
        """顯示歡迎畫面"""
        clear_screen()
        display_banner()
        
        print(f"""
{Colors.WHITE}歡迎來到德州撲克教學版！{Colors.RESET}

這個遊戲的目標不只是贏牌，更重要的是學習：

  {Colors.GREEN}📊 用機率輔助決策{Colors.RESET}
     遊戲會即時顯示你的勝率和成牌機率

  {Colors.YELLOW}💰 掌握下注時機{Colors.RESET}
     機率有利時要大膽下注，不利時要果斷放棄

  {Colors.CYAN}💡 即時教學建議{Colors.RESET}
     每個回合都會提供決策建議和學習要點

{Colors.BOLD}遊戲設定:{Colors.RESET}
  • 對手數量: {len(self.ai_opponents)} 位 AI
  • AI 難度: {self.ai_difficulty.value}
  • 起始籌碼: ${self.human_player.chips}
  • 盲注: ${self.table.small_blind}/${self.table.big_blind}

{Colors.GRAY}按 Enter 開始遊戲...{Colors.RESET}
""")
        input()
    
    def _play_hand(self):
        """進行一局遊戲"""
        # 開始新局
        self.table.start_new_hand()
        
        # 遊戲主循環
        while self.table.stage not in [GameStage.SHOWDOWN, GameStage.FINISHED]:
            current_player = self.table.get_current_player()
            
            if current_player is None:
                # 沒有需要行動的玩家，進入下一階段
                self.table.advance_stage()
                continue
            
            # 顯示遊戲狀態
            self.ui.display_game_state(self.human_player)
            
            if current_player == self.human_player:
                # 人類玩家回合
                action, amount = self.ui.get_player_action(self.human_player)
                self.table.process_player_action(action, amount)
            else:
                # AI 回合
                self._process_ai_turn(current_player)
                time.sleep(0.8)  # 稍微延遲，讓玩家看到 AI 行動
        
        # 處理攤牌
        if self.table.stage == GameStage.SHOWDOWN:
            self._handle_showdown()
        elif self.table.stage == GameStage.FINISHED:
            self._handle_early_finish()
    
    def _process_ai_turn(self, ai_player: Player):
        """處理 AI 回合"""
        # 找到對應的 AI 決策器
        ai = None
        for player, opponent_ai in self.ai_opponents:
            if player == ai_player:
                ai = opponent_ai
                break
        
        if ai is None:
            # 預設動作
            self.table.process_player_action("fold", 0)
            return
        
        # 計算勝率和底池賠率
        num_opponents = len([p for p in self.table.players 
                            if p.is_active and p != ai_player])
        
        if ai_player.hole_cards and num_opponents > 0:
            win_rate, _, _ = self.calculator.calculate_win_rate(
                ai_player.hole_cards,
                self.table.community_cards,
                num_opponents
            )
            
            call_amount = 0
            if self.table.betting_round:
                call_amount = self.table.betting_round.get_amount_to_call(ai_player)
            
            pot_odds = self.calculator.calculate_pot_odds(
                self.table.pot.total, call_amount
            )
        else:
            win_rate = 0.5
            pot_odds = 0.0
        
        # AI 做出決策
        decision = ai.make_decision(ai_player, self.table, win_rate, pot_odds)
        
        # 執行決策
        success = self.table.process_player_action(decision.action, decision.amount)
        
        if not success:
            # 如果決策失敗，嘗試安全動作
            actions = self.table.get_available_actions()
            if actions:
                safe_action, safe_amount = actions[0]  # 通常是 fold
                self.table.process_player_action(safe_action, safe_amount)
    
    def _handle_showdown(self):
        """處理攤牌"""
        # 顯示最終狀態
        self.ui.display_game_state(self.human_player)
        
        # 評估所有活躍玩家的手牌
        active_players = self.table.get_active_players()
        results = []
        
        for player in active_players:
            all_cards = player.hole_cards + self.table.community_cards
            result = HandEvaluator.evaluate(all_cards)
            results.append((player, result))
        
        # 找出贏家
        results.sort(key=lambda x: x[1], reverse=True)
        best_result = results[0][1]
        winners = [player for player, result in results if result == best_result]
        
        # 顯示攤牌結果
        self.ui.display_showdown(winners, results)
        
        # 分配底池
        pot = self.table.pot.total
        share = pot // len(winners)
        for winner in winners:
            winner.win_pot(share)
        
        # 顯示結果
        self.ui.display_hand_result(winners, pot)
    
    def _handle_early_finish(self):
        """處理提前結束（所有人棄牌）"""
        # 找到唯一活躍的玩家
        active_players = self.table.get_active_players()
        
        if len(active_players) == 1:
            winner = active_players[0]
            pot = self.table.pot.total
            winner.win_pot(pot)
            
            self.ui.display_game_state(self.human_player)
            self.ui.display_hand_result([winner], pot)
    
    def _handle_player_bust(self):
        """處理玩家破產"""
        clear_screen()
        display_banner()
        
        print(f"""
{Colors.RED}╔══════════════════════════════════════╗
║             遊戲結束！               ║
║                                      ║
║       你的籌碼已經用完了...          ║
╚══════════════════════════════════════╝{Colors.RESET}

{Colors.YELLOW}別灰心！這是學習的好機會。{Colors.RESET}

回顧一下可能的問題：
  • 是否在不利的情況下跟注太多？
  • 是否在強牌時沒有足夠加注？
  • 是否能辨識對手的行為模式？

{Colors.CYAN}繼續練習，你一定會進步的！{Colors.RESET}
""")
    
    def _handle_game_over(self):
        """處理遊戲結束（贏了所有對手）"""
        clear_screen()
        display_banner()
        
        print(f"""
{Colors.GREEN}╔══════════════════════════════════════╗
║           🎉 恭喜獲勝！🎉            ║
║                                      ║
║     你擊敗了所有電腦對手！           ║
╚══════════════════════════════════════╝{Colors.RESET}

{Colors.YELLOW}你已經掌握了基本的機率概念：{Colors.RESET}

  ✓ 比較勝率與底池賠率
  ✓ 在有利時積極下注
  ✓ 在不利時果斷棄牌

{Colors.CYAN}繼續挑戰更高難度來提升技術！{Colors.RESET}
""")
    
    def _ask_continue(self) -> bool:
        """詢問是否繼續"""
        print(f"\n{Colors.CYAN}繼續下一局？ (y/n): {Colors.RESET}", end="")
        response = input().strip().lower()
        return response != 'n'
    
    def _show_final_stats(self):
        """顯示最終統計"""
        clear_screen()
        display_banner()
        
        print(f"\n{Colors.BOLD}{Colors.CYAN}═══ 遊戲統計 ═══{Colors.RESET}\n")
        
        print(f"  總局數: {self.human_player.hands_played}")
        print(f"  勝利局數: {self.human_player.hands_won}")
        
        if self.human_player.hands_played > 0:
            win_rate = self.human_player.hands_won / self.human_player.hands_played
            print(f"  勝率: {win_rate:.1%}")
        
        print(f"\n  最終籌碼: ${self.human_player.chips}")
        profit = self.human_player.chips - 1000
        profit_color = Colors.GREEN if profit >= 0 else Colors.RED
        profit_sign = "+" if profit >= 0 else ""
        print(f"  淨收益: {profit_color}{profit_sign}${profit}{Colors.RESET}")
        
        print(f"\n{Colors.GRAY}感謝遊玩！希望你學到了有用的撲克機率概念。{Colors.RESET}\n")


def main():
    """主程式入口"""
    
    # 遊戲設定
    clear_screen()
    display_banner()
    
    print(f"\n{Colors.BOLD}遊戲設定{Colors.RESET}\n")
    
    # 選擇對手數量
    print(f"{Colors.CYAN}選擇對手數量 (3-5):{Colors.RESET} ", end="")
    try:
        num_opponents = int(input().strip())
        num_opponents = max(3, min(5, num_opponents))
    except ValueError:
        num_opponents = 3
    
    # 選擇難度
    print(f"\n{Colors.CYAN}選擇 AI 難度:{Colors.RESET}")
    print("  [1] 初級 (隨機決策，適合新手)")
    print("  [2] 中級 (基於牌力，有一定策略)")
    print("  [3] 高級 (考慮機率和對手，具挑戰性)")
    print(f"\n{Colors.CYAN}選擇 (1-3):{Colors.RESET} ", end="")
    
    try:
        diff_choice = int(input().strip())
        difficulty_map = {1: AIDifficulty.EASY, 2: AIDifficulty.MEDIUM, 3: AIDifficulty.HARD}
        difficulty = difficulty_map.get(diff_choice, AIDifficulty.MEDIUM)
    except ValueError:
        difficulty = AIDifficulty.MEDIUM
    
    # 創建並運行遊戲
    game = TexasHoldemGame(
        num_opponents=num_opponents,
        starting_chips=1000,
        small_blind=10,
        big_blind=20,
        ai_difficulty=difficulty
    )
    
    game.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}遊戲已中斷。感謝遊玩！{Colors.RESET}\n")
        sys.exit(0)
