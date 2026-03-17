import os
import json
import uuid
import logging
from flask import Flask, render_template, jsonify, request, send_from_directory
from chess_engine import ChessGame
from chess_ai import ChessAI

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'chess-secret-key-' + str(uuid.uuid4()))

games = {}
ais = {}
users = {}
sessions = {}
learning_data = {}

@app.route('/static/asset/<path:filename>')
def serve_asset(filename):
    return send_from_directory('app/asset', filename)

def get_game(session_id):
    if session_id not in games:
        games[session_id] = ChessGame()
        ais[session_id] = ChessAI(3)
    return games[session_id], ais[session_id]

def get_user_id():
    session_id = request.headers.get('X-Session-ID', 'default')
    session = sessions.get(session_id, {})
    user = session.get('user', {})
    return user.get('email') or user.get('username') or 'guest'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/new-game', methods=['POST'])
def new_game():
    session_id = request.headers.get('X-Session-ID', 'default')
    game, ai = get_game(session_id)
    
    data = request.json or {}
    difficulty = data.get('difficulty', 3)
    game_mode = data.get('gameMode', 'normal')
    user_id = data.get('user_id') or get_user_id()
    
    ai.set_difficulty(difficulty)
    ai.set_learning_mode(game_mode == 'learning')
    ai.set_user_id(user_id)
    
    if game_mode == 'learning' and user_id != 'guest':
        ai.load_learning_data(learning_data.get(user_id, {}))
    
    games[session_id] = ChessGame()
    ais[session_id] = ChessAI(difficulty)
    ais[session_id].set_learning_mode(game_mode == 'learning')
    ais[session_id].set_user_id(user_id)
    
    if game_mode == 'learning' and user_id != 'guest':
        ais[session_id].load_learning_data(learning_data.get(user_id, {}))
    
    return jsonify({
        'board': games[session_id].board,
        'currentTurn': games[session_id].get_current_turn(),
        'gameOver': games[session_id].is_game_over(),
        'winner': games[session_id].get_winner()
    })

@app.route('/api/get-board', methods=['GET'])
def get_board():
    session_id = request.headers.get('X-Session-ID', 'default')
    game, _ = get_game(session_id)
    
    return jsonify({
        'board': game.board,
        'currentTurn': game.get_current_turn(),
        'gameOver': game.is_game_over(),
        'winner': game.get_winner(),
        'inCheck': {
            'white': game.is_in_check('white'),
            'black': game.is_in_check('black')
        }
    })

@app.route('/api/valid-moves', methods=['GET'])
def valid_moves():
    session_id = request.headers.get('X-Session-ID', 'default')
    game, _ = get_game(session_id)
    
    row = request.args.get('row', type=int)
    col = request.args.get('col', type=int)
    
    if row is None or col is None:
        return jsonify({'error': 'Missing row or col'}), 400
    
    moves = game.get_valid_moves(row, col)
    return jsonify({'moves': moves})

@app.route('/api/make-move', methods=['POST'])
def make_move():
    session_id = request.headers.get('X-Session-ID', 'default')
    game, ai = get_game(session_id)
    
    data = request.json
    from_row = data.get('fromRow')
    from_col = data.get('fromCol')
    to_row = data.get('toRow')
    to_col = data.get('toCol')
    
    if None in [from_row, from_col, to_row, to_col]:
        return jsonify({'error': 'Missing move coordinates'}), 400
    
    valid_moves = game.get_valid_moves(from_row, from_col)
    is_valid = any(m['row'] == to_row and m['col'] == to_col for m in valid_moves)
    
    if not is_valid:
        return jsonify({'error': 'Invalid move'}), 400
    
    if ai.learning_mode and ai.user_id and ai.user_id != 'guest':
        board_state = str(game.board)
        move = (from_row, from_col, to_row, to_col)
        ai.record_player_move(board_state, move)
    
    game.make_move(from_row, from_col, to_row, to_col)
    
    return jsonify({
        'board': game.board,
        'currentTurn': game.get_current_turn(),
        'gameOver': game.is_game_over(),
        'winner': game.get_winner(),
        'inCheck': {
            'white': game.is_in_check('white'),
            'black': game.is_in_check('black')
        }
    })

