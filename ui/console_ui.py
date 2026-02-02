"""
Console UI for Texas Hold'em
命令行介面
"""

import os
import sys
import time
from typing import List, Optional, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.card import Card
from game.player import Player
from game.table import Table, GameStage
from game.hand_evaluator import HandEvaluator
from probability.calculator import ProbabilityCalculator, OddsResult
from probability.advisor import DecisionAdvisor, Advice


# ANSI 顏色碼
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"
    
    # 背景色
    BG_GREEN = "\033[42m"
    BG_RED = "\033[41m"


def clear_screen():
    """清除螢幕"""
    os.system('cls' if os.name == 'nt' else 'clear')


def display_banner():
    """顯示遊戲標題"""
    banner = f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   {Colors.WHITE}♠ ♥ ♦ ♣{Colors.CYAN}    {Colors.BOLD}{Colors.WHITE}德州撲克教學版 Texas Hold'em{Colors.RESET}{Colors.CYAN}    {Colors.WHITE}♣ ♦ ♥ ♠{Colors.CYAN}   ║
║                                                                          ║
║   {Colors.YELLOW}學習用機率做決策 | 掌握下注時機 | 成為撲克高手{Colors.CYAN}                    ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝{Colors.RESET}
"""
    print(banner)


def display_card(card: Card, hidden: bool = False) -> str:
    """
    格式化顯示單張牌
    
    Args:
        card: 牌
        hidden: 是否隱藏（顯示背面）
    """
    if hidden:
        return f"{Colors.GRAY}[??]{Colors.RESET}"
    
    suit_colors = {
        "♠": Colors.WHITE,
        "♣": Colors.WHITE,
        "♥": Colors.RED,
        "♦": Colors.RED,
    }
    
    suit_sym = card.suit.symbol
    color = suit_colors.get(suit_sym, Colors.WHITE)
    
    return f"{color}[{card.rank.symbol}{suit_sym}]{Colors.RESET}"


def display_cards(cards: List[Card], hidden: bool = False) -> str:
    """格式化顯示多張牌"""
    return ' '.join(display_card(c, hidden) for c in cards)


class ConsoleUI:
    """
    控制台介面
    
    管理遊戲畫面顯示和使用者輸入
    """
    
    def __init__(self, table: Table):
        self.table = table
        self.calculator = ProbabilityCalculator(simulation_count=2000)
        self.advisor = DecisionAdvisor()
        self.show_probability = True  # 是否顯示機率資訊
        self.show_advice = True       # 是否顯示建議
    
    def display_game_state(self, human_player: Player):
        """顯示完整遊戲狀態"""
        clear_screen()
        display_banner()
        
        print(f"\n{Colors.BOLD}═══ 第 {self.table.hand_number} 局 ═══{Colors.RESET}")
        print(f"{Colors.GRAY}階段: {self._get_stage_name()}{Colors.RESET}")
        
        # 顯示公共牌
        self._display_community_cards()
        
        # 顯示底池
        print(f"\n{Colors.YELLOW}💰 底池: ${self.table.pot.total}{Colors.RESET}")
        
        # 分隔線
        print(f"\n{Colors.GRAY}{'─' * 60}{Colors.RESET}")
        
        # 顯示所有玩家
        self._display_players(human_player)
        
        # 分隔線
        print(f"\n{Colors.GRAY}{'─' * 60}{Colors.RESET}")
        
        # 顯示人類玩家的詳細資訊
        self._display_human_player_section(human_player)
        
        # 顯示機率和建議
        if self.show_probability and human_player.hole_cards:
            self._display_probability_section(human_player)
    
    def _get_stage_name(self) -> str:
        """獲取階段中文名稱"""
        stage_names = {
            GameStage.WAITING: "等待中",
            GameStage.PRE_FLOP: "翻牌前 (Pre-Flop)",
            GameStage.FLOP: "翻牌 (Flop)",
            GameStage.TURN: "轉牌 (Turn)",
            GameStage.RIVER: "河牌 (River)",
            GameStage.SHOWDOWN: "攤牌 (Showdown)",
            GameStage.FINISHED: "已結束",
        }
        return stage_names.get(self.table.stage, str(self.table.stage))
    
    def _display_community_cards(self):
        """顯示公共牌"""
        print(f"\n{Colors.BOLD}公共牌:{Colors.RESET}")
        
        if not self.table.community_cards:
            placeholders = f"{Colors.GRAY}[ ? ] [ ? ] [ ? ] [ ? ] [ ? ]{Colors.RESET}"
            print(f"  {placeholders}")
        else:
            cards = display_cards(self.table.community_cards)
            # 補上未發的牌位
            remaining = 5 - len(self.table.community_cards)
            placeholders = f"{Colors.GRAY}[ ? ]{Colors.RESET} " * remaining
            print(f"  {cards} {placeholders}")
    
    def _display_players(self, human_player: Player):
        """顯示所有玩家資訊"""
        print(f"\n{Colors.BOLD}玩家:{Colors.RESET}")
        
        for i, player in enumerate(self.table.players):
            # 莊家標記
            dealer_mark = f"{Colors.YELLOW}[D]{Colors.RESET}" if i == self.table.dealer_position else "   "
            
            # 當前行動者標記
            current_mark = f"{Colors.GREEN}→{Colors.RESET}" if player == self.table.get_current_player() else " "
            
            # 狀態
            if not player.is_active:
                status = f"{Colors.GRAY}(已棄牌){Colors.RESET}"
            elif player.is_all_in:
                status = f"{Colors.RED}(All-in){Colors.RESET}"
            else:
                status = ""
            
            # 下注信息
            bet_info = f"下注: ${player.current_bet}" if player.current_bet > 0 else ""
            
            # 手牌（只有AI玩家隱藏，除非是攤牌階段）
            if player == human_player:
                cards_str = display_cards(player.hole_cards) if player.hole_cards else ""
            elif self.table.stage == GameStage.SHOWDOWN and player.is_active:
                cards_str = display_cards(player.hole_cards) if player.hole_cards else ""
            else:
                cards_str = display_cards(player.hole_cards, hidden=True) if player.hole_cards else ""
            
            # 組合顯示
            player_type = "👤" if player.is_human else "🤖"
            print(f"  {current_mark} {dealer_mark} {player_type} {player.name:<10} "
                  f"${player.chips:>6} {bet_info:<15} {cards_str} {status}")
    
    def _display_human_player_section(self, human_player: Player):
        """顯示人類玩家詳細區塊"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}═══ 你的手牌 ═══{Colors.RESET}")
        
        if human_player.hole_cards:
            cards_display = display_cards(human_player.hole_cards)
            print(f"  {cards_display}")
            
            # 評估當前手牌
            if self.table.community_cards:
                all_cards = human_player.hole_cards + self.table.community_cards
                result = HandEvaluator.evaluate(all_cards)
                print(f"\n  {Colors.YELLOW}當前牌型: {result.rank.chinese_name}{Colors.RESET}")
                print(f"  最佳組合: {display_cards(result.best_five)}")
        else:
            print(f"  {Colors.GRAY}尚未發牌{Colors.RESET}")
    
    def _display_probability_section(self, human_player: Player):
        """顯示機率分析區塊"""
        if not human_player.hole_cards:
            return
        
        num_opponents = len([p for p in self.table.players 
                            if p.is_active and p != human_player])
        
        if num_opponents == 0:
            return
        
        print(f"\n{Colors.BOLD}{Colors.MAGENTA}═══ 📊 機率分析 ═══{Colors.RESET}")
        
        # 計算分析結果
        call_amount = 0
        if self.table.betting_round:
            call_amount = self.table.betting_round.get_amount_to_call(human_player)
        
        analysis = self.calculator.full_analysis(
            human_player.hole_cards,
            self.table.community_cards,
            num_opponents,
            self.table.pot.total,
            call_amount
        )
        
        # 勝率
        win_color = Colors.GREEN if analysis.win_rate > 0.5 else Colors.YELLOW if analysis.win_rate > 0.3 else Colors.RED
        print(f"  {Colors.WHITE}勝率:{Colors.RESET} {win_color}{analysis.win_rate:.1%}{Colors.RESET}")
        
        # Outs
        if analysis.outs_list:
            print(f"  {Colors.WHITE}聽牌:{Colors.RESET}")
            for outs in analysis.outs_list[:3]:
                print(f"    • {outs.target_hand}: {Colors.CYAN}{outs.count} outs{Colors.RESET} ({outs.probability:.0%})")
        
        # 底池賠率
        if call_amount > 0:
            print(f"  {Colors.WHITE}底池賠率:{Colors.RESET} {analysis.pot_odds:.1%}")
            
            # EV
            ev_color = Colors.GREEN if analysis.expected_value > 0 else Colors.RED
            ev_sign = "+" if analysis.expected_value > 0 else ""
            print(f"  {Colors.WHITE}期望值 (EV):{Colors.RESET} {ev_color}{ev_sign}${analysis.expected_value:.0f}{Colors.RESET}")
        
        # 建議
        if self.show_advice:
            self._display_advice_section(human_player, call_amount, num_opponents)
    
    def _display_advice_section(self, human_player: Player, call_amount: int, 
                               num_opponents: int):
        """顯示建議區塊"""
        can_check = call_amount == 0
        
        advice = self.advisor.get_advice(
            human_player.hole_cards,
            self.table.community_cards,
            num_opponents,
            self.table.pot.total,
            call_amount,
            human_player.chips,
            can_check
        )
        
        print(f"\n{Colors.BOLD}{Colors.YELLOW}═══ 💡 教學建議 ═══{Colors.RESET}")
        print(f"  {advice.emoji} {Colors.BOLD}{advice.action}{Colors.RESET}")
        print(f"  {Colors.GRAY}{advice.reasoning}{Colors.RESET}")
        
        if advice.teaching_points:
            print(f"\n  {Colors.CYAN}學習重點:{Colors.RESET}")
            for point in advice.teaching_points[:2]:
                print(f"    • {point}")
    
    def get_player_action(self, human_player: Player) -> Tuple[str, int]:
        """
        獲取玩家輸入的動作
        
        Returns:
            (action, amount)
        """
        actions = self.table.get_available_actions()
        
        print(f"\n{Colors.BOLD}═══ 你的回合 ═══{Colors.RESET}")
        print(f"{Colors.GRAY}可用籌碼: ${human_player.chips}{Colors.RESET}\n")
        
        # 顯示選項
        for i, (action, amount) in enumerate(actions, 1):
            action_display = self._format_action(action, amount)
            print(f"  [{i}] {action_display}")
        
        print(f"\n  [0] 查看幫助")
        
        while True:
            try:
                choice = input(f"\n{Colors.CYAN}請選擇動作 (輸入數字): {Colors.RESET}").strip()
                
                if choice == "0":
                    self._show_help()
                    continue
                
                choice_num = int(choice)
                if 1 <= choice_num <= len(actions):
                    action, amount = actions[choice_num - 1]
                    
                    # 如果是加注或下注，詢問金額
                    if action in ["raise", "bet"]:
                        amount = self._get_bet_amount(human_player, action, amount)
                    
                    return action, amount
                else:
                    print(f"{Colors.RED}無效選擇，請重試{Colors.RESET}")
            
            except ValueError:
                print(f"{Colors.RED}請輸入有效數字{Colors.RESET}")
    
    def _format_action(self, action: str, amount: int) -> str:
        """格式化動作顯示"""
        action_names = {
            "fold": f"{Colors.RED}棄牌{Colors.RESET}",
            "check": f"{Colors.GREEN}過牌{Colors.RESET}",
            "call": f"{Colors.YELLOW}跟注 ${amount}{Colors.RESET}",
            "bet": f"{Colors.CYAN}下注{Colors.RESET}",
            "raise": f"{Colors.MAGENTA}加注{Colors.RESET}",
            "all_in": f"{Colors.RED}{Colors.BOLD}全押 ${amount}{Colors.RESET}",
        }
        return action_names.get(action, action)
    
    def _get_bet_amount(self, player: Player, action: str, min_amount: int) -> int:
        """獲取下注金額"""
        max_amount = player.chips + player.current_bet
        
        print(f"\n{Colors.CYAN}請輸入金額 (最小 ${min_amount}, 最大 ${max_amount}):{Colors.RESET}")
        
        while True:
            try:
                amount_str = input(f"{Colors.CYAN}金額: ${Colors.RESET}").strip()
                amount = int(amount_str)
                
                if amount < min_amount:
                    print(f"{Colors.YELLOW}金額必須至少為 ${min_amount}{Colors.RESET}")
                elif amount > max_amount:
                    print(f"{Colors.YELLOW}金額不能超過 ${max_amount}{Colors.RESET}")
                else:
                    return amount
            
            except ValueError:
                print(f"{Colors.RED}請輸入有效數字{Colors.RESET}")
    
    def _show_help(self):
        """顯示幫助說明"""
        help_text = f"""
{Colors.BOLD}{Colors.CYAN}═══ 德州撲克教學說明 ═══{Colors.RESET}

{Colors.BOLD}基本規則:{Colors.RESET}
  • 每人發 2 張手牌（只有你能看到）
  • 公共牌最多 5 張（所有人共用）
  • 用你的 2 張 + 公共 5 張，組成最佳的 5 張牌

{Colors.BOLD}牌型大小（由大到小）:{Colors.RESET}
  1. 皇家同花順 (A-K-Q-J-10 同花色)
  2. 同花順
  3. 四條
  4. 葫蘆 (三條 + 一對)
  5. 同花 (5張同花色)
  6. 順子 (5張連續)
  7. 三條
  8. 兩對
  9. 一對
  10. 高牌

{Colors.BOLD}機率概念:{Colors.RESET}
  • {Colors.YELLOW}勝率{Colors.RESET}: 你贏得這局的機率
  • {Colors.YELLOW}底池賠率{Colors.RESET}: 跟注金額 ÷ (底池 + 跟注金額)
  • {Colors.YELLOW}Outs{Colors.RESET}: 能改善你手牌的剩餘牌數
  • {Colors.YELLOW}期望值 (EV){Colors.RESET}: 長期來看這個決定的平均收益

{Colors.BOLD}核心策略:{Colors.RESET}
  {Colors.GREEN}✓ 勝率 > 底池賠率 → 跟注或加注{Colors.RESET}
  {Colors.RED}✗ 勝率 < 底池賠率 → 考慮棄牌{Colors.RESET}

{Colors.GRAY}按 Enter 繼續...{Colors.RESET}
"""
        print(help_text)
        input()
    
    def display_showdown(self, winners: List[Player], results: List[Tuple[Player, any]]):
        """顯示攤牌結果"""
        print(f"\n{Colors.BOLD}{Colors.YELLOW}═══ 攤牌結果 ═══{Colors.RESET}\n")
        
        for player, hand_result in results:
            if not player.is_active:
                continue
            
            cards = display_cards(player.hole_cards)
            status = f"{Colors.GREEN}★ 贏家!{Colors.RESET}" if player in winners else ""
            
            print(f"  {player.name}: {cards}")
            print(f"    牌型: {hand_result.rank.chinese_name} {status}")
            print()
    
    def display_hand_result(self, winners: List[Player], pot: int):
        """顯示本局結果"""
        print(f"\n{Colors.BOLD}{Colors.GREEN}═══ 本局結束 ═══{Colors.RESET}")
        
        if len(winners) == 1:
            winner = winners[0]
            print(f"\n  🎉 {Colors.GREEN}{Colors.BOLD}{winner.name}{Colors.RESET} 贏得 ${pot}!")
        else:
            names = ', '.join(w.name for w in winners)
            share = pot // len(winners)
            print(f"\n  🤝 平局! {names} 各得 ${share}")
        
        print(f"\n{Colors.GRAY}按 Enter 繼續下一局...{Colors.RESET}")
        input()
    
    def display_post_hand_analysis(self, human_player: Player, 
                                   actions_taken: List[Tuple[str, int]]):
        """顯示局後分析（教學功能）"""
        if not actions_taken:
            return
        
        print(f"\n{Colors.BOLD}{Colors.MAGENTA}═══ 📚 本局回顧 ═══{Colors.RESET}")
        
        # 這裡可以加入更詳細的局後分析
        print(f"\n{Colors.GRAY}本局你做了 {len(actions_taken)} 個決策。{Colors.RESET}")
        print(f"{Colors.GRAY}繼續練習，你會越來越進步！{Colors.RESET}\n")
    
    def display_game_stats(self, human_player: Player):
        """顯示遊戲統計"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}═══ 遊戲統計 ═══{Colors.RESET}")
        
        print(f"\n  總局數: {human_player.hands_played}")
        print(f"  勝局數: {human_player.hands_won}")
        print(f"  勝率: {human_player.win_rate:.1%}")
        print(f"  淨收益: ${human_player.total_winnings - (human_player.hands_played * 30)}")  # 假設平均每局付30盲注
        
        if human_player.total_decisions > 0:
            print(f"\n  決策正確率: {human_player.decision_accuracy:.1%}")


# 測試代碼
if __name__ == "__main__":
    from game.table import Table
    from game.player import HumanPlayer, AIPlayer
    
    # 創建牌桌
    table = Table(small_blind=10, big_blind=20)
    
    # 添加玩家
    human = HumanPlayer("玩家", 1000)
    table.add_player(human)
    table.add_player(AIPlayer("AI-1", 1000))
    table.add_player(AIPlayer("AI-2", 1000))
    
    # 創建 UI
    ui = ConsoleUI(table)
    
    # 開始遊戲
    table.start_new_hand()
    
    # 顯示狀態
    ui.display_game_state(human)
