import random
from typing import List, Dict, Any, Optional
from chess_engine import ChessGame


class ChessAI:

    
    def __init__(self, difficulty: int = 3):
        self.difficulty = difficulty  
        self.search_depths = {
            1: 1,  
            2: 2,  
            3: 3,  
            4: 4,  
            5: 5   
        }
        self.nodes_searched = 0
        
       
        self.learning_mode = False
        self.user_id = None
        self.player_moves = {}  
        
        
        self.piece_values = {
            'p': 100,
            'n': 320,
            'b': 330,
            'r': 500,
            'q': 900,
            'k': 20000
        }
        
       
        self.pst = self._initialize_pst()
    
    def _initialize_pst(self) -> Dict[str, List[List[int]]]:
        """Initialize piece-square tables"""
        pawn_table = [
            [0,  0,  0,  0,  0,  0,  0,  0],
            [50, 50, 50, 50, 50, 50, 50, 50],
            [10, 10, 20, 30, 30, 20, 10, 10],
            [5,  5, 10, 25, 25, 10,  5,  5],
            [0,  0,  0, 20, 20,  0,  0,  0],
            [5, -5, -10,  0,  0, -10, -5,  5],
            [5, 10, 10, -20, -20, 10, 10,  5],
            [0,  0,  0,  0,  0,  0,  0,  0]
        ]

        knight_table = [
            [-50, -40, -30, -30, -30, -30, -40, -50],
            [-40, -20,  0,  0,  0,  0, -20, -40],
            [-30,  0, 10, 15, 15, 10,  0, -30],
            [-30,  5, 15, 20, 20, 15,  5, -30],
            [-30,  0, 15, 20, 20, 15,  0, -30],
            [-30,  5, 10, 15, 15, 10,  5, -30],
            [-40, -20,  0,  5,  5,  0, -20, -40],
            [-50, -40, -30, -30, -30, -30, -40, -50]
        ]

        bishop_table = [
            [-20, -10, -10, -10, -10, -10, -10, -20],
            [-10,  0,  0,  0,  0,  0,  0, -10],
            [-10,  0,  5, 10, 10,  5,  0, -10],
            [-10,  5,  5, 10, 10,  5,  5, -10],
            [-10,  0, 10, 10, 10, 10,  0, -10],
            [-10, 10, 10, 10, 10, 10, 10, -10],
            [-10,  5,  0,  0,  0,  0,  5, -10],
            [-20, -10, -10, -10, -10, -10, -10, -20]
        ]

        rook_table = [
            [0,  0,  0,  0,  0,  0,  0,  0],
            [5, 10, 10, 10, 10, 10, 10,  5],
            [-5,  0,  0,  0,  0,  0,  0, -5],
            [-5,  0,  0,  0,  0,  0,  0, -5],
            [-5,  0,  0,  0,  0,  0,  0, -5],
            [-5,  0,  0,  0,  0,  0,  0, -5],
            [-5,  0,  0,  0,  0,  0,  0, -5],
            [0,  0,  0,  5,  5,  0,  0,  0]
        ]

        queen_table = [
            [-20, -10, -10, -5, -5, -10, -10, -20],
            [-10,  0,  0,  0,  0,  0,  0, -10],
            [-10,  0,  5,  5,  5,  5,  0, -10],
            [-5,  0,  5,  5,  5,  5,  0, -5],
            [0,  0,  5,  5,  5,  5,  0, -5],
            [-10,  5,  5,  5,  5,  5,  0, -10],
            [-10,  0,  5,  0,  0,  0,  0, -10],
            [-20, -10, -10, -5, -5, -10, -10, -20]
        ]

        king_table = [
            [-30, -40, -40, -50, -50, -40, -40, -30],
            [-30, -40, -40, -50, -50, -40, -40, -30],
            [-30, -40, -40, -50, -50, -40, -40, -30],
            [-30, -40, -40, -50, -50, -40, -40, -30],
            [-20, -30, -30, -40, -40, -30, -30, -20],
            [-10, -20, -20, -20, -20, -20, -20, -10],
            [20, 20,  0,  0,  0,  0, 20, 20],
            [20, 30, 10,  0,  0, 10, 30, 20]
        ]

        return {
            'p': pawn_table,
            'n': knight_table,
            'b': bishop_table,
            'r': rook_table,
            'q': queen_table,
            'k': king_table
        }
    
    def set_difficulty(self, level: int) -> None:
        """Set the AI difficulty level"""
        self.difficulty = max(1, min(5, level))
    
    def get_best_move(self, game: ChessGame) -> Optional[Dict[str, Any]]:
        """Get the best move for the current position"""
        self.nodes_searched = 0
        
        depth = self.search_depths[self.difficulty]
        color = game.get_current_turn()
        
       
        if self.difficulty <= 2:
            return self._get_random_move_with_bias(game, color)

        
        moves = game.get_all_moves(color)
        
        if len(moves) == 0:
            return None

        best_move = moves[0]
        best_score = float('-inf')
        alpha = float('-inf')
        beta = float('inf')

      
        ordered_moves = self._order_moves(moves, game, color)

        for move in ordered_moves:
            new_game = game.clone()
            new_game.make_move(
                move['from']['row'], move['from']['col'],
                move['to']['row'], move['to']['col']
            )
            
            score = self._minimax(new_game, depth - 1, alpha, beta, False, color)
            
            if score > best_score:
                best_score = score
                best_move = move
            
            alpha = max(alpha, best_score)

        print(f"AI searched {self.nodes_searched} nodes at depth {depth}")
        return best_move
    
    def _get_random_move_with_bias(self, game: ChessGame, color: str) -> Optional[Dict[str, Any]]:
        """Get a move with some randomness for lower difficulties"""
        moves = game.get_all_moves(color)
        
        if len(moves) == 0:
            return None

        
        random_chance = 0.2 if self.difficulty == 1 else 0.1
        
        if random.random() < random_chance:
            return random.choice(moves)

       
        best_move = moves[0]
        best_score = float('-inf')

        for move in moves:
            new_game = game.clone()
            new_game.make_move(
                move['from']['row'], move['from']['col'],
                move['to']['row'], move['to']['col']
            )
            
            score = self.evaluate_board(new_game, color)
            
            if score > best_score:
                best_score = score
                best_move = move

        return best_move
    
    def _minimax(self, game: ChessGame, depth: int, alpha: float, beta: float, 
                 is_maximizing: bool, original_color: str) -> float:
        """Minimax algorithm with alpha-beta pruning"""
        self.nodes_searched += 1

        if depth == 0 or game.is_game_over():
            return self.evaluate_board(game, original_color)

        color = original_color if is_maximizing else ('white' if original_color == 'black' else 'black')
        moves = game.get_all_moves(color)

        if len(moves) == 0:
            if game.is_in_check(color):
                return -100000 + depth if is_maximizing else 100000 - depth
            return 0  

        
        ordered_moves = self._order_moves(moves, game, color)

        if is_maximizing:
            max_score = float('-inf')
            for move in ordered_moves:
                new_game = game.clone()
                new_game.make_move(
                    move['from']['row'], move['from']['col'],
                    move['to']['row'], move['to']['col']
                )
                
                score = self._minimax(new_game, depth - 1, alpha, beta, False, original_color)
                max_score = max(max_score, score)
                alpha = max(alpha, score)
                
                if beta <= alpha:
                    break  
            
            return max_score
        else:
            min_score = float('inf')
            for move in ordered_moves:
                new_game = game.clone()
                new_game.make_move(
                    move['from']['row'], move['from']['col'],
                    move['to']['row'], move['to']['col']
                )
                
                score = self._minimax(new_game, depth - 1, alpha, beta, True, original_color)
                min_score = min(min_score, score)
                beta = min(beta, score)
                
                if beta <= alpha:
                    break  
            
            return min_score
    
    def _order_moves(self, moves: List[Dict[str, Any]], game: ChessGame, 
                     color: str) -> List[Dict[str, Any]]:
        """Order moves for better alpha-beta pruning (captures first)"""
        scored_moves = []
        
        for move in moves:
            score = 0
            target_piece = game.board[move['to']['row']][move['to']['col']]
            
            if target_piece is not None:
                
                score += self.piece_values[target_piece[1]] * 10
            
           
            test_game = game.clone()
            test_game.make_move(
                move['from']['row'], move['from']['col'],
                move['to']['row'], move['to']['col']
            )
            if test_game.is_in_check('black' if color == 'white' else 'white'):
                score += 50

            scored_moves.append((score, move))
        
      
        scored_moves.sort(key=lambda x: x[0], reverse=True)
        return [move for _, move in scored_moves]
    
   
    def set_learning_mode(self, enabled: bool):
        """Enable or disable learning mode"""
        self.learning_mode = enabled
    
    def set_user_id(self, user_id: str):
        """Set the user ID for learning"""
        self.user_id = user_id
    
    def load_learning_data(self, data: dict):
        """Load player's move history from saved data"""
        if data:
            self.player_moves = data.get('player_moves', {})
    
    def record_player_move(self, board_state: str, move: tuple):
        """Record a player's move for learning"""
        if board_state not in self.player_moves:
            self.player_moves[board_state] = []
        
        move_key = f"{move[0]},{move[1]}->{move[2]},{move[3]}"
        if move_key not in self.player_moves[board_state]:
            self.player_moves[board_state].append(move_key)
    
    def get_preferred_moves(self, board_state: str) -> list:
        """Get player's preferred moves from learning data"""
        return self.player_moves.get(board_state, [])
    
    def get_learning_data(self) -> dict:
        """Get learning data to save"""
        return {
            'player_moves': self.player_moves
        }
    
    def evaluate_board(self, game: ChessGame, ai_color: str) -> float:
        """Evaluate the board position from AI's perspective"""
        board = game.board
        score = 0.0

        for r in range(8):
            for c in range(8):
                piece = board[r][c]
                if piece is None:
                    continue

                piece_type = piece[1]
                piece_color = piece[0]
                value = self.piece_values[piece_type]
                
                
                pst = self.pst[piece_type]
                pst_row = r if piece_color == 'w' else 7 - r
                pst_value = pst[pst_row][c]

                if piece_color == 'w':
                    score += value + pst_value
                else:
                    score -= value + pst_value

        
        if ai_color == 'white':
            if game.castling_rights['white']['king_side']:
                score += 10
            if game.castling_rights['white']['queen_side']:
                score += 10
        else:
            if game.castling_rights['black']['king_side']:
                score -= 10
            if game.castling_rights['black']['queen_side']:
                score -= 10

        
        center_squares = [(3, 3), (3, 4), (4, 3), (4, 4)]
        for r, c in center_squares:
            piece = board[r][c]
            if piece is not None:
                if piece[0] == 'w':
                    score += 5
                else:
                    score -= 5

       
        if game.is_in_check(ai_color):
            score -= 50

        return score if ai_color == 'white' else -score



DIFFICULTY_NAMES = {
    1: 'Beginner',
    2: 'Easy',
    3: 'Medium',
    4: 'Hard',
    5: 'Expert'
}
