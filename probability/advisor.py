"""
Decision Advisor for Texas Hold'em
決策建議系統 - 提供即時教學建議
"""

from enum import Enum, auto
from typing import List, Optional, Tuple
from dataclasses import dataclass
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.card import Card
from probability.calculator import ProbabilityCalculator, OddsResult


class AdviceLevel(Enum):
    """建議等級"""
    STRONG_BET = "strong_bet"       # 強烈建議加注
    BET = "bet"                     # 建議下注/加注
    CALL = "call"                   # 建議跟注
    CHECK_CALL = "check_call"       # 過牌或跟注
    CHECK_FOLD = "check_fold"       # 過牌或棄牌
    FOLD = "fold"                   # 建議棄牌


@dataclass
class Advice:
    """
    決策建議
    
    包含建議動作、理由和教學說明
    """
    level: AdviceLevel
    action: str              # 建議的動作
    reasoning: str           # 決策理由
    teaching_points: List[str]  # 教學要點
    confidence: float        # 信心程度 (0-1)
    
    # 視覺顯示
    emoji: str = ""
    color: str = ""         # 用於UI顯示
    
    def __post_init__(self):
        level_display = {
            AdviceLevel.STRONG_BET: ("🟢", "green", "強烈建議加注"),
            AdviceLevel.BET: ("🟢", "green", "建議下注"),
            AdviceLevel.CALL: ("🟡", "yellow", "建議跟注"),
            AdviceLevel.CHECK_CALL: ("🟡", "yellow", "過牌/跟注"),
            AdviceLevel.CHECK_FOLD: ("🟠", "orange", "謹慎行事"),
            AdviceLevel.FOLD: ("🔴", "red", "建議棄牌"),
        }
        self.emoji, self.color, _ = level_display.get(self.level, ("⚪", "white", ""))
    
    def __str__(self) -> str:
        lines = [
            f"{self.emoji} 建議: {self.action}",
            f"原因: {self.reasoning}",
        ]
        if self.teaching_points:
            lines.append("教學要點:")
            for point in self.teaching_points:
                lines.append(f"  • {point}")
        return '\n'.join(lines)
    
    def to_display_dict(self) -> dict:
        """轉換為顯示用的字典"""
        return {
            "level": self.level.value,
            "action": self.action,
            "reasoning": self.reasoning,
            "teaching_points": self.teaching_points,
            "confidence": self.confidence,
            "emoji": self.emoji,
            "color": self.color
        }


