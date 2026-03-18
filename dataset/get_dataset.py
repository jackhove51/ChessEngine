from __future__ import annotations

import os
import json
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


class Dataset:

    def __init__(
        self,
        input_filepath: Path = INPUT_FILEPATH,
        output_filepath: Path = OUTPUT_FILEPATH,
        max_positions: int = POSITIONS,
        overwrite: bool = False,
    ):
        """
        Decompresses position evaluations stored in a .zst file and
        preprocesses the data such that each entry is reduced to FEN and
        centipawn evaluation (cp).

        :param input_filepath: Filepath to .zst archive of chess evaluations.
        :param output_filepath: Filepath to existing/desired location of
        decompressed sample of chess evaluations (JSON).
        :param max_positions: Maximum number of lines to read from archive.
        :param overwrite: Whether to overwrite existing samples.
        """
        self.input_filepath = input_filepath
        self.output_filepath = output_filepath
        self.max_positions = max_positions

        # Fail-safes could be added to ensure a pre-existing output file is
        # not empty and contains the proper schema.
        if not overwrite and os.path.exists(self.output_filepath):
            pass
        else:
            self._extract_subset()

        with open(self.output_filepath, 'r') as f:
            self.raw_data = json.load(f)

        # Remove repeated positions
        self.data = list({d["fen"]: d for d in self.raw_data}.values())

        self._parse_fen()

        for position in self.data:
            self._select_eval(position)
            self._handle_pvs(position)

        self.preprocessed_data = self._flatten()

    def __len__(self) -> int:
        return len(self.data)

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

    def _parse_fen(self) -> None:
        # TODO: Do we want to add functionality to convert FEN to match board
        #  structure in chess_engine.py?
        """
        Removes invalid positions
        :return:
        """
        for i, position in enumerate(self.raw_data):
            fen = position["fen"]
            try:
                board = chess.Board(fen)
                board.is_valid()
            except ValueError as e:
                del self.data[i]
                logger.info(
                    "Deleted position at index %s due to ValueError: %s",
                    i, e
                )

    @staticmethod
    def _select_eval(position: dict[str, Any]) -> None:
        """
        In positions with multiple evals, this calculates the best evaluation
        and removes the others
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
        best_pv["cp"] = max(-1.0, min(1.0, best_pv["cp"] / max_cp))
        position["evals"][0]["pvs"] = [best_pv]

    def _flatten(self) -> list[dict[str, Any]]:
        return [
            {
                "fen": position["fen"],
                "cp": position["evals"][0]["pvs"][0]["cp"]
            } for position in self.data
        ]
