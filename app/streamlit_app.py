import base64
import json
import re
from pathlib import Path
from urllib.parse import quote

import chess
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="AI Chess", page_icon="♟️", layout="centered")

root = Path(__file__).resolve().parent
assets = root / "assets"
pieces_dir = assets / "pieces"
board_img = assets / "board.png"

st.title("♟️ AI Chess")
st.caption("Drag pieces to move")

if not board_img.exists():
    st.error(f"Missing file: {board_img}")
    st.stop()

if not pieces_dir.exists():
    st.error(f"Missing folder: {pieces_dir}")
    st.stop()

if "board" not in st.session_state:
    st.session_state.board = chess.Board()

board = st.session_state.board

if st.button("New Game"):
    st.session_state.board = chess.Board()
    st.query_params.clear()
    st.rerun()

frm = st.query_params.get("from")
to = st.query_params.get("to")

if frm and to:
    try:
        move = chess.Move.from_uci(frm + to)
        if move in board.legal_moves:
            board.push(move)
        else:
            promo = chess.Move.from_uci(frm + to + "q")
            if promo in board.legal_moves:
                board.push(promo)
    except Exception:
        pass
    st.query_params.clear()
    st.rerun()

board_b64 = base64.b64encode(board_img.read_bytes()).decode()
board_url = "data:image/png;base64," + board_b64

wanted = {"bb","bk","bn","bp","bq","br","wb","wk","wn","wp","wq","wr"}
pieces = {}

for f in pieces_dir.iterdir():
    if not f.is_file():
        continue
    m = re.search(r"(bb|bk|bn|bp|bq|br|wb|wk|wn|wp|wq|wr)", f.name.lower())
    if not m:
        continue
    code = m.group(1)
    ext = f.suffix.lower()
    if ext == ".svg":
        svg = f.read_text(encoding="utf-8")
        pieces[code] = "data:image/svg+xml;charset=utf-8," + quote(svg)
    elif ext == ".png":
        pieces[code] = "data:image/png;base64," + base64.b64encode(f.read_bytes()).decode()

missing = sorted(list(wanted - set(pieces.keys())))
if missing:
    st.error("Missing piece files for: " + ", ".join(missing))
    st.stop()

position = {}
for sq in chess.SQUARES:
    piece = board.piece_at(sq)
    if piece:
        name = chess.square_name(sq)
        color = "w" if piece.color else "b"
        kind = {1:"p",2:"n",3:"b",4:"r",5:"q",6:"k"}[piece.piece_type]
        position[name] = color + kind

payload = {
    "board": board_url,
    "pieces": pieces,
    "position": position
}

size = 640
label_pad = 28
board_size = size
wrap_size = board_size + label_pad

html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
#wrap {{
  width: {wrap_size}px;
  height: {wrap_size}px;
  position: relative;
}}

#board {{
  width: {board_size}px;
  height: {board_size}px;
  position: absolute;
  left: {label_pad}px;
  top: 0px;
  background-image: url("{payload["board"]}");
  background-size: cover;
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  grid-template-rows: repeat(8, 1fr);
}}

.square {{
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  border: 1px solid rgba(255,255,255,0.22);
  display: flex;
  align-items: center;
  justify-content: center;
}}

.square.dark {{
  background: rgba(0,0,0,0.12);
}}

.piece {{
  display: block;
  width: 82%;
  height: 82%;
  margin: 0;
  cursor: grab;
  z-index: 10;
  pointer-events: auto;
}}

#fileLabels {{
  position: absolute;
  left: {label_pad}px;
  top: {board_size}px;
  width: {board_size}px;
  height: {label_pad}px;
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  align-items: center;
  color: rgba(255,255,255,0.75);
  font-family: ui-sans-serif, system-ui;
  font-size: 14px;
}}

#rankLabels {{
  position: absolute;
  left: 0px;
  top: 0px;
  width: {label_pad}px;
  height: {board_size}px;
  display: grid;
  grid-template-rows: repeat(8, 1fr);
  align-items: center;
  justify-items: center;
  color: rgba(255,255,255,0.75);
  font-family: ui-sans-serif, system-ui;
  font-size: 14px;
}}

.label {{
  user-select: none;
}}
</style>
</head>
<body style="margin:0">
<div id="wrap">
  <div id="rankLabels"></div>
  <div id="board"></div>
  <div id="fileLabels"></div>
</div>

<script>
const DATA = {json.dumps(payload)};
const boardEl = document.getElementById("board");
const rankLabels = document.getElementById("rankLabels");
const fileLabels = document.getElementById("fileLabels");
const files = ["a","b","c","d","e","f","g","h"];

function buildLabels() {{
  rankLabels.innerHTML = "";
  for (let r = 8; r >= 1; r--) {{
    const d = document.createElement("div");
    d.className = "label";
    d.textContent = String(r);
    rankLabels.appendChild(d);
  }}

  fileLabels.innerHTML = "";
  for (let f = 0; f < 8; f++) {{
    const d = document.createElement("div");
    d.className = "label";
    d.style.textAlign = "center";
    d.textContent = files[f];
    fileLabels.appendChild(d);
  }}
}}

function buildBoard() {{
  boardEl.innerHTML = "";
  for (let r = 7; r >= 0; r--) {{
    for (let f = 0; f < 8; f++) {{
      const sq = document.createElement("div");
      const name = files[f] + (r + 1);
      const isDark = (r + f) % 2 === 1;

      sq.className = "square" + (isDark ? " dark" : "");
      sq.dataset.square = name;

      sq.ondragover = e => e.preventDefault();
      sq.ondrop = e => {{
        e.preventDefault();
        const from = e.dataTransfer.getData("text");
        if (!from || from === name) return;
        window.parent.postMessage({{ type:"move", from:from, to:name }}, "*");
      }};

      const code = DATA.position[name];
      if (code) {{
        const src = DATA.pieces[code];
        if (src) {{
          const img = document.createElement("img");
          img.src = src;
          img.className = "piece";
          img.draggable = true;
          img.ondragstart = e => e.dataTransfer.setData("text", name);
          sq.appendChild(img);
        }}
      }}

      boardEl.appendChild(sq);
    }}
  }}
}}

buildLabels();
buildBoard();

window.addEventListener("message", e => {{
  if (!e.data || e.data.type !== "move") return;
  const p = new URLSearchParams();
  p.set("from", e.data.from);
  p.set("to", e.data.to);
  history.replaceState({{}}, "", "?" + p.toString());
  location.reload();
}});
</script>
</body>
</html>
"""
components.html(html, height=wrap_size + 30)

