from __future__ import annotations

import json
import numpy as np
import math
import chess
import logging
import zstandard as zstd
from typing import Any
from pathlib import Path

logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

INPUT_FILEPATH = Path(__file__).parent / "lichess_db_eval.jsonl.zst"
OUTPUT_FILEPATH = Path(__file__).parent / "lichess_positions.json"
POSITIONS = 100000

PIECE_TO_INDEX = {
    (chess.PAWN, chess.WHITE): 0,
    (chess.KNIGHT, chess.WHITE): 1,
    (chess.BISHOP, chess.WHITE): 2,
    (chess.ROOK, chess.WHITE): 3,
    (chess.QUEEN, chess.WHITE): 4,
    (chess.KING, chess.WHITE): 5,
    (chess.PAWN, chess.BLACK): 6,
    (chess.KNIGHT, chess.BLACK): 7,
    (chess.BISHOP, chess.BLACK): 8,
    (chess.ROOK, chess.BLACK): 9,
    (chess.QUEEN, chess.BLACK): 10,
    (chess.KING, chess.BLACK): 11,
}

# Material values in pawns (used for hand-crafted scalar features)
MATERIAL_VALUES = {
    chess.PAWN: 1.0,
    chess.KNIGHT: 3.0,
    chess.BISHOP: 3.0,
    chess.ROOK: 5.0,
    chess.QUEEN: 9.0,
    chess.KING: 0.0,
}


