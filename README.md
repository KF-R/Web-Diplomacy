# Diplomacy Minimal Flask Platform

A small Flask application for hot-seat, LAN, and play-by-mail style Diplomacy adjudication.

## Features
<img width="430" height="270" align="right" alt="Web-Diplomacy" src="https://github.com/user-attachments/assets/6720ebc4-90b2-48a0-a884-6e6acc87322f" />

- Uses SVG board as source of truth for game state
- Shows/hides SVG unit positions by changing `*_pos_A`, `*_pos_F`, and `*_pos_Fs` classes.
- Updates supply-center circles by changing `*_sc` classes.
- Optional controlled-land recolouring via `ctrl_*` classes.
- Accepts complete country-prefixed order sheets.
- Parses abbreviated orders:
  - `A Vie H`
  - `A Vie-Tri`
  - `A Bud S A Vie-Tri`
  - `A Bud S A Vie`
  - `F NTH C A Lon-Nwy`
- Supports split-coast fleet notation:
  - `Bul`, `Spa`, `Stp` = primary/north/east coast.
  - `BUL`, `SPA`, `STP` = secondary/south coast, using SVG ids ending in `Fs`.
- Resolves normal movement, support, support cutting, standoffs, dislodgements, retreats, Fall supply-center capture, builds, and disbands.
- Maintains per-turn history snapshots under `games/default/history/`.

## Install

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open:

```text
http://127.0.0.1:5000/
```

## Notes

This is intentionally compact and hackable. The adjudicator covers the main Diplomacy movement rules and includes convoy path detection, but it is not a formal DATC-certified adjudicator. Treat it as a strong platform foundation and add regression tests for every edge case you care about before tournament or archive-critical use.
