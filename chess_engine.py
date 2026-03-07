from typing import Optional, List, Tuple, Dict, Any
from copy import deepcopy
from dataclasses import dataclass, field


class ChessGame:
   
    
    def __init__(self):
        self.board: List[List[Optional[str]]] = []
        self.current_turn: str = 'white'
        self.selected_square: Optional[Tuple[int, int]] = None
        self.valid_moves: List[Dict[str, Any]] = []
        self.move_history: List[Dict[str, Any]] = []
        self.captured_pieces: Dict[str, List[str]] = {'white': [], 'black': []}
        self.castling_rights = {
            'white': {'king_side': True, 'queen_side': True},
            'black': {'king_side': True, 'queen_side': True}
        }
        self.en_passant_target: Optional[Dict[str, int]] = None
        self.game_over: bool = False
        self.winner: Optional[str] = None
        
        self.initialize_board()
    
    def initialize_board(self) -> None:
        """Initialize the standard chess board setup"""
        self.board = [
            ['br', 'bn', 'bb', 'bq', 'bk', 'bb', 'bn', 'br'],
            ['bp', 'bp', 'bp', 'bp', 'bp', 'bp', 'bp', 'bp'],
            [None] * 8,
            [None] * 8,
            [None] * 8,
            [None] * 8,
            ['wp', 'wp', 'wp', 'wp', 'wp', 'wp', 'wp', 'wp'],
            ['wr', 'wn', 'wb', 'wq', 'wk', 'wb', 'wn', 'wr']
        ]
    
    def get_piece_color(self, piece: Optional[str]) -> Optional[str]:
        """Get the color of a piece"""
        if piece is None:
            return None
        return 'white' if piece[0] == 'w' else 'black'
    
    def get_piece_type(self, piece: Optional[str]) -> Optional[str]:
        """Get the type of a piece"""
        if piece is None:
            return None
        return piece[1]
    
    def is_valid_square(self, row: int, col: int) -> bool:
        """Check if a square is within the board"""
        return 0 <= row < 8 and 0 <= col < 8
    
    def is_path_clear(self, row1: int, col1: int, row2: int, col2: int) -> bool:
        """Check if the path between two squares is clear"""
        row_dir = self._sign(row2 - row1)
        col_dir = self._sign(col2 - col1)
        r = row1 + row_dir
        c = col1 + col_dir
        
        while r != row2 or c != col2:
            if self.board[r][c] is not None:
                return False
            r += row_dir
            c += col_dir
        return True
    
    @staticmethod
    def _sign(x: int) -> int:
        """Return the sign of a number"""
        if x > 0:
            return 1
        elif x < 0:
            return -1
        return 0
    
    def get_valid_moves(self, row: int, col: int) -> List[Dict[str, Any]]:
        """Get all valid moves for a piece at the given position"""
        piece = self.board[row][col]
        if piece is None:
            return []
        
        color = self.get_piece_color(piece)
        piece_type = self.get_piece_type(piece)
        moves = []
        
        
        if piece_type == 'p':
            moves.extend(self.get_pawn_moves(row, col, color))
        elif piece_type == 'r':
            moves.extend(self.get_rook_moves(row, col, color))
        elif piece_type == 'n':
            moves.extend(self.get_knight_moves(row, col, color))
        elif piece_type == 'b':
            moves.extend(self.get_bishop_moves(row, col, color))
        elif piece_type == 'q':
            moves.extend(self.get_queen_moves(row, col, color))
        elif piece_type == 'k':
            moves.extend(self.get_king_moves(row, col, color))
        
       
        return [move for move in moves if not self.would_be_in_check(
            row, col, move['row'], move['col'], color
        )]
    
    def get_pawn_moves(self, row: int, col: int, color: str) -> List[Dict[str, Any]]:
        """Get valid pawn moves"""
        moves = []
        direction = -1 if color == 'white' else 1
        start_row = 6 if color == 'white' else 1
        
        
        if self.is_valid_square(row + direction, col) and self.board[row + direction][col] is None:
            moves.append({'row': row + direction, 'col': col})
            
            
            if row == start_row and self.board[row + 2 * direction][col] is None:
                moves.append({'row': row + 2 * direction, 'col': col})
        
       
        for dc in [-1, 1]:
            new_col = col + dc
            if self.is_valid_square(row + direction, new_col):
                target = self.board[row + direction][new_col]
                if target is not None and self.get_piece_color(target) != color:
                    moves.append({'row': row + direction, 'col': new_col})
                
            
                if (self.en_passant_target and 
                    self.en_passant_target['row'] == row + direction and 
                    self.en_passant_target['col'] == new_col):
                    moves.append({'row': row + direction, 'col': new_col, 'en_passant': True})
        
        return moves
    
    def get_rook_moves(self, row: int, col: int, color: str) -> List[Dict[str, Any]]:
        """Get valid rook moves"""
        moves = []
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        
        for dr, dc in directions:
            for i in range(1, 8):
                new_row = row + dr * i
                new_col = col + dc * i
                
                if not self.is_valid_square(new_row, new_col):
                    break
                
                target = self.board[new_row][new_col]
                if target is None:
                    moves.append({'row': new_row, 'col': new_col})
                else:
                    if self.get_piece_color(target) != color:
                        moves.append({'row': new_row, 'col': new_col})
                    break
        
        return moves
    
    def get_knight_moves(self, row: int, col: int, color: str) -> List[Dict[str, Any]]:
        """Get valid knight moves"""
        moves = []
        offsets = [
            (-2, -1), (-2, 1), (-1, -2), (-1, 2),
            (1, -2), (1, 2), (2, -1), (2, 1)
        ]
        
        for dr, dc in offsets:
            new_row = row + dr
            new_col = col + dc
            
            if self.is_valid_square(new_row, new_col):
                target = self.board[new_row][new_col]
                if target is None or self.get_piece_color(target) != color:
                    moves.append({'row': new_row, 'col': new_col})
        
        return moves
    
    def get_bishop_moves(self, row: int, col: int, color: str) -> List[Dict[str, Any]]:
        """Get valid bishop moves"""
        moves = []
        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        
        for dr, dc in directions:
            for i in range(1, 8):
                new_row = row + dr * i
                new_col = col + dc * i
                
                if not self.is_valid_square(new_row, new_col):
                    break
                
                target = self.board[new_row][new_col]
                if target is None:
                    moves.append({'row': new_row, 'col': new_col})
                else:
                    if self.get_piece_color(target) != color:
                        moves.append({'row': new_row, 'col': new_col})
                    break
        
        return moves
    
    def get_queen_moves(self, row: int, col: int, color: str) -> List[Dict[str, Any]]:
        """Get valid queen moves (combination of rook and bishop)"""
        return (self.get_rook_moves(row, col, color) + 
                self.get_bishop_moves(row, col, color))
    
    def get_king_moves(self, row: int, col: int, color: str) -> List[Dict[str, Any]]:
        """Get valid king moves including castling"""
        moves = []
        offsets = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1), (0, 1),
            (1, -1), (1, 0), (1, 1)
        ]
        
        for dr, dc in offsets:
            new_row = row + dr
            new_col = col + dc
            
            if self.is_valid_square(new_row, new_col):
                target = self.board[new_row][new_col]
                if target is None or self.get_piece_color(target) != color:
                    moves.append({'row': new_row, 'col': new_col})
        
        
        rights = (self.castling_rights['white'] if color == 'white' 
                 else self.castling_rights['black'])
        
      
        if rights['king_side']:
            if self.board[row][col + 1] is None and self.board[row][col + 2] is None:
                moves.append({'row': row, 'col': col + 2, 'castling': 'king_side'})
        
        
        if rights['queen_side']:
            if (self.board[row][col - 1] is None and 
                self.board[row][col - 2] is None and 
                self.board[row][col - 3] is None):
                moves.append({'row': row, 'col': col - 2, 'castling': 'queen_side'})
        
        return moves
    
    def is_square_attacked(self, row: int, col: int, by_color: str) -> bool:
        """Check if a square is attacked by any piece of the given color"""
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece is not None and self.get_piece_color(piece) == by_color:
                    piece_type = self.get_piece_type(piece)
                    
                    
                    if piece_type == 'p':
                        direction = -1 if by_color == 'white' else 1
                        if r + direction == row and (c - 1 == col or c + 1 == col):
                            return True
                    elif piece_type == 'n':
                       
                        dr = abs(r - row)
                        dc = abs(c - col)
                        if (dr == 2 and dc == 1) or (dr == 1 and dc == 2):
                            return True
                    elif piece_type == 'b':
                       
                        if abs(r - row) == abs(c - col) and self.is_path_clear(r, c, row, col):
                            return True
                    elif piece_type == 'r':
                        
                        if (r == row or c == col) and self.is_path_clear(r, c, row, col):
                            return True
                    elif piece_type == 'q':
                       
                        if ((abs(r - row) == abs(c - col) or r == row or c == col) 
                            and self.is_path_clear(r, c, row, col)):
                            return True
                    elif piece_type == 'k':
                       
                        dr = abs(r - row)
                        dc = abs(c - col)
                        if dr <= 1 and dc <= 1 and not (dr == 0 and dc == 0):
                            return True
        
        return False
    
    def find_king(self, color: str) -> Optional[Tuple[int, int]]:
        """Find the position of the king"""
        king = 'wk' if color == 'white' else 'bk'
        for r in range(8):
            for c in range(8):
                if self.board[r][c] == king:
                    return (r, c)
        return None
    
    def is_in_check(self, color: str) -> bool:
        """Check if the king of the given color is in check"""
        king_pos = self.find_king(color)
        if king_pos is None:
            return False
        opponent_color = 'black' if color == 'white' else 'white'
        return self.is_square_attacked(king_pos[0], king_pos[1], opponent_color)
    
    def would_be_in_check(self, from_row: int, from_col: int, 
                          to_row: int, to_col: int, color: str) -> bool:
        """Check if making a move would leave the king in check"""
        
        temp_board = [row[:] for row in self.board]
        temp_en_passant = (dict(self.en_passant_target) 
                          if self.en_passant_target else None)
        
        self.board[to_row][to_col] = self.board[from_row][from_col]
        self.board[from_row][from_col] = None
        
        in_check = self.is_in_check(color)
        
      
        self.board = temp_board
        self.en_passant_target = temp_en_passant
        
        return in_check
    
    def make_move(self, from_row: int, from_col: int, 
                  to_row: int, to_col: int) -> bool:
        """Make a move on the board"""
        piece = self.board[from_row][from_col]
        color = self.get_piece_color(piece)
        piece_type = self.get_piece_type(piece)
        captured = self.board[to_row][to_col]
        
       
        en_passant_captured = None
        if piece_type == 'p' and to_col != from_col and captured is None:
            capture_row = to_row + 1 if color == 'white' else to_row - 1
            en_passant_captured = self.board[capture_row][to_col]
            self.captured_pieces[color].append(en_passant_captured)
            self.board[capture_row][to_col] = None
        
        
        castling_move = None
        if piece_type == 'k' and abs(to_col - from_col) == 2:
            castling_move = 'king_side' if to_col > from_col else 'queen_side'
            rook_col = 7 if castling_move == 'king_side' else 0
            new_rook_col = 5 if castling_move == 'king_side' else 3
            rook = self.board[from_row][rook_col]
            self.board[from_row][new_rook_col] = rook
            self.board[from_row][rook_col] = None
        
       
        self.board[to_row][to_col] = piece
        self.board[from_row][from_col] = None
        
       
        if piece_type == 'p' and abs(to_row - from_row) == 2:
            self.en_passant_target = {
                'row': (from_row + to_row) // 2,
                'col': from_col
            }
        else:
            self.en_passant_target = None
        
        
        promotion = None
        if piece_type == 'p' and (to_row == 0 or to_row == 7):
            promotion = 'q'
            self.board[to_row][to_col] = ('wq' if color == 'white' else 'bq')
        
       
        if piece_type == 'k':
            self.castling_rights[color]['king_side'] = False
            self.castling_rights[color]['queen_side'] = False
        if piece_type == 'r':
            if from_col == 0:
                self.castling_rights[color]['queen_side'] = False
            elif from_col == 7:
                self.castling_rights[color]['king_side'] = False
        
        
        if captured is not None:
            self.captured_pieces[color].append(captured)
        
        
        self.move_history.append({
            'from': {'row': from_row, 'col': from_col},
            'to': {'row': to_row, 'col': to_col},
            'piece': piece,
            'captured': captured or en_passant_captured,
            'castling': castling_move,
            'promotion': promotion,
            'en_passant': en_passant_captured is not None
        })
        
       
        self.current_turn = 'black' if self.current_turn == 'white' else 'white'
        
        
        self.check_game_over()
        
        return True
    
    def check_game_over(self) -> None:
        """Check if the game is over"""
        color = self.current_turn
        
        
        has_valid_moves = False
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece is not None and self.get_piece_color(piece) == color:
                    moves = self.get_valid_moves(r, c)
                    if len(moves) > 0:
                        has_valid_moves = True
                        break
            if has_valid_moves:
                break
        
        if not has_valid_moves:
            self.game_over = True
            if self.is_in_check(color):
                self.winner = 'black' if color == 'white' else 'white'
            else:
                self.winner = 'draw' 
    
    def undo_move(self) -> bool:
        """Undo the last move"""
        if len(self.move_history) == 0:
            return False
        
        last_move = self.move_history.pop()
        from_pos = last_move['from']
        to_pos = last_move['to']
        piece = last_move['piece']
        captured = last_move['captured']
        castling = last_move['castling']
        promotion = last_move['promotion']
        en_passant = last_move['en_passant']
        color = self.get_piece_color(piece)
        
       
        self.board[from_pos['row']][from_pos['col']] = piece
        
        
        if captured is not None:
            self.board[to_pos['row']][to_pos['col']] = captured
        elif en_passant:
           
            capture_row = to_pos['row'] + 1 if color == 'white' else to_pos['row'] - 1
            self.board[capture_row][to_pos['col']] = ('bp' if color == 'white' else 'wp')
            self.board[to_pos['row']][to_pos['col']] = None
        else:
            self.board[to_pos['row']][to_pos['col']] = None
        
      
        if castling is not None:
            rook_col = 7 if castling == 'king_side' else 0
            new_rook_col = 5 if castling == 'king_side' else 3
            rook = self.board[to_pos['row']][new_rook_col]
            self.board[to_pos['row']][rook_col] = rook
            self.board[to_pos['row']][new_rook_col] = None
        
        
        if promotion is not None:
            self.board[from_pos['row']][from_pos['col']] = ('wp' if color == 'white' else 'bp')
        
        
        if captured is not None or en_passant:
            if self.captured_pieces[color]:
                self.captured_pieces[color].pop()
        
        self.current_turn = color
        self.game_over = False
        self.winner = None
         
        
        return True
    
    def get_current_turn(self) -> str:
        """Get the current player's turn"""
        return self.current_turn
    
    def is_game_over(self) -> bool:
        """Check if the game is over"""
        return self.game_over
    
    def get_winner(self) -> Optional[str]:
        """Get the winner of the game"""
        return self.winner
    
    def get_move_history(self) -> List[Dict[str, Any]]:
        """Get the move history"""
        return self.move_history
    
    def get_captured_pieces(self) -> Dict[str, List[str]]:
        """Get captured pieces for both sides"""
        return self.captured_pieces
    
    def get_all_moves(self, color: str) -> List[Dict[str, Any]]:
        """Get all valid moves for all pieces of a given color"""
        all_moves = []
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece is not None and self.get_piece_color(piece) == color:
                    moves = self.get_valid_moves(r, c)
                    for move in moves:
                        all_moves.append({
                            'from': {'row': r, 'col': c},
                            'to': {'row': move['row'], 'col': move['col']}
                        })
        return all_moves
    
    def clone(self) -> 'ChessGame':
        """Create a deep copy of the game"""
        new_game = ChessGame()
        new_game.board = [row[:] for row in self.board]
        new_game.current_turn = self.current_turn
        new_game.captured_pieces = {k: v[:] for k, v in self.captured_pieces.items()}
        new_game.castling_rights = deepcopy(self.castling_rights)
        new_game.en_passant_target = (dict(self.en_passant_target) 
                                      if self.en_passant_target else None)
        new_game.game_over = self.game_over
        new_game.winner = self.winner
        return new_game
