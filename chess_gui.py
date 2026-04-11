import tkinter as tk
from tkinter import messagebox, simpledialog
from typing import Optional, List, Tuple, Dict, Any
from chess_engine import ChessGame
from chess_ai import ChessAI, DIFFICULTY_NAMES


class ChessGUI:
    """Main chess game GUI using Tkinter"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Chess Game - 1v1 vs AI")
        self.root.configure(bg='#1a1a2e')
        self.root.resizable(False, False)
        
      
        self.game = ChessGame()
        self.ai = ChessAI(3)
        
        # Game state
        self.game_mode: Optional[str] = None  
        self.ai_difficulty = 3
        self.selected_square: Optional[Tuple[int, int]] = None
        self.valid_moves: List[Dict[str, Any]] = []
        
        
        self.piece_symbols = {
            'wp': '♙', 'wr': '♖', 'wn': '♘', 'wb': '♗', 'wq': '♕', 'wk': '♔',
            'bp': '♟', 'br': '♜', 'bn': '♞', 'bb': '♝', 'bq': '♛', 'bk': '♚'
        }
        
        
        self.light_square = '#f0d9b5'
        self.dark_square = '#b58863'
        self.selected_color = '#ffff00'
        self.valid_move_color = '#90EE90'
        self.capture_color = '#FF6B6B'
        self.check_color = '#FF6B6B'
        
       
        self.square_size = 70
        
        
        self._setup_ui()
        self._render_board()
    
    def _setup_ui(self) -> None:
        """Setup the user interface"""
        
        self.main_frame = tk.Frame(self.root, bg='#1a1a2e')
        self.main_frame.pack(padx=20, pady=20)
        
        
        header_frame = tk.Frame(self.main_frame, bg='#1a1a2e')
        header_frame.pack(pady=(0, 20))
        
        title_label = tk.Label(
            header_frame,
            text="Chess Game",
            font=('Segoe UI', 24, 'bold'),
            bg='#1a1a2e',
            fg='#f0d9b5'
        )
        title_label.pack()
        
        
        self.turn_label = tk.Label(
            header_frame,
            text="White's Turn",
            font=('Segoe UI', 14),
            bg='#1a1a2e',
            fg='#ffffff',
            padx=20,
            pady=5
        )
        self.turn_label.pack(pady=5)
        
        
        self.status_label = tk.Label(
            header_frame,
            text="",
            font=('Segoe UI', 12),
            bg='#1a1a2e',
            fg='#ffd700',
            padx=20,
            pady=5
        )
        self.status_label.pack()
        
        
        self.board_frame = tk.Frame(self.main_frame, bg='#5c4033', bd=5)
        self.board_frame.pack()
        
        
        self.board_canvas = tk.Canvas(
            self.board_frame,
            width=8 * self.square_size,
            height=8 * self.square_size,
            highlightthickness=0
        )
        self.board_canvas.pack()
        
       
        self.board_canvas.bind('<Button-1>', self._on_square_click)
        
       
        control_frame = tk.Frame(self.main_frame, bg='#1a1a2e')
        control_frame.pack(pady=15)
        
        btn_new_game = tk.Button(
            control_frame,
            text="New Game",
            font=('Segoe UI', 11),
            bg='#4a5568',
            fg='#ffffff',
            padx=20,
            pady=5,
            command=self._show_mode_selection
        )
        btn_new_game.pack(side=tk.LEFT, padx=5)
        
        btn_undo = tk.Button(
            control_frame,
            text="Undo",
            font=('Segoe UI', 11),
            bg='#4a5568',
            fg='#ffffff',
            padx=20,
            pady=5,
            command=self._undo_move
        )
        btn_undo.pack(side=tk.LEFT, padx=5)
        
        btn_resign = tk.Button(
            control_frame,
            text="Resign",
            font=('Segoe UI', 11),
            bg='#4a5568',
            fg='#ffffff',
            padx=20,
            pady=5,
            command=self._resign
        )
        btn_resign.pack(side=tk.LEFT, padx=5)
        
        
        captured_frame = tk.Frame(self.main_frame, bg='#1a1a2e')
        captured_frame.pack(pady=10)
        
        self.captured_white_label = tk.Label(
            captured_frame,
            text="White captured:",
            font=('Segoe UI', 10),
            bg='#1a1a2e',
            fg='#f0d9b5'
        )
        self.captured_white_label.pack()
        
        self.captured_white = tk.Label(
            captured_frame,
            text="",
            font=('Segoe UI', 12),
            bg='#1a1a2e',
            fg='#ffffff',
            width=30
        )
        self.captured_white.pack()
        
        self.captured_black_label = tk.Label(
            captured_frame,
            text="Black captured:",
            font=('Segoe UI', 10),
            bg='#1a1a2e',
            fg='#b58863'
        )
        self.captured_black_label.pack()
        
        self.captured_black = tk.Label(
            captured_frame,
            text="",
            font=('Segoe UI', 12),
            bg='#1a1a2e',
            fg='#ffffff',
            width=30
        )
        self.captured_black.pack()
        
        
        self._show_mode_selection()
    
    def _show_mode_selection(self) -> None:
        """Show mode selection dialog"""
        self.game = ChessGame()
        self.selected_square = None
        self.valid_moves = []
        
       
        mode = messagebox.askyesno(
            "Game Mode",
            "Do you want to play against AI?\n\nYes = vs AI\nNo = Player vs Player"
        )
        
        if mode:
          
            self.game_mode = 'ai'
            difficulty = simpledialog.askinteger(
                "AI Difficulty",
                "Select difficulty (1-5):\n1 = Beginner\n2 = Easy\n3 = Medium (default)\n4 = Hard\n5 = Expert",
                parent=self.root,
                minvalue=1,
                maxvalue=5,
                initialvalue=3
            )
            if difficulty is None:
                difficulty = 3
            self.ai_difficulty = difficulty
            self.ai.set_difficulty(difficulty)
        else:
            self.game_mode = '1v1'
        
        self._render_board()
        self._update_display()
    
    def _render_board(self) -> None:
        """Render the chess board"""
        self.board_canvas.delete('all')
        
        board = self.game.board
        
        for row in range(8):
            for col in range(8):
                x1 = col * self.square_size
                y1 = row * self.square_size
                x2 = x1 + self.square_size
                y2 = y1 + self.square_size
                
               
                is_dark = (row + col) % 2 == 1
                color = self.dark_square if is_dark else self.light_square
                
               
                is_selected = (self.selected_square == (row, col))
                is_valid_move = any(m['row'] == row and m['col'] == col for m in self.valid_moves)
                
                if is_selected:
                    color = self.selected_color
                elif is_valid_move:
                    piece = board[row][col]
                    if piece is not None:
                        color = self.capture_color
                    else:
                        color = self.valid_move_color
                
                
                piece = board[row][col]
                if piece is not None and piece[1] == 'k':
                    color_piece = 'white' if piece[0] == 'w' else 'black'
                    if self.game.is_in_check(color_piece):
                        color = self.check_color
                
                
                self.board_canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=color,
                    outline=''
                )
                
               
                if piece is not None:
                    symbol = self.piece_symbols.get(piece, '')
                    piece_color = '#000000' if piece[0] == 'b' else '#ffffff'
                    
                   
                    self.board_canvas.create_text(
                        x1 + self.square_size // 2,
                        y1 + self.square_size // 2 + 2,
                        text=symbol,
                        font=('Segoe UI', 36),
                        fill='#000000'
                    )
                    self.board_canvas.create_text(
                        x1 + self.square_size // 2,
                        y1 + self.square_size // 2,
                        text=symbol,
                        font=('Segoe UI', 36),
                        fill=piece_color
                    )
    
    def _on_square_click(self, event: tk.Event) -> None:
        """Handle square click events"""
        if self.game.is_game_over():
            return
        
        
        col = event.x // self.square_size
        row = event.y // self.square_size
        
        if not self.game.is_valid_square(row, col):
            return
        
        
        if self.game_mode == 'ai' and self.game.get_current_turn() == 'black':
            return
        
        piece = self.game.board[row][col]
        piece_color = self.game.get_piece_color(piece) if piece else None
        current_turn = self.game.get_current_turn()
        
       
        if piece and piece_color == current_turn:
            self.selected_square = (row, col)
            self.valid_moves = self.game.get_valid_moves(row, col)
            self._render_board()
            return
        
      
        if self.selected_square:
            is_valid = any(m['row'] == row and m['col'] == col for m in self.valid_moves)
            
            if is_valid:
                self._make_move(self.selected_square[0], self.selected_square[1], row, col)
            else:
                
                self.selected_square = None
                self.valid_moves = []
                self._render_board()
    
    def _make_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> None:
        """Make a move on the board"""
        self.game.make_move(from_row, from_col, to_row, to_col)
        
        self.selected_square = None
        self.valid_moves = []
        
        self._render_board()
        self._update_display()
        self._check_game_over()
        
      
        if (self.game_mode == 'ai' and 
            not self.game.is_game_over() and 
            self.game.get_current_turn() == 'black'):
            self._make_ai_move()
    
    def _make_ai_move(self) -> None:
        """Make AI move"""
        
        self.status_label.config(text="AI is thinking...")
        self.root.update()
        
       
        best_move = self.ai.get_best_move(self.game)
        
        if best_move:
            self._make_move(
                best_move['from']['row'],
                best_move['from']['col'],
                best_move['to']['row'],
                best_move['to']['col']
            )
        
        self.status_label.config(text="")
    
    def _undo_move(self) -> None:
        """Undo the last move"""
        if self.game_mode == 'ai':
            self.game.undo_move()
        
        if self.game.undo_move():
            self.selected_square = None
            self.valid_moves = []
            self._render_board()
            self._update_display()
            self.status_label.config(text="")
    
    def _resign(self) -> None:
        """Handle resignation"""
        if self.game.is_game_over():
            return
        
        current_turn = self.game.get_current_turn()
        self.game.game_over = True
        self.game.winner = 'black' if current_turn == 'white' else 'white'
        
        winner_name = "Black" if current_turn == 'white' else "White"
        self.status_label.config(text=f"{winner_name} wins by resignation!")
        self._check_game_over()
    
    def _update_display(self) -> None:
        """Update turn indicator and captured pieces"""
        turn = self.game.get_current_turn()
        turn_bg = '#dddddd' if turn == 'white' else '#444444'
        turn_fg = '#333333' if turn == 'white' else '#ffffff'
        self.turn_label.config(
            text=f"{'White' if turn == 'white' else 'Black'}'s Turn",
            bg=turn_bg,
            fg=turn_fg
        )
        
        
        captured = self.game.get_captured_pieces()
        
        white_captured = ''.join([self.piece_symbols.get(p, '') for p in captured['white']])
        black_captured = ''.join([self.piece_symbols.get(p, '') for p in captured['black']])
        
        self.captured_white.config(text=white_captured)
        self.captured_black.config(text=black_captured)
        
       
        if self.game_mode == 'ai':
            # TODO: Is this variable needed?
            diff_name = DIFFICULTY_NAMES.get(self.ai_difficulty, 'Medium')
           
    
    def _check_game_over(self) -> None:
        """Check and display game over status"""
        if self.game.is_game_over():
            winner = self.game.get_winner()
            
            if winner == 'draw':
                message = "Game Over - Draw!"
            else:
                message = f"{'White' if winner == 'white' else 'Black'} wins!"
                
                current_turn = self.game.get_current_turn()
                if self.game.is_in_check(current_turn):
                    message += " (Checkmate!)"
            
            self.status_label.config(text=message)
            messagebox.showinfo("Game Over", message)


def main():
    """Main entry point"""
    root = tk.Tk()
    ChessGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
