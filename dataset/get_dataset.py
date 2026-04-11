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

# Replace filename with the path to the downloaded .zst file, which can be
# downloaded at https://database.lichess.org/#evals
INPUT_FILEPATH = Path(__file__).parent / "<filename>.zst"
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


class Dataset:

    def __init__(
        self,
        input_filepath: Path = INPUT_FILEPATH,
        output_filepath: Path = OUTPUT_FILEPATH,
        max_positions: int = POSITIONS,
        overwrite: bool = False,
    ):
        """
        Prepares a chess position dataset from a Lichess .zst evaluation
        archive. Construction is cheap; call build() to run the full pipeline.

        :param input_filepath: Filepath to .zst archive of chess evaluations.
        :param output_filepath: Filepath to existing/desired location of
        decompressed sample of chess evaluations (JSON).
        :param max_positions: Maximum number of lines to read from archive.
        :param overwrite: Whether to overwrite existing samples.
        """
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
        """Run the full pipeline. Returns self for chaining."""
        self._load()
        self._clean()
        self._preprocess()
        self._vectorize()
        return self

    def _load(self) -> None:
        """Decompress archive (if needed) and read JSON into self.data."""
        if self.overwrite or not self.output_filepath.exists():
            self._extract_subset()
            logger.info("Wrote samples to %s", self.output_filepath)
        else:
            logger.info("Using existing samples at %s", self.output_filepath)

        with open(self.output_filepath, "r") as f:
            raw = json.load(f)

        # Deduplicate by FEN
        self.data = list({d["fen"]: d for d in raw}.values())
        logger.info("Loaded %d unique positions", len(self.data))

    def _clean(self) -> None:
        """Remove positions with invalid FENs."""
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
        """Select best eval, normalize scores, flatten to (fen, cp) pairs."""
        for position in self.data:
            self._select_eval(position)
            self._handle_pvs(position)
        self.preprocessed_data = self._flatten()
        logger.info("Preprocessed %d positions", len(self.preprocessed_data))

    def _vectorize(self) -> None:
        """Encode FENs to feature vectors and build X, y arrays."""
        self.X = np.array(
            [self._fen_to_feature_vector(d["fen"]) for d in
             self.preprocessed_data]
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
        """
        In positions with multiple evals, selects the most reliable evaluation
        using depth * log(knodes) as a quality heuristic, and removes the
        others. Falls back to index 0 if no eval has knodes > 0.
        :param position:
        :return:
        """
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
                "All evals have knodes=0 for position %s, "
                "defaulting to first eval",
                position["fen"]
            )

        position["evals"] = [position["evals"][best_index]]

    @staticmethod
    def _handle_pvs(position: dict[str, Any], max_cp: int = 1000) -> None:
        """
        Selects the top principal variation (i.e. best variation) and
        converts "mate in n" to centipawn evaluation, if needed.
        :param position: Chess board state.
        :param max_cp: Upper bound for centipawn evaluation.
        :return:
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

        # Planes 0–11: piece positions
        planes = np.zeros((18, 8, 8), dtype=np.float32)
        for square, piece in board.piece_map().items():
            rank, file = divmod(square, 8)
            plane = PIECE_TO_INDEX[(piece.piece_type, piece.color)]
            planes[plane, rank, file] = 1.0

        # Plane 12: side to move (1.0 = white, 0.0 = black)
        planes[12, :, :] = 1.0 if board.turn == chess.WHITE else 0.0

        # Planes 13–16: castling rights
        planes[13, :, :] = float(
            board.has_kingside_castling_rights(chess.WHITE))
        planes[14, :, :] = float(
            board.has_queenside_castling_rights(chess.WHITE))
        planes[15, :, :] = float(
            board.has_kingside_castling_rights(chess.BLACK))
        planes[16, :, :] = float(
            board.has_queenside_castling_rights(chess.BLACK))

        # Plane 17: en passant (marks the target file if available)
        if board.ep_square is not None:
            _, ep_file = divmod(board.ep_square, 8)
            planes[17, :, ep_file] = 1.0

        return planes.flatten()
