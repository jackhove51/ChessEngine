"""
Running this file will write the data as compressed .pgn.zst files and then
decompress them to games.pgn.
"""
import requests
import zstandard as zstd

url = "https://database.lichess.org/standard/lichess_db_standard_rated_2024-01.pgn.zst"

with requests.get(url, stream=True) as r:
    r.raise_for_status()
    with open("games.pgn.zst", "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

print("Download Complete")

with open("games.pgn.zst", "rb") as compressed:
    dctx = zstd.ZstdDecompressor()
    with open("../scratch/games.pgn", "wb") as output:
        dctx.copy_stream(compressed, output)

print("Decompressed to games.pgn")