class Dataset:

    def __init__(
        self,
        input_filepath: Path = INPUT_FILEPATH,
        output_filepath: Path = OUTPUT_FILEPATH,
        max_positions: int = POSITIONS,
        overwrite: bool = False,
    ):
        self.input_filepath = input_filepath
        self.output_filepath = output_filepath
        self.max_positions = max_positions
        self.overwrite = overwrite

        self.data: list[dict[str, Any]] = []
        self.preprocessed_data: list[dict[str, Any]] = []
        self.X: np.ndarray | None = None
        self.y: np.ndarray | None = None

    def __len__(self) -> int:
        return len(self.data)

    def build(self) -> "Dataset":
        self._load()
        self._clean()
        self._preprocess()
        self._vectorize()
        return self

    def _load(self) -> None:
        if self.overwrite or not self.output_filepath.exists():
            self._extract_subset()
            logger.info("Wrote samples to %s", self.output_filepath)
        else:
            logger.info("Using existing samples at %s", self.output_filepath)

        with open(self.output_filepath, "r") as f:
            raw = json.load(f)

        self.data = list({d["fen"]: d for d in raw}.values())
        logger.info("Loaded %d unique positions", len(self.data))

    def _clean(self) -> None:
        valid = []
        for position in self.data:
            try:
                chess.Board(position["fen"]).is_valid()
                valid.append(position)
            except ValueError as e:
                logger.info("Removed invalid FEN %s: %s", position["fen"], e)
        removed = len(self.data) - len(valid)
        if removed:
            logger.info("Removed %d invalid positions", removed)
        self.data = valid

    def _preprocess(self) -> None:
        for position in self.data:
            self._select_eval(position)
            self._handle_pvs(position)
        self.preprocessed_data = self._flatten()
        logger.info("Preprocessed %d positions", len(self.preprocessed_data))

    def _vectorize(self) -> None:
        self.X = np.array(
            [self._fen_to_feature_vector(d["fen"]) for d in self.preprocessed_data]
        )
        self.y = np.array([d["cp"] for d in self.preprocessed_data])
        logger.info("Dataset ready: X=%s y=%s", self.X.shape, self.y.shape)

    def _extract_subset(self) -> None:
        dctx = zstd.ZstdDecompressor()
        with open(self.input_filepath, "rb") as f:
            with dctx.stream_reader(f) as reader:
                with open(self.output_filepath, "wb") as writer:
                    writer.write(b"[\n")
                    line_count = 0
                    buffer = b""
                    first_line = True
                    while line_count < self.max_positions:
                        chunk = reader.read(16384)
                        if not chunk:
                            break
                        buffer = buffer + chunk
                        lines = buffer.split(b"\n")

                        for line in lines[:-1]:
                            if not line.strip():
                                continue
                            prefix = b"" if first_line else b",\n"
                            writer.write(prefix + line)
                            first_line = False
                            line_count += 1
                            if line_count >= self.max_positions:
                                break

                        if line_count >= self.max_positions:
                            break

                        buffer = lines[-1]

                    if buffer.strip() and line_count < self.max_positions:
                        prefix = b"" if first_line else b",\n"
                        writer.write(prefix + buffer)

                    writer.write(b"\n]")

    @staticmethod
    def _select_eval(position: dict[str, Any]) -> None:
        evals = position["evals"]
        best_index = 0
        max_score = 0
        for i, ev in enumerate(evals):
            knodes = ev['knodes']
            depth = ev['depth']
            if knodes > 0:
                score = depth * math.log(knodes)
                if score > max_score:
                    best_index = i
                    max_score = score

        if max_score == 0:
            logger.warning(
                "All evals have knodes=0 for position %s, defaulting to first eval",
                position["fen"]
            )

        position["evals"] = [position["evals"][best_index]]

    @staticmethod
    def _handle_pvs(position: dict[str, Any], max_cp: int = 3000) -> None:
        """
        Selects the top principal variation and converts mate scores to
        centipawn. max_cp raised to 3000 to preserve signal in sharp positions.
        """
        best_pv = position["evals"][0]["pvs"][0]
        mate = best_pv.pop("mate", None)
        if mate is not None:
            best_pv["cp"] = (max_cp - abs(mate)) * (1 if mate > 0 else -1)
        cp = best_pv.get("cp", 0)
        best_pv["cp"] = max(-1.0, min(1.0, cp / max_cp))
        position["evals"][0]["pvs"] = [best_pv]

    def _flatten(self) -> list[dict[str, Any]]:
        return [
            {
                "fen": position["fen"],
                "cp": position["evals"][0]["pvs"][0]["cp"]
            } for position in self.data
        ]

    @staticmethod
    def _fen_to_feature_vector(fen: str) -> np.ndarray:
        board = chess.Board(fen)

        # --- Planes 0–11: piece positions (768 features) ---
        planes = np.zeros((18, 8, 8), dtype=np.float32)
        for square, piece in board.piece_map().items():
            rank, file = divmod(square, 8)
            plane = PIECE_TO_INDEX[(piece.piece_type, piece.color)]
            planes[plane, rank, file] = 1.0

        # Plane 12: side to move
        planes[12, :, :] = 1.0 if board.turn == chess.WHITE else 0.0

        # Planes 13–16: castling rights
        planes[13, :, :] = float(board.has_kingside_castling_rights(chess.WHITE))
        planes[14, :, :] = float(board.has_queenside_castling_rights(chess.WHITE))
        planes[15, :, :] = float(board.has_kingside_castling_rights(chess.BLACK))
        planes[16, :, :] = float(board.has_queenside_castling_rights(chess.BLACK))

        # Plane 17: en passant target file
        if board.ep_square is not None:
            _, ep_file = divmod(board.ep_square, 8)
            planes[17, :, ep_file] = 1.0

        bitboard_features = planes.flatten()  # 1152 features

        # --- Attack maps (128 features) ---
        # Two 8x8 boards: squares attacked by white, squares attacked by black.
        # These encode piece activity and control far more efficiently than the
        # model trying to infer it from piece positions alone.
        white_attacks = np.zeros(64, dtype=np.float32)
        black_attacks = np.zeros(64, dtype=np.float32)
        for square in chess.SQUARES:
            if board.is_attacked_by(chess.WHITE, square):
                white_attacks[square] = 1.0
            if board.is_attacked_by(chess.BLACK, square):
                black_attacks[square] = 1.0
        attack_features = np.concatenate([white_attacks, black_attacks])

        # --- Scalar hand-crafted features (8 features) ---
        # These give the model a strong prior without it needing to derive
        # basic positional concepts from raw squares.
        scalars = np.zeros(8, dtype=np.float32)

        # 0: Material balance (white - black) in pawn units, normalised by 39
        #    (max material on one side: Q+2R+2B+2N+8P = 9+10+6+6+8 = 39)
        white_material = sum(
            MATERIAL_VALUES[p.piece_type]
            for p in board.piece_map().values()
            if p.color == chess.WHITE and p.piece_type != chess.KING
        )
        black_material = sum(
            MATERIAL_VALUES[p.piece_type]
            for p in board.piece_map().values()
            if p.color == chess.BLACK and p.piece_type != chess.KING
        )
        scalars[0] = (white_material - black_material) / 39.0

        # 1: Mobility ratio — white legal moves / (white + black legal moves).
        # Proxy for piece activity. Switch turns to count both sides.
        white_mobility = board.legal_moves.count()
        board.push(chess.Move.null())
        black_mobility = board.legal_moves.count()
        board.pop()
        total_mobility = white_mobility + black_mobility
        scalars[1] = white_mobility / total_mobility if total_mobility > 0 else 0.5

        # 2–3: King safety — number of squares adjacent to each king that are
        # attacked by the opponent. Higher = less safe.
        white_king_sq = board.king(chess.WHITE)
        black_king_sq = board.king(chess.BLACK)
        if white_king_sq is not None:
            adj = chess.SquareSet(chess.BB_KING_ATTACKS[white_king_sq])
            scalars[2] = sum(1 for sq in adj if board.is_attacked_by(chess.BLACK, sq)) / 8.0
        if black_king_sq is not None:
            adj = chess.SquareSet(chess.BB_KING_ATTACKS[black_king_sq])
            scalars[3] = sum(1 for sq in adj if board.is_attacked_by(chess.WHITE, sq)) / 8.0

        # 4–5: Pawn structure — doubled pawns per side (normalised by 8)
        white_pawns = board.pieces(chess.PAWN, chess.WHITE)
        black_pawns = board.pieces(chess.PAWN, chess.BLACK)
        white_pawn_files = [chess.square_file(sq) for sq in white_pawns]
        black_pawn_files = [chess.square_file(sq) for sq in black_pawns]
        scalars[4] = sum(white_pawn_files.count(f) - 1 for f in set(white_pawn_files) if white_pawn_files.count(f) > 1) / 8.0
        scalars[5] = sum(black_pawn_files.count(f) - 1 for f in set(black_pawn_files) if black_pawn_files.count(f) > 1) / 8.0

        # 6–7: Passed pawns per side (normalised by 8).
        # A pawn is passed if no opposing pawn can ever contest its advance.
        def count_passed_pawns(our_pawns, their_pawns, our_color):
            count = 0
            for sq in our_pawns:
                f = chess.square_file(sq)
                r = chess.square_rank(sq)
                adjacent_files = [f] + ([f - 1] if f > 0 else []) + ([f + 1] if f < 7 else [])
                if our_color == chess.WHITE:
                    blockers = [
                        s for s in their_pawns
                        if chess.square_file(s) in adjacent_files and chess.square_rank(s) > r
                    ]
                else:
                    blockers = [
                        s for s in their_pawns
                        if chess.square_file(s) in adjacent_files and chess.square_rank(s) < r
                    ]
                if not blockers:
                    count += 1
            return count

        scalars[6] = count_passed_pawns(white_pawns, black_pawns, chess.WHITE) / 8.0
        scalars[7] = count_passed_pawns(black_pawns, white_pawns, chess.BLACK) / 8.0

        return np.concatenate([bitboard_features, attack_features, scalars])