class DecisionAdvisor:
    """
    決策建議器
    
    根據機率分析提供即時建議和教學
    """
    
    def __init__(self):
        self.calculator = ProbabilityCalculator(simulation_count=2000)
    
    def get_advice(self, hole_cards: List[Card], community_cards: List[Card],
                  num_opponents: int, pot: int, call_amount: int,
                  player_chips: int, can_check: bool = False) -> Advice:
        """
        獲取決策建議
        
        Args:
            hole_cards: 玩家手牌
            community_cards: 公共牌
            num_opponents: 活躍對手數
            pot: 底池金額
            call_amount: 需要跟注的金額
            player_chips: 玩家籌碼
            can_check: 是否可以過牌
            
        Returns:
            Advice 決策建議
        """
        # 進行完整分析
        analysis = self.calculator.full_analysis(
            hole_cards, community_cards, num_opponents, pot, call_amount
        )
        
        # 根據分析結果生成建議
        return self._generate_advice(analysis, pot, call_amount, 
                                    player_chips, can_check, num_opponents)
    
    def _generate_advice(self, analysis: OddsResult, pot: int, call_amount: int,
                        player_chips: int, can_check: bool, 
                        num_opponents: int) -> Advice:
        """根據分析生成建議"""
        
        win_rate = analysis.win_rate
        pot_odds = analysis.pot_odds
        ev = analysis.expected_value
        hand_strength = analysis.hand_strength
        outs = analysis.total_outs
        
        teaching_points = []
        
        # 核心教學邏輯：比較勝率和底池賠率
        if call_amount > 0:
            is_profitable = win_rate > pot_odds
            
            # 教學點 1: 解釋勝率和底池賠率
            if is_profitable:
                teaching_points.append(
                    f"你的勝率 ({win_rate:.0%}) > 底池賠率 ({pot_odds:.0%})，這是一個有利的情況！"
                )
            else:
                teaching_points.append(
                    f"你的勝率 ({win_rate:.0%}) < 底池賠率 ({pot_odds:.0%})，跟注長期來說是虧損的。"
                )
        
            # 教學點 2: 解釋期望值
            if ev > 0:
                teaching_points.append(
                    f"期望值 (EV) 是正的 (+${ev:.0f})，表示這個決定長期有利。"
                )
            else:
                teaching_points.append(
                    f"期望值 (EV) 是負的 (${ev:.0f})，表示這個決定長期會虧錢。"
                )
        
        # 教學點 3: 解釋 Outs（如果有聽牌）
        if analysis.outs_list:
            outs_info = analysis.outs_list[0]
            teaching_points.append(
                f"你有 {outs_info.count} 張 outs 可以組成{outs_info.target_hand}，"
                f"成牌機率約 {outs_info.probability:.0%}。"
            )
        
        # 根據情況給出建議
        if call_amount == 0:
            # 可以免費看牌
            return self._advice_for_check_situation(
                analysis, pot, player_chips, num_opponents, teaching_points
            )
        else:
            # 需要跟注
            return self._advice_for_call_situation(
                analysis, pot, call_amount, player_chips, num_opponents, teaching_points
            )
    
    def _advice_for_check_situation(self, analysis: OddsResult, pot: int,
                                   player_chips: int, num_opponents: int,
                                   teaching_points: List[str]) -> Advice:
        """不需要跟注時的建議"""
        
        win_rate = analysis.win_rate
        hand_strength = analysis.hand_strength
        
        if win_rate >= 0.70:
            # 很強的牌，應該價值下注
            bet_size = self._recommend_bet_size(pot, "large")
            teaching_points.append(
                f"你有很強的牌（勝率 {win_rate:.0%}），應該下注獲取價值！"
            )
            teaching_points.append(
                f"「機率有利時要下大注」—— 這是獲利的關鍵！"
            )
            return Advice(
                level=AdviceLevel.STRONG_BET,
                action=f"下注 ${bet_size}",
                reasoning=f"勝率高達 {win_rate:.0%}，這是價值下注的好機會",
                teaching_points=teaching_points,
                confidence=0.9
            )
        
        elif win_rate >= 0.50:
            # 還不錯，可以下注或過牌
            bet_size = self._recommend_bet_size(pot, "medium")
            teaching_points.append(
                f"中等強度的牌，可以下注試探對手，也可以過牌控制底池。"
            )
            return Advice(
                level=AdviceLevel.BET,
                action=f"下注 ${bet_size} 或過牌",
                reasoning=f"勝率 {win_rate:.0%}，適合控制性下注",
                teaching_points=teaching_points,
                confidence=0.6
            )
        
        elif analysis.outs_list:
            # 有聽牌，免費看牌
            teaching_points.append(
                "有潛在成牌機會，過牌是最佳選擇——免費看能否成牌。"
            )
            return Advice(
                level=AdviceLevel.CHECK_CALL,
                action="過牌",
                reasoning=f"聽牌中（{analysis.total_outs} outs），免費看牌最佳",
                teaching_points=teaching_points,
                confidence=0.7
            )
        
        else:
            # 弱牌但可以免費看
            teaching_points.append(
                "雖然牌力不強，但既然可以免費看牌，就繼續看。"
            )
            return Advice(
                level=AdviceLevel.CHECK_CALL,
                action="過牌",
                reasoning="免費看牌，沒理由棄牌",
                teaching_points=teaching_points,
                confidence=0.8
            )
    
    def _advice_for_call_situation(self, analysis: OddsResult, pot: int,
                                  call_amount: int, player_chips: int,
                                  num_opponents: int, 
                                  teaching_points: List[str]) -> Advice:
        """需要跟注時的建議"""
        
        win_rate = analysis.win_rate
        pot_odds = analysis.pot_odds
        ev = analysis.expected_value
        
        # 計算跟注佔籌碼的比例
        call_ratio = call_amount / player_chips if player_chips > 0 else 1
        
        if win_rate >= 0.65 and ev > 0:
            # 非常有利，應該加注
            raise_size = self._recommend_raise_size(pot, call_amount, "large")
            teaching_points.append(
                "「機率對你有利的時候要下大注」—— 現在是最佳時機！"
            )
            return Advice(
                level=AdviceLevel.STRONG_BET,
                action=f"加注到 ${raise_size}",
                reasoning=f"勝率 {win_rate:.0%}，正 EV (+${ev:.0f})，應該加注！",
                teaching_points=teaching_points,
                confidence=0.85
            )
        
        elif win_rate > pot_odds and ev > 0:
            # 有利，跟注
            teaching_points.append(
                f"勝率 > 底池賠率，這是一個「數學上有利」的跟注。"
            )
            return Advice(
                level=AdviceLevel.CALL,
                action=f"跟注 ${call_amount}",
                reasoning=f"勝率 ({win_rate:.0%}) > 底池賠率 ({pot_odds:.0%})，跟注是正確的",
                teaching_points=teaching_points,
                confidence=0.7
            )
        
        elif win_rate <= pot_odds * 0.8:
            # 明顯不利，應該棄牌
            teaching_points.append(
                f"「機率不利的時候要縮小下注或棄牌」—— 這就是減少損失的方法。"
            )
            teaching_points.append(
                f"好的玩家懂得在不利時放棄，保存籌碼等待更好的機會。"
            )
            return Advice(
                level=AdviceLevel.FOLD,
                action="棄牌",
                reasoning=f"勝率 ({win_rate:.0%}) 遠低於底池賠率 ({pot_odds:.0%})，棄牌是正確的",
                teaching_points=teaching_points,
                confidence=0.8
            )
        
        elif analysis.outs_list and analysis.total_outs >= 8:
            # 有強聽牌，可能值得跟注
            combined_odds = sum(o.probability for o in analysis.outs_list[:2])
            if win_rate + combined_odds * 0.7 > pot_odds:
                teaching_points.append(
                    f"雖然當前勝率不高，但加上聽牌機率（{analysis.total_outs} outs），整體仍有利。"
                )
                return Advice(
                    level=AdviceLevel.CALL,
                    action=f"跟注 ${call_amount}",
                    reasoning=f"強聽牌（{analysis.total_outs} outs），隱含賠率值得跟注",
                    teaching_points=teaching_points,
                    confidence=0.55
                )
        
        # 邊緣情況
        if call_ratio > 0.3:
            # 跟注太大
            teaching_points.append(
                f"跟注金額佔你籌碼的 {call_ratio:.0%}，風險太高。"
            )
            return Advice(
                level=AdviceLevel.FOLD,
                action="棄牌",
                reasoning=f"跟注金額過大，不值得冒險",
                teaching_points=teaching_points,
                confidence=0.6
            )
        
        # 小額跟注，邊緣決策
        teaching_points.append(
            "這是一個邊緣情況，跟注和棄牌都可以接受。"
        )
        return Advice(
            level=AdviceLevel.CHECK_FOLD,
            action=f"棄牌或跟注 ${call_amount}",
            reasoning="邊緣決策，根據對手的打法風格決定",
            teaching_points=teaching_points,
            confidence=0.4
        )
    
    def _recommend_bet_size(self, pot: int, size: str) -> int:
        """推薦下注大小"""
        if size == "small":
            return max(int(pot * 0.33), 10)
        elif size == "large":
            return max(int(pot * 0.75), 20)
        else:  # medium
            return max(int(pot * 0.5), 15)
    
    def _recommend_raise_size(self, pot: int, current_bet: int, size: str) -> int:
        """推薦加注大小"""
        base = current_bet + pot
        if size == "small":
            return int(base * 0.5)
        elif size == "large":
            return int(base * 1.0)
        else:  # medium
            return int(base * 0.75)
    
    def analyze_decision(self, hole_cards: List[Card], community_cards: List[Card],
                        action_taken: str, amount: int,
                        num_opponents: int, pot: int, 
                        call_amount: int) -> Tuple[bool, str, List[str]]:
        """
        分析玩家做出的決策是否正確
        
        用於回合結束後的教學回顧
        
        Returns:
            (is_correct, explanation, learning_points)
        """
        analysis = self.calculator.full_analysis(
            hole_cards, community_cards, num_opponents, pot, call_amount
        )
        
        win_rate = analysis.win_rate
        pot_odds = analysis.pot_odds
        ev = analysis.expected_value
        
        learning_points = []
        
        action = action_taken.lower()
        
        if action == "fold":
            if win_rate > pot_odds and ev > 0:
                return False, "你棄掉了一手有利的牌！", [
                    f"你的勝率是 {win_rate:.0%}，高於底池賠率 {pot_odds:.0%}",
                    "當勝率 > 底池賠率時，應該跟注或加注",
                    f"這次棄牌讓你損失了潛在 ${ev:.0f} 的期望值"
                ]
            else:
                return True, "好的棄牌決定！", [
                    f"你的勝率是 {win_rate:.0%}，低於底池賠率 {pot_odds:.0%}",
                    "當機率不利時，棄牌是正確的選擇",
                    "保存籌碼等待更好的機會"
                ]
        
        elif action == "call":
            if win_rate > pot_odds:
                return True, "正確的跟注！", [
                    f"你的勝率 ({win_rate:.0%}) > 底池賠率 ({pot_odds:.0%})",
                    "這是一個有正期望值的決定"
                ]
            else:
                return False, "這個跟注從長期來看是虧損的", [
                    f"你的勝率 ({win_rate:.0%}) < 底池賠率 ({pot_odds:.0%})",
                    "當勝率 < 底池賠率時，跟注會讓你長期虧損",
                    "考慮棄牌或加注 bluff（如果對手可能會棄牌）"
                ]
        
        elif action in ["bet", "raise"]:
            if win_rate >= 0.5:
                return True, "好的價值下注！", [
                    f"你的勝率是 {win_rate:.0%}，適合從弱牌那裡獲取價值",
                    "「機率有利時要下大注」—— 這正是你做的！"
                ]
            elif win_rate < 0.3 and num_opponents <= 2:
                return True, "不錯的詐唬嘗試！", [
                    "對手較少時，詐唬成功率更高",
                    "但要控制詐唬頻率，不要太頻繁"
                ]
            else:
                return False, "這個下注風險較高", [
                    f"你的勝率只有 {win_rate:.0%}",
                    "當牌力不強時，下注可能會被更強的牌跟注"
                ]
        
        elif action == "check":
            if win_rate >= 0.6:
                learning_points.append(
                    f"你的勝率有 {win_rate:.0%}，考慮下注獲取更多價值"
                )
                learning_points.append(
                    "過牌不是錯誤，但可能錯過了賺錢的機會"
                )
                return True, "過牌可以接受，但考慮價值下注", learning_points
            else:
                return True, "好的過牌！", [
                    "免費看牌是聰明的選擇"
                ]
        
        return True, "決策可以接受", learning_points


