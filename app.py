
from pathlib import Path
from flask import Flask, jsonify, render_template, request, send_file, abort

from diplomacy_engine import (
    GameStore, POWER_NAMES, HOME_CENTERS, SUPPLY_CENTERS, state_summary,
    parse_order_sheet, resolve_movement, apply_retreats, apply_adjustments,
)

APP_ROOT = Path(__file__).resolve().parent
DATA_ROOT = APP_ROOT / "games" / "default"
TEMPLATE_SVG = APP_ROOT / "data" / "diplomacy_board.svg"

app = Flask(__name__)
store = GameStore(DATA_ROOT, TEMPLATE_SVG)


def public_state(state):
    s = dict(state)
    s["power_names"] = POWER_NAMES
    s["home_centers"] = HOME_CENTERS
    s["supply_centers"] = sorted(SUPPLY_CENTERS)
    s["summary"] = state_summary(state)
    return s


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/state")
def api_state():
    return jsonify(public_state(store.load()))


@app.post("/api/new-game")
def api_new_game():
    state = store.reset()
    return jsonify({"ok": True, "state": public_state(state)})


@app.post("/api/phase/writing")
def api_phase_writing():
    state = store.load()
    state["phase"] = "WRITING"
    store.save(state)
    return jsonify({"ok": True, "state": public_state(state)})


@app.post("/api/settings")
def api_settings():
    state = store.load()
    data = request.get_json(force=True, silent=True) or {}
    settings = state.setdefault("settings", {})
    if "colour_controlled_land" in data:
        settings["colour_controlled_land"] = bool(data["colour_controlled_land"])
    store.save(state)
    return jsonify({"ok": True, "state": public_state(state)})


@app.post("/api/orders")
def api_orders():
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("orders_text", "")
    state = store.load()
    orders, errors, meta = parse_order_sheet(text, state["season"], state["year"])
    state["orders_text"] = text
    store.save(state)
    return jsonify({
        "ok": not errors,
        "errors": errors,
        "meta": meta,
        "orders": [o.as_dict() for o in orders],
        "state": public_state(state),
    })


@app.post("/api/resolve")
def api_resolve():
    state = store.load()
    if state["phase"] not in {"WRITING", "DIPLOMACY"}:
        return jsonify({"ok": False, "errors": [f"Cannot resolve orders during {state['phase']} phase."]}), 400
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("orders_text", state.get("orders_text", ""))
    orders, errors, meta = parse_order_sheet(text, state["season"], state["year"])
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400
    new_state, log = resolve_movement(state, orders)
    # Keep the submitted movement orders in the history snapshot, but clear the
    # live order sheet once movement has been resolved.
    new_state["orders_text"] = ""
    store.append_log(new_state, log)
    store.save(new_state, snapshot=True, orders_text=text, log_text=log)
    return jsonify({"ok": True, "log": log, "state": public_state(new_state)})


@app.post("/api/retreats")
def api_retreats():
    state = store.load()
    if state["phase"] != "RETREAT":
        return jsonify({"ok": False, "errors": ["No retreat phase is currently pending."]}), 400
    data = request.get_json(force=True, silent=True) or {}
    decisions = data.get("decisions", {})
    new_state, log = apply_retreats(state, decisions)
    store.append_log(new_state, log)
    store.save(new_state, snapshot=True, orders_text=state.get("orders_text", ""), log_text=log)
    return jsonify({"ok": True, "log": log, "state": public_state(new_state)})


@app.post("/api/adjustments")
def api_adjustments():
    state = store.load()
    if state["phase"] != "ADJUSTMENT":
        return jsonify({"ok": False, "errors": ["No unit-count adjustment phase is currently pending."]}), 400
    data = request.get_json(force=True, silent=True) or {}
    builds = data.get("builds", [])
    disbands = data.get("disbands", [])
    new_state, log = apply_adjustments(state, builds, disbands)
    store.append_log(new_state, log)
    store.save(new_state, snapshot=True, orders_text=state.get("orders_text", ""), log_text=log)
    return jsonify({"ok": True, "log": log, "state": public_state(new_state)})


@app.get("/board.svg")
def board_svg():
    state = store.load()
    store.save(state)
    return send_file(store.current_svg_path, mimetype="image/svg+xml", max_age=0)


@app.get("/api/history")
def api_history():
    return jsonify({"items": store.history_items()})


@app.get("/history/<snapshot_id>/<name>")
def history_file(snapshot_id, name):
    if name not in {"board.svg", "orders.md", "log.md", "state.json"}:
        abort(404)
    path = DATA_ROOT / "history" / snapshot_id / name
    if not path.exists():
        abort(404)
    mimetype = {
        "board.svg": "image/svg+xml",
        "orders.md": "text/markdown",
        "log.md": "text/markdown",
        "state.json": "application/json",
    }[name]
    return send_file(path, mimetype=mimetype, max_age=0)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
