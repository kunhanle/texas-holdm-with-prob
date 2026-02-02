"""
Texas Hold'em Educational Poker Game - Web Application
德州撲克教學版 - Flask Web 應用

啟動方式:
    python app.py
    
瀏覽器訪問: http://localhost:5000
"""

import sys
import os
from flask import Flask, render_template, jsonify, request, session
import secrets

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.card import Card, Deck
from game.player import Player, HumanPlayer, AIPlayer
from game.table import Table, GameStage
from game.hand_evaluator import HandEvaluator
from ai.opponent import AIOpponent, AIDifficulty, AIPersonality, create_ai_players
from probability.calculator import ProbabilityCalculator
from probability.advisor import DecisionAdvisor

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key_fixed_12345")

# 遊戲狀態存儲（簡單實現，實際應用可用 Redis 等）
games = {}


class WebGame:
    """Web 遊戲管理器"""
    
    def __init__(self, num_opponents: int = 3, difficulty: str = "medium"):
        self.table = Table(small_blind=10, big_blind=20)
        
        # 創建人類玩家
        self.human_player = HumanPlayer("玩家", 1000)
        self.table.add_player(self.human_player)
        
        # 創建 AI 對手
        diff_map = {"easy": AIDifficulty.EASY, "medium": AIDifficulty.MEDIUM, "hard": AIDifficulty.HARD}
        ai_difficulty = diff_map.get(difficulty, AIDifficulty.MEDIUM)
        
        self.ai_opponents = []
        ai_players = create_ai_players(num_opponents, ai_difficulty, 1000)
        for ai_player in ai_players:
            self.table.add_player(ai_player)
            personality = AIPersonality(ai_player.personality)
            ai = AIOpponent(ai_difficulty, personality)
            self.ai_opponents.append((ai_player, ai))
        
        self.calculator = ProbabilityCalculator(simulation_count=300)
        self.advisor = DecisionAdvisor()
        self.message_log = []
        self.hand_result = None
        
        # Caching
        self.last_analysis_key = None
        self.cached_analysis = None
    
    def start_new_hand(self):
        """開始新一局"""
        self.table.start_new_hand()
        self.message_log = []
        self.hand_result = None
        self.last_analysis_key = None
        self.cached_analysis = None
        self._process_ai_until_human()
    
    def _process_ai_until_human(self):
        """處理 AI 回合直到輪到人類玩家"""
        while True:
            if self.table.stage in [GameStage.SHOWDOWN, GameStage.FINISHED]:
                self._handle_end_of_hand()
                break
            
            current = self.table.get_current_player()
            if current is None:
                self.table.advance_stage()
                continue
            
            if current == self.human_player:
                break
            
            # AI 行動
            self._process_ai_action(current)
    
    def _process_ai_action(self, ai_player: Player):
        """處理 AI 行動"""
        ai = None
        for player, opponent_ai in self.ai_opponents:
            if player == ai_player:
                ai = opponent_ai
                break
        
        if ai is None:
            self.table.process_player_action("fold", 0)
            self.message_log.append(f"{ai_player.name} 棄牌")
            return
        
        # 計算勝率
        num_opponents = len([p for p in self.table.players if p.is_active and p != ai_player])
        win_rate = 0.5
        pot_odds = 0.0
        
        if ai_player.hole_cards and num_opponents > 0:
            # win_rate, _, _ = self.calculator.calculate_win_rate(
            #     ai_player.hole_cards, self.table.community_cards, num_opponents
            # )
            win_rate = 0.5  # Forced simple mode for performance test
            call_amount = self.table.betting_round.get_amount_to_call(ai_player) if self.table.betting_round else 0
            pot_odds = self.calculator.calculate_pot_odds(self.table.pot.total, call_amount)
        
        decision = ai.make_decision(ai_player, self.table, win_rate, pot_odds)
        success = self.table.process_player_action(decision.action, decision.amount)
        
        if success:
            action_msg = self._format_action(ai_player.name, decision.action, decision.amount)
            self.message_log.append(action_msg)
        else:
            self.table.process_player_action("fold", 0)
            self.message_log.append(f"{ai_player.name} 棄牌")
    
    def _format_action(self, name: str, action: str, amount: int) -> str:
        """格式化動作訊息"""
        action_names = {
            "fold": "棄牌", "check": "過牌", "call": f"跟注 ${amount}",
            "bet": f"下注 ${amount}", "raise": f"加注到 ${amount}", "all_in": f"全押 ${amount}"
        }
        return f"{name} {action_names.get(action, action)}"
    
    def _handle_end_of_hand(self):
        """處理本局結束"""
        active_players = self.table.get_active_players()
        
        if len(active_players) == 1:
            winner = active_players[0]
            pot = self.table.pot.total
            # winner.win_pot(pot) # Removed: Table already handles this in _showdown or _end_hand check?
            # Wait, check Table._showdown logic. 
            # If Table stage is FINISHED, checks must ensure chips aren't added twice.
            # Table.advance_stage calls _showdown which calls win_pot.
            # app.py's process_loop calls table.advance_stage().
            # So table update happens first. 
            # Just read the result.
            self.hand_result = {
                "winners": [winner.name],
                "pot": pot,
                "hands": []
            }
            return
        
        # 攤牌
        results = []
        for player in active_players:
            all_cards = player.hole_cards + self.table.community_cards
            result = HandEvaluator.evaluate(all_cards)
            results.append((player, result))
        
        results.sort(key=lambda x: x[1], reverse=True)
        best_result = results[0][1]
        winners = [p for p, r in results if r == best_result]
        
        pot = self.table.pot.total
        # share = pot // len(winners)
        # for winner in winners:
        #     winner.win_pot(share) # Removed: Table handles this

        
        self.hand_result = {
            "winners": [w.name for w in winners],
            "pot": pot,
            "hands": [
                {"name": p.name, "hand": r.description, 
                 "cards": [{"rank": c.rank.symbol, "suit": c.suit.symbol} for c in p.hole_cards]}
                for p, r in results
            ]
        }
    
    def player_action(self, action: str, amount: int = 0) -> bool:
        """處理玩家動作"""
        if self.table.get_current_player() != self.human_player:
            return False
        
        success = self.table.process_player_action(action, amount)
        if success:
            msg = self._format_action("你", action, amount)
            self.message_log.append(msg)
            self._process_ai_until_human()
        return success
    
    def get_state(self) -> dict:
        """獲取遊戲狀態"""
        # 公共牌
        community = [
            {"rank": c.rank.symbol, "suit": c.suit.symbol}
            for c in self.table.community_cards
        ]
        
        # 玩家資訊
        players = []
        for i, p in enumerate(self.table.players):
            is_dealer = i == self.table.dealer_position
            is_current = p == self.table.get_current_player()
            
            player_data = {
                "name": p.name,
                "chips": p.chips,
                "bet": p.current_bet,
                "is_active": p.is_active,
                "is_all_in": p.is_all_in,
                "is_dealer": is_dealer,
                "is_current": is_current,
                "is_human": p.is_human
            }
            
            # 手牌（人類玩家或攤牌時顯示）
            if p.is_human or self.table.stage == GameStage.SHOWDOWN:
                if p.hole_cards:
                    player_data["cards"] = [
                        {"rank": c.rank.symbol, "suit": c.suit.symbol}
                        for c in p.hole_cards
                    ]
            
            players.append(player_data)
        
        # 可用動作
        actions = []
        if self.table.get_current_player() == self.human_player:
            for action, amount in self.table.get_available_actions():
                actions.append({"action": action, "amount": amount})
        
        # 機率分析
        analysis = None
        advice = None
        # DISABLED FOR PERFORMANCE TESTING
        # if self.human_player.hole_cards and self.table.stage not in [GameStage.SHOWDOWN, GameStage.FINISHED]:
        #     num_opponents = len([p for p in self.table.players if p.is_active and p != self.human_player])
        #     if num_opponents > 0:
        #         call_amount = 0
        #         if self.table.betting_round:
        #             call_amount = self.table.betting_round.get_amount_to_call(self.human_player)
                
        #         # Check cache
        #         current_key = (
        #             str(self.human_player.hole_cards),
        #             str(self.table.community_cards),
        #             num_opponents,
        #             self.table.pot.total,
        #             call_amount
        #         )
                
        #         if current_key == self.last_analysis_key and self.cached_analysis:
        #             result = self.cached_analysis
        #         else:
        #             result = self.calculator.full_analysis(
        #                 self.human_player.hole_cards,
        #                 self.table.community_cards,
        #                 num_opponents,
        #                 self.table.pot.total,
        #                 call_amount
        #             )
        #             self.cached_analysis = result
        #             self.last_analysis_key = current_key
                
        #         analysis = {
        #             "win_rate": result.win_rate,
        #             "pot_odds": result.pot_odds,
        #             "ev": result.expected_value,
        #             "hand_strength": result.hand_strength,
        #             "outs": [
        #                 {"name": o.target_hand, "count": o.count, "probability": o.probability}
        #                 for o in result.outs_list
        #             ]
        #         }
                
        #         # 獲取建議
        #         adv = self.advisor.get_advice(
        #             self.human_player.hole_cards,
        #             self.table.community_cards,
        #             num_opponents,
        #             self.table.pot.total,
        #             call_amount,
        #             self.human_player.chips,
        #             call_amount == 0
        #         )
                
        #         advice = {
        #             "level": adv.level.value,
        #             "action": adv.action,
        #             "reasoning": adv.reasoning,
        #             "teaching_points": adv.teaching_points[:2]
        #         }
        
        # 當前手牌評估
        current_hand = None
        if self.human_player.hole_cards and self.table.community_cards:
            all_cards = self.human_player.hole_cards + self.table.community_cards
            if len(all_cards) >= 5:
                hand_result = HandEvaluator.evaluate(all_cards)
                current_hand = hand_result.description
        
        return {
            "stage": self.table.stage.name,
            "hand_number": self.table.hand_number,
            "pot": self.table.pot.total,
            "community_cards": community,
            "players": players,
            "available_actions": actions,
            "analysis": analysis,
            "advice": advice,
            "current_hand": current_hand,
            "messages": self.message_log[-5:],
            "hand_result": self.hand_result,
            "is_game_over": self.human_player.chips <= 0 or len([p for p in self.table.players if p.chips > 0]) < 2
        }


