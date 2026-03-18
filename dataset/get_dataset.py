import os
import json
from copy import deepcopy
import zstandard as zstd
from pathlib import Path

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
        overwrite: bool = True,
    ):
        """

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

        self.data = deepcopy(self.raw_data)
        # TODO: Implement some kind of hash to ensure position uniqueness

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

    def _parse_fen(self):
        # TODO: Parse fen to align with pre-existing board position
        #  representation and/or desired structure for input tensor
        pass

    # TODO: Remove any of the following - illegal positions, missing info,
    #  illegal castling rights, out-of-range evals

    def _select_eval(self):
        # TODO: Select best eval from the list of evals in a position using
        #  weighted quality (score = depth * log(knodes)). Also,
        #  potentially filter low quality positions
        pass

    def handle_mate_in_n(self):
        pass
        # TODO: Convert to cp eval, assign sign and n
        # mate_in_n = sign + (10000 - 100 * n)
        # cp = min(-1000, min(1000, mate_in_n))

    def normalize(self):
        # TODO: Normalize to [-1, 1] using tanh(cp / 400)
        pass
