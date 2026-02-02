
import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.table import Table, GameStage
from game.player import HumanPlayer, AIPlayer
from game.card import Card, Deck, Rank, Suit
from game.hand_evaluator import HandEvaluator

class TestPokerGame(unittest.TestCase):
    
    def setUp(self):
        self.table = Table(small_blind=10, big_blind=20)
        self.p1 = HumanPlayer("P1", 1000)
        self.p2 = AIPlayer("P2", 1000)
        self.p3 = AIPlayer("P3", 1000)
        self.table.add_player(self.p1)
        self.table.add_player(self.p2)
        self.table.add_player(self.p3)
        self.table.start_new_hand()

    def test_deck_integrity(self):
        """Test deck creation and shuffling"""
        deck = Deck()
        self.assertEqual(len(deck.cards), 52)
        
    def test_pre_flop_action_all_call(self):
        """Test logic where everyone calls limits"""
        self.table.process_player_action("call", 20)
        self.table.process_player_action("call", 10)
        self.table.process_player_action("check", 0)
        self.assertEqual(self.table.stage, GameStage.FLOP)

    def test_fold_logic(self):
        """Test player folding"""
        self.table.process_player_action("fold")
        self.assertFalse(self.p1.is_active)
        
    def test_raise_logic(self):
        """Test raising"""
        self.table.process_player_action("raise", 40)
        amount_to_call = self.table.betting_round.get_amount_to_call(self.p2)
        self.assertEqual(amount_to_call, 30)
        self.table.process_player_action("call", amount_to_call)
        self.table.process_player_action("call", 20)
        self.assertEqual(self.table.stage, GameStage.FLOP)
        
    def test_all_in_side_pot(self):
        """Test side pot creation with all-in"""
        self.table = Table(10, 20)
        short_stack = HumanPlayer("Shorty", 50)
        big_stack1 = AIPlayer("Big1", 1000)
        big_stack2 = AIPlayer("Big2", 1000)
        self.table.add_player(big_stack1)
        self.table.add_player(big_stack2)
        self.table.add_player(short_stack)
        self.table.start_new_hand()
        self.table.process_player_action("raise", 100)
        self.table.process_player_action("call", 90)
        self.table.process_player_action("all_in", 30)
        
        self.assertEqual(self.table.pot.total, 250)
        self.assertTrue(short_stack.is_all_in)

    def test_hand_evaluator(self):
        """Test hand ranking"""
        # Royal Flush
        cards = [
            Card(Suit.SPADES, Rank.ACE), Card(Suit.SPADES, Rank.KING),
            Card(Suit.SPADES, Rank.QUEEN), Card(Suit.SPADES, Rank.JACK),
            Card(Suit.SPADES, Rank.TEN), Card(Suit.HEARTS, Rank.TWO),
            Card(Suit.DIAMONDS, Rank.THREE)
        ]
        result = HandEvaluator.evaluate(cards)
        self.assertEqual(result.rank.value, 10) # 10 is Royal Flush
        self.assertTrue("同花順" in result.description or "Royal Flush" in result.description)

if __name__ == "__main__":
    unittest.main()