# 教學信息生成
def generate_teaching_message(analysis: OddsResult, stage: str) -> str:
    """
    生成適合顯示的教學訊息
    """
    lines = []
    
    # 當前狀態
    lines.append(f"📊 當前勝率: {analysis.win_rate:.1%}")
    
    if analysis.pot_odds > 0:
        lines.append(f"📈 底池賠率: {analysis.pot_odds:.1%}")
        
        # 核心比較
        if analysis.win_rate > analysis.pot_odds:
            lines.append("✅ 勝率 > 底池賠率 = 有利情況！")
        else:
            lines.append("⚠️ 勝率 < 底池賠率 = 不利情況")
    
    # Outs 信息
    if analysis.outs_list:
        outs = analysis.outs_list[0]
        lines.append(f"🃏 {outs.target_hand}: {outs.count} outs ({outs.probability:.0%})")
    
    return '\n'.join(lines)


if __name__ == "__main__":
    from game.card import cards_from_string
    
    # 測試建議系統
    advisor = DecisionAdvisor()
    
    # 測試案例
    hole = cards_from_string("Qs Js")
    board = cards_from_string("9s 2s 7h")
    
    print("=" * 60)
    print("測試案例: Q♠ J♠ (同花聽牌)")
    print("公共牌: 9♠ 2♠ 7♥")
    print("=" * 60)
    
    advice = advisor.get_advice(
        hole, board,
        num_opponents=2,
        pot=200,
        call_amount=50,
        player_chips=500,
        can_check=False
    )
    
    print(advice)
    
    print("\n" + "=" * 60)
    print("決策分析（假設玩家跟注）:")
    is_correct, explanation, points = advisor.analyze_decision(
        hole, board, "call", 50, 2, 200, 50
    )
    print(f"正確: {is_correct}")
    print(f"說明: {explanation}")
    for point in points:
        print(f"  • {point}")