@app.route('/api/ai-move', methods=['POST'])
def ai_move():
    session_id = request.headers.get('X-Session-ID', 'default')
    game, ai = get_game(session_id)
    
    data = request.json or {}
    game_mode = data.get('gameMode', 'normal')
    user_id = data.get('user_id') or get_user_id()
    
    if game.get_current_turn() != 'black' or game.is_game_over():
        return jsonify({'error': 'Not AI turn'}), 400
    
    ai.set_learning_mode(game_mode == 'learning')
    ai.set_user_id(user_id)
    
    move = ai.get_best_move(game)
    
    if move:
        game.make_move(
            move['from']['row'], move['from']['col'],
            move['to']['row'], move['to']['col']
        )
    
    return jsonify({
        'board': game.board,
        'currentTurn': game.get_current_turn(),
        'gameOver': game.is_game_over(),
        'winner': game.get_winner(),
        'aiMove': move,
        'inCheck': {
            'white': game.is_in_check('white'),
            'black': game.is_in_check('black')
        }
    })

@app.route('/api/undo', methods=['POST'])
def undo_move():
    session_id = request.headers.get('X-Session-ID', 'default')
    game, _ = get_game(session_id)
    
    game.undo_move()
    game.undo_move()
    
    return jsonify({
        'board': game.board,
        'currentTurn': game.get_current_turn(),
        'gameOver': game.is_game_over(),
        'winner': game.get_winner()
    })

@app.route('/api/captured-pieces', methods=['GET'])
def captured_pieces():
    session_id = request.headers.get('X-Session-ID', 'default')
    game, _ = get_game(session_id)
    
    return jsonify(game.get_captured_pieces())

@app.route('/api/save-learning', methods=['POST'])
def save_learning():
    session_id = request.headers.get('X-Session-ID', 'default')
    game, ai = get_game(session_id)
    
    user_id = get_user_id()
    
    if user_id != 'guest':
        user_learning = ai.get_learning_data()
        if user_id not in learning_data:
            learning_data[user_id] = {}
        learning_data[user_id].update(user_learning)
        
        try:
            with open('learning_data.json', 'w') as f:
                json.dump(learning_data, f)
        except Exception as e:
            logger.debug(
                "Learning data not written due to exception %s",
                e
            )
    
    return jsonify({'success': True})

@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    session_id = request.headers.get('X-Session-ID', 'default')
    session = sessions.get(session_id)
    
    if session and session.get('user'):
        return jsonify({
            'logged_in': True,
            'user': session['user']
        })
    return jsonify({'logged_in': False})

@app.route('/api/auth/guest', methods=['POST'])
def guest_login():
    session_id = request.headers.get('X-Session-ID', 'default')
    
    guest_user = {
        'username': f'Guest_{session_id[:6]}',
        'is_guest': True
    }
    
    sessions[session_id] = {
        'user': guest_user,
        'is_guest': True
    }
    
    return jsonify({
        'success': True,
        'user': guest_user
    })

@app.route('/api/auth/login', methods=['POST'])
def login():
    session_id = request.headers.get('X-Session-ID', 'default')
    data = request.json
    
    email = data.get('email', '').lower().strip()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password required'}), 400
    
    user = users.get(email)
    if not user or user['password'] != password:
        return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
    
    sessions[session_id] = {
        'user': {
            'username': user['username'],
            'email': email,
            'is_guest': False
        },
        'is_guest': False
    }
    
    return jsonify({
        'success': True,
        'user': sessions[session_id]['user']
    })

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    session_id = request.headers.get('X-Session-ID', 'default')
    data = request.json
    
    username = data.get('username', '').strip()
    email = data.get('email', '').lower().strip()
    password = data.get('password', '')
    
    if not username or not email or not password:
        return jsonify({'success': False, 'message': 'All fields are required'}), 400
    
    if len(password) < 4:
        return jsonify({'success': False, 'message': 'Password must be at least 4 characters'}), 400
    
    if email in users:
        return jsonify({'success': False, 'message': 'Email already registered'}), 409
    
    users[email] = {
        'username': username,
        'password': password
    }
    
    sessions[session_id] = {
        'user': {
            'username': username,
            'email': email,
            'is_guest': False
        },
        'is_guest': False
    }
    
    return jsonify({
        'success': True,
        'user': sessions[session_id]['user']
    })

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session_id = request.headers.get('X-Session-ID', 'default')
    
    if session_id in ais:
        ai = ais[session_id]
        if ai.learning_mode and ai.user_id and ai.user_id != 'guest':
            user_learning = ai.get_learning_data()
            if ai.user_id not in learning_data:
                learning_data[ai.user_id] = {}
            learning_data[ai.user_id].update(user_learning)
    
    if session_id in sessions:
        del sessions[session_id]
    
    return jsonify({'success': True})

def load_learning_data():
    global learning_data
    try:
        with open('learning_data.json', 'r') as f:
            learning_data = json.load(f)
    except FileNotFoundError:
        learning_data = {}
    except Exception:
        learning_data = {}

if __name__ == '__main__':
    load_learning_data()
    app.run(debug=True, host='0.0.0.0', port=5000)