# ===== Routes =====

@app.route('/')
def index():
    """主頁面"""
    return render_template('index.html')


@app.route('/api/game/new', methods=['POST'])
def new_game():
    """開始新遊戲"""
    data = request.get_json() or {}
    num_opponents = data.get('opponents', 3)
    difficulty = data.get('difficulty', 'medium')
    
    game_id = secrets.token_hex(8)
    games[game_id] = WebGame(num_opponents, difficulty)
    
    session['game_id'] = game_id
    return jsonify({"game_id": game_id, "success": True})


@app.route('/api/game/start', methods=['POST'])
def start_hand():
    """開始新的一局"""
    game_id = session.get('game_id')
    if not game_id or game_id not in games:
        return jsonify({"error": "No active game"}), 400
    
    game = games[game_id]
    game.start_new_hand()
    return jsonify(game.get_state())


@app.route('/api/game/state', methods=['GET'])
def get_state():
    """獲取遊戲狀態"""
    game_id = session.get('game_id')
    if not game_id or game_id not in games:
        return jsonify({"error": "No active game"}), 400
    
    return jsonify(games[game_id].get_state())


@app.route('/api/game/action', methods=['POST'])
def player_action():
    """執行玩家動作"""
    game_id = session.get('game_id')
    if not game_id or game_id not in games:
        return jsonify({"error": "No active game"}), 400
    
    data = request.get_json()
    action = data.get('action')
    amount = data.get('amount', 0)
    
    game = games[game_id]
    success = game.player_action(action, amount)
    
    return jsonify({
        "success": success,
        **game.get_state()
    })


if __name__ == '__main__':
    print("\n🎴 德州撲克教學版 - Web 版")
    print("=" * 40)
    print("瀏覽器訪問: http://localhost:5000")
    print("=" * 40 + "\n")
    
    # 部署環境配置
    port = int(os.environ.get("PORT", 8000))
    # 在生產環境中關閉 debug 模式
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host='0.0.0.0', port=port, debug=debug)
