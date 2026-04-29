
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Any
import copy
import datetime as _dt
import json
import re
import shutil
import xml.etree.ElementTree as ET


# ---------------------------------------------------------------------------
# Static Diplomacy map data
# ---------------------------------------------------------------------------

POWER_NAMES = {
    "ah": "Austria-Hungary",
    "en": "England",
    "fr": "France",
    "de": "Germany",
    "it": "Italy",
    "ru": "Russia",
    "tu": "Turkey",
    "in": "Independent",
}

POWER_ALIASES = {
    "austria": "ah", "austria-hungary": "ah", "austria_hungary": "ah", "ah": "ah",
    "england": "en", "britain": "en", "great britain": "en", "en": "en",
    "france": "fr", "fr": "fr",
    "germany": "de", "de": "de",
    "italy": "it", "it": "it",
    "russia": "ru", "ru": "ru",
    "turkey": "tu", "ottoman": "tu", "tu": "tu",
}

SEAS = {
    "ADR", "AEG", "BAL", "BAR", "BLA", "BOT", "EAS", "ENG", "HEL", "ION",
    "IRI", "LYO", "MAO", "NAO", "NTH", "NWG", "SKA", "TYS", "WES"
}

ALIASES = {
    "AES": "AEG",      # rules text variant
    "EMS": "EAS",      # rules text variant
    "EAS": "EAS",
    "GOL": "LYO",      # Gulf of Lyon, SVG uses LYO
    "LYO": "LYO",
    "GOB": "BOT",      # Gulf of Bothnia, SVG uses BOT
    "BOT": "BOT",
    "Nwy": "Nwy", "Nor": "Nwy",
    "Lvn": "Lvn", "Liv": "Lvn",
}

SPECIAL_COASTS = {"Bul", "Spa", "Stp"}
COAST_LABEL = {"Bul": ("ec", "sc"), "Spa": ("nc", "sc"), "Stp": ("nc", "sc")}

LAND = {
    "Alb","Ank","Apu","Arm","Bel","Ber","Boh","Bre","Bud","Bul","Bur","Cly","Con",
    "Den","Edi","Fin","Gal","Gas","Gre","Hol","Kie","Lvn","Lon","Lvp","Mar","Mos",
    "Mun","Naf","Nap","Nwy","Par","Pic","Pie","Por","Pru","Rom","Ruh","Rum","Ser",
    "Sev","Sil","Smy","Spa","Stp","Swe","Syr","Tri","Tun","Tus","Tyr","Ukr","Ven",
    "Vie","Wal","War","Yor"
}

SUPPLY_CENTERS = {
    "Vie","Bud","Tri", "Lon","Lvp","Edi", "Par","Bre","Mar", "Ber","Kie","Mun",
    "Rom","Nap","Ven", "Mos","Sev","Stp","War", "Ank","Con","Smy", "Bel","Hol",
    "Den","Nwy","Swe","Spa","Por","Ser","Bul","Rum","Gre","Tun"
}

HOME_CENTERS = {
    "ah": ["Vie", "Bud", "Tri"],
    "en": ["Lon", "Lvp", "Edi"],
    "fr": ["Par", "Bre", "Mar"],
    "de": ["Ber", "Kie", "Mun"],
    "it": ["Rom", "Nap", "Ven"],
    "ru": ["Mos", "Sev", "Stp", "War"],
    "tu": ["Ank", "Con", "Smy"],
}

INITIAL_UNITS = [
    ("ah", "A", "Vie", None), ("ah", "A", "Bud", None), ("ah", "F", "Tri", None),
    ("en", "A", "Lvp", None), ("en", "F", "Lon", None), ("en", "F", "Edi", None),
    ("fr", "A", "Par", None), ("fr", "A", "Mar", None), ("fr", "F", "Bre", None),
    ("de", "A", "Ber", None), ("de", "A", "Mun", None), ("de", "F", "Kie", None),
    ("it", "A", "Ven", None), ("it", "A", "Rom", None), ("it", "F", "Nap", None),
    ("ru", "A", "Mos", None), ("ru", "A", "War", None), ("ru", "F", "Sev", None), ("ru", "F", "Stp", "s"),
    ("tu", "A", "Con", None), ("tu", "A", "Smy", None), ("tu", "F", "Ank", None),
]

INITIAL_SC_CONTROL = {sc: "in" for sc in SUPPLY_CENTERS}
for _p, _homes in HOME_CENTERS.items():
    for _sc in _homes:
        INITIAL_SC_CONTROL[_sc] = _p


# Army adjacency is by province, independent of coasts.
ARMY_ADJ: Dict[str, Set[str]] = {
    "Alb": {"Tri","Ser","Gre"},
    "Ank": {"Arm","Con","Smy"},
    "Apu": {"Ven","Rom","Nap"},
    "Arm": {"Ank","Smy","Syr","Sev"},
    "Bel": {"Pic","Bur","Ruh","Hol"},
    "Ber": {"Kie","Pru","Sil","Mun"},
    "Boh": {"Mun","Sil","Gal","Vie","Tyr"},
    "Bre": {"Pic","Par","Gas"},
    "Bud": {"Vie","Gal","Rum","Ser","Tri"},
    "Bul": {"Rum","Ser","Gre","Con"},
    "Bur": {"Par","Pic","Bel","Ruh","Mun","Mar","Gas"},
    "Cly": {"Lvp","Edi"},
    "Con": {"Bul","Ank","Smy"},
    "Den": {"Kie","Swe"},
    "Edi": {"Cly","Lvp","Yor"},
    "Fin": {"Stp","Nwy","Swe"},
    "Gal": {"Boh","Sil","War","Ukr","Rum","Bud","Vie"},
    "Gas": {"Bre","Par","Bur","Mar","Spa"},
    "Gre": {"Alb","Ser","Bul"},
    "Hol": {"Bel","Ruh","Kie"},
    "Kie": {"Den","Hol","Ruh","Mun","Ber"},
    "Lvn": {"Stp","Mos","War","Pru"},
    "Lon": {"Wal","Yor"},
    "Lvp": {"Cly","Edi","Yor","Wal"},
    "Mar": {"Spa","Gas","Bur","Pie"},
    "Mos": {"Stp","Lvn","War","Ukr","Sev"},
    "Mun": {"Ber","Sil","Boh","Tyr","Bur","Ruh","Kie"},
    "Naf": {"Tun"},
    "Nap": {"Rom","Apu"},
    "Nwy": {"Fin","Stp","Swe"},
    "Par": {"Bre","Pic","Bur","Gas"},
    "Pic": {"Bre","Par","Bur","Bel"},
    "Pie": {"Mar","Tus","Ven","Tyr"},
    "Por": {"Spa"},
    "Pru": {"Ber","Sil","War","Lvn"},
    "Rom": {"Tus","Ven","Apu","Nap"},
    "Ruh": {"Hol","Bel","Bur","Mun","Kie"},
    "Rum": {"Bud","Gal","Ukr","Sev","Bul","Ser"},
    "Ser": {"Tri","Bud","Rum","Bul","Gre","Alb"},
    "Sev": {"Rum","Ukr","Mos","Arm"},
    "Sil": {"Ber","Pru","War","Gal","Boh","Mun"},
    "Smy": {"Con","Ank","Arm","Syr"},
    "Spa": {"Por","Gas","Mar"},
    "Stp": {"Nwy","Fin","Lvn","Mos"},
    "Swe": {"Nwy","Fin","Den"},
    "Syr": {"Smy","Arm"},
    "Tri": {"Ven","Tyr","Vie","Bud","Ser","Alb"},
    "Tun": {"Naf"},
    "Tus": {"Pie","Ven","Rom"},
    "Tyr": {"Mun","Boh","Vie","Tri","Ven","Pie"},
    "Ukr": {"War","Mos","Sev","Rum","Gal"},
    "Ven": {"Pie","Tyr","Tri","Apu","Rom","Tus"},
    "Vie": {"Tyr","Boh","Gal","Bud","Tri"},
    "Wal": {"Lvp","Yor","Lon"},
    "War": {"Pru","Sil","Gal","Ukr","Mos","Lvn"},
    "Yor": {"Edi","Lvp","Wal","Lon"},
}
for a, bs in list(ARMY_ADJ.items()):
    for b in bs:
        ARMY_ADJ.setdefault(b, set()).add(a)


# Fleet adjacency uses explicit coast keys for the three split-coast provinces:
# Bul = east coast, BUL = south coast; Spa = north coast, SPA = south coast;
# Stp = north coast, STP = south coast.
FLEET_ADJ: Dict[str, Set[str]] = {
    "ADR": {"Tri","Ven","Apu","Alb","ION"},
    "AEG": {"Gre","BUL","Con","Smy","ION","EAS"},
    "BAL": {"Den","Kie","Ber","Pru","Lvn","BOT","Swe"},
    "BAR": {"NWG","Nwy","Stp"},
    "BLA": {"Sev","Arm","Ank","Con","Bul","Rum"},
    "BOT": {"BAL","Swe","Fin","STP","Lvn"},
    "EAS": {"AEG","ION","Smy","Syr"},
    "ENG": {"NTH","Bel","Pic","Bre","MAO","IRI","Wal","Lon"},
    "HEL": {"NTH","Hol","Kie","Den"},
    "ION": {"ADR","Alb","Gre","AEG","EAS","Tun","TYS","Nap","Apu"},
    "IRI": {"NAO","Lvp","Wal","ENG","MAO"},
    "LYO": {"Mar","SPA","Pie","Tus","TYS","WES"},
    "MAO": {"NAO","IRI","ENG","Bre","Gas","Spa","Por","WES","Naf"},
    "NAO": {"NWG","Cly","Lvp","IRI","MAO"},
    "NTH": {"NWG","Nwy","SKA","Den","HEL","Hol","Bel","ENG","Lon","Yor","Edi"},
    "NWG": {"BAR","Nwy","NTH","Edi","Cly","NAO"},
    "SKA": {"NTH","Nwy","Swe","Den"},
    "TYS": {"LYO","Tus","Rom","Nap","ION","Tun","WES"},
    "WES": {"MAO","SPA","LYO","TYS","Tun","Naf"},
    "Alb": {"Tri","ADR","ION","Gre"},
    "Ank": {"BLA","Con","Arm"},
    "Apu": {"Ven","ADR","ION","Nap"},
    "Arm": {"BLA","Sev","Ank"},
    "Bel": {"NTH","ENG","Pic","Hol"},
    "Ber": {"BAL","Kie","Pru"},
    "Bre": {"Pic","ENG","MAO","Gas"},
    "Bul": {"BLA","Rum","Con"},           # east coast
    "BUL": {"AEG","Gre","Con"},           # south coast
    "Cly": {"NWG","NAO","Lvp","Edi"},
    "Con": {"Bul","BUL","BLA","Ank","Smy","AEG"},
    "Den": {"HEL","NTH","SKA","Swe","BAL","Kie"},
    "Edi": {"Cly","NWG","NTH","Yor"},
    "Fin": {"BOT","Swe","STP"},
    "Gas": {"Bre","MAO","Spa"},
    "Gre": {"Alb","ION","AEG","BUL"},
    "Hol": {"Bel","NTH","HEL","Kie"},
    "Kie": {"Den","HEL","Hol","Ber","BAL"},
    "Lvn": {"BAL","BOT","STP","Pru"},
    "Lon": {"ENG","NTH","Yor","Wal"},
    "Lvp": {"Cly","NAO","IRI","Wal"},
    "Mar": {"SPA","LYO","Pie"},
    "Naf": {"MAO","WES","Tun"},
    "Nap": {"Apu","ION","TYS","Rom"},
    "Nwy": {"BAR","NWG","NTH","SKA","Swe","Stp"},
    "Pic": {"Bre","ENG","Bel"},
    "Pie": {"Mar","LYO","Tus"},
    "Por": {"MAO","Spa","SPA"},
    "Pru": {"Ber","BAL","Lvn"},
    "Rom": {"Tus","TYS","Nap"},
    "Rum": {"Sev","BLA","Bul"},
    "Sev": {"Rum","BLA","Arm"},
    "Smy": {"Con","AEG","EAS","Syr"},
    "Spa": {"Gas","MAO","Por"},            # north coast
    "SPA": {"Por","WES","LYO","Mar"},      # south coast
    "Stp": {"Nwy","BAR"},                  # north coast
    "STP": {"Fin","BOT","Lvn"},           # south coast
    "Swe": {"Nwy","SKA","Den","BAL","BOT","Fin"},
    "Syr": {"Smy","EAS"},
    "Tri": {"Ven","ADR","Alb"},
    "Tun": {"Naf","WES","TYS","ION"},
    "Tus": {"Pie","LYO","TYS","Rom"},
    "Ven": {"Tri","ADR","Apu"},
    "Wal": {"Lvp","IRI","ENG","Lon"},
    "Yor": {"Edi","NTH","Lon"},
}
for a, bs in list(FLEET_ADJ.items()):
    for b in bs:
        FLEET_ADJ.setdefault(b, set()).add(a)


@dataclass
class Location:
    province: str
    coast: Optional[str] = None

    def key(self) -> str:
        if self.coast == "s" and self.province in SPECIAL_COASTS:
            return self.province.upper()
        return self.province

    def display(self) -> str:
        if self.coast == "s" and self.province in SPECIAL_COASTS:
            return self.province.upper()
        return self.province

    @staticmethod
    def from_token(token: str) -> "Location":
        raw = token.strip().replace(".", "")
        raw = raw.strip()
        if raw in ALIASES:
            raw = ALIASES[raw]
        upper = raw.upper()
        if upper in ALIASES:
            mapped = ALIASES[upper]
            if mapped in SEAS:
                return Location(mapped)
        if upper in SEAS:
            return Location(upper)
        # Capitalized special three-letter region denotes secondary/south coast.
        title = raw[:1].upper() + raw[1:].lower()
        if upper in {s.upper() for s in SPECIAL_COASTS} and raw.isupper():
            return Location(title, "s")
        if title in ALIASES:
            title = ALIASES[title]
        return Location(title)

    def as_dict(self) -> Dict[str, Any]:
        return {"province": self.province, "coast": self.coast}


@dataclass
class Unit:
    id: str
    power: str
    type: str
    loc: str
    coast: Optional[str] = None

    def location(self) -> Location:
        return Location(self.loc, self.coast if self.type == "F" else None)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Order:
    power: str
    unit_type: str
    origin: Location
    kind: str  # H, M, S, C
    dest: Optional[Location] = None
    support_unit_type: Optional[str] = None
    support_origin: Optional[Location] = None
    support_dest: Optional[Location] = None
    via_convoy: bool = False
    raw: str = ""
    valid: bool = True
    reason: str = ""

    def origin_key(self) -> str:
        return self.origin.province

    def summary(self) -> str:
        if self.kind == "H":
            return f"{self.unit_type} {self.origin.display()} holds"
        if self.kind == "M":
            via = " via convoy" if self.via_convoy else ""
            return f"{self.unit_type} {self.origin.display()} → {self.dest.display()}{via}"
        if self.kind == "S":
            if self.support_dest:
                return f"{self.unit_type} {self.origin.display()} supports {self.support_unit_type} {self.support_origin.display()} → {self.support_dest.display()}"
            return f"{self.unit_type} {self.origin.display()} supports {self.support_unit_type} {self.support_origin.display()} to hold"
        if self.kind == "C":
            return f"{self.unit_type} {self.origin.display()} convoys {self.support_unit_type} {self.support_origin.display()} → {self.support_dest.display()}"
        return self.raw

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["origin"] = self.origin.as_dict()
        d["dest"] = self.dest.as_dict() if self.dest else None
        d["support_origin"] = self.support_origin.as_dict() if self.support_origin else None
        d["support_dest"] = self.support_dest.as_dict() if self.support_dest else None
        return d


# ---------------------------------------------------------------------------
# General helpers
# ---------------------------------------------------------------------------

def canonical_power(name: str) -> Optional[str]:
    return POWER_ALIASES.get(name.strip().lower())

def fleet_key(loc: Location) -> str:
    return loc.key()

def base(loc_or_code: Location | str) -> str:
    return loc_or_code.province if isinstance(loc_or_code, Location) else loc_or_code

def has_coast(province: str) -> bool:
    return province in FLEET_ADJ or province.upper() in FLEET_ADJ

def legal_army_move(origin: str, dest: str) -> bool:
    return dest in ARMY_ADJ.get(origin, set())

def legal_fleet_move(origin: Location, dest: Location) -> bool:
    # For split-coast destinations, an unspecified coast is accepted only when one
    # adjacent coast is possible. If both would be possible, require explicit coast.
    ok = fleet_key(dest) in FLEET_ADJ.get(fleet_key(origin), set())
    if ok:
        return True
    if dest.province in SPECIAL_COASTS and dest.coast is None:
        choices = [Location(dest.province, None).key(), Location(dest.province, "s").key()]
        return any(c in FLEET_ADJ.get(fleet_key(origin), set()) for c in choices)
    return False

def normalize_dest_for_fleet(origin: Location, dest: Location) -> Location:
    if dest.province in SPECIAL_COASTS and dest.coast is None:
        choices = [Location(dest.province, None), Location(dest.province, "s")]
        possible = [c for c in choices if c.key() in FLEET_ADJ.get(fleet_key(origin), set())]
        if len(possible) == 1:
            return possible[0]
    return dest

def can_move(unit_type: str, origin: Location, dest: Location, convoy_possible: bool = False) -> bool:
    if unit_type == "A":
        return legal_army_move(origin.province, dest.province) or convoy_possible
    return legal_fleet_move(origin, dest)

def support_can_reach(supporter: Unit, target: Location) -> bool:
    # Support is adjudicated as "could the supporting unit move to the province
    # being attacked/held?", ignoring occupancy.
    if supporter.type == "A":
        return legal_army_move(supporter.loc, target.province)
    return legal_fleet_move(supporter.location(), target)


def initial_state() -> Dict[str, Any]:
    units = []
    n = 1
    for power, utype, loc, coast in INITIAL_UNITS:
        units.append(Unit(f"u{n:03d}", power, utype, loc, coast).as_dict())
        n += 1
    return {
        "game_id": "default",
        "year": 1901,
        "season": "Spring",
        "phase": "DIPLOMACY",
        "units": units,
        "centers": dict(sorted(INITIAL_SC_CONTROL.items())),
        "orders_text": "",
        "pending_retreats": [],
        "pending_adjustments": {},
        "logs": [],
        "history": [],
        "unit_seq": n,
        "settings": {"colour_controlled_land": False},
    }


def normalize_loaded_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Repair older untouched games created before War was in Russia's home centers."""
    if (
        state.get("year") == 1901
        and state.get("season") == "Spring"
        and not state.get("history")
        and not state.get("logs")
        and state.get("centers", {}).get("War") == "in"
    ):
        has_initial_warsaw_army = any(
            u.get("power") == "ru" and u.get("type") == "A" and u.get("loc") == "War"
            for u in state.get("units", [])
        )
        if has_initial_warsaw_army:
            state["centers"]["War"] = "ru"
    return state


# ---------------------------------------------------------------------------
# Order parsing
# ---------------------------------------------------------------------------

def clean_order_text(text: str) -> str:
    text = text.replace("—", "-").replace("–", "-").replace("−", "-")
    text = re.sub(r"\bto\b", "-", text, flags=re.I)
    text = re.sub(r"\bholds?\b", " H ", text, flags=re.I)
    text = re.sub(r"\bsupports?\b", " S ", text, flags=re.I)
    text = re.sub(r"\bconvoys?\b", " C ", text, flags=re.I)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def parse_single_order(power: str, raw: str) -> Order:
    original = raw.strip()
    s = clean_order_text(original)
    # Standard abbreviation starts with A/F + origin.
    m = re.match(r"^(A|F)\s+([A-Za-z]{3})(?:\s+|(?=-))(.*)$", s, re.I)
    if not m:
        return Order(power, "?", Location("???"), "H", raw=original, valid=False, reason="Could not parse order.")
    unit_type = m.group(1).upper()
    origin = Location.from_token(m.group(2))
    rest = m.group(3).strip()

    # Hold
    if rest.upper() in {"H", "HOLD"}:
        return Order(power, unit_type, origin, "H", raw=original)

    # Convoy: F NTH C A Lon-Nwy
    m = re.match(r"^C\s+(A)\s+([A-Za-z]{3})\s*-\s*([A-Za-z]{3})(?:\s+.*)?$", rest, re.I)
    if m:
        return Order(
            power, unit_type, origin, "C",
            support_unit_type=m.group(1).upper(),
            support_origin=Location.from_token(m.group(2)),
            support_dest=Location.from_token(m.group(3)),
            raw=original,
        )

    # Support: A Bud S A Vie-Tri  OR A Bud S A Vie
    m = re.match(r"^S\s+(A|F)\s+([A-Za-z]{3})(?:\s*-\s*([A-Za-z]{3}))?(?:\s+.*)?$", rest, re.I)
    if m:
        return Order(
            power, unit_type, origin, "S",
            support_unit_type=m.group(1).upper(),
            support_origin=Location.from_token(m.group(2)),
            support_dest=Location.from_token(m.group(3)) if m.group(3) else None,
            raw=original,
        )

    # Move: A Vie-Tri [via convoy]
    m = re.match(r"^-?\s*([A-Za-z]{3})(?:\s+via\s+convoy)?$", rest, re.I)
    if m:
        dest = Location.from_token(m.group(1))
        via_convoy = bool(re.search(r"via\s+convoy", rest, flags=re.I))
        return Order(power, unit_type, origin, "M", dest=dest, via_convoy=via_convoy, raw=original)

    return Order(power, unit_type, origin, "H", raw=original, valid=False, reason="Unrecognized order shape.")

def parse_order_sheet(text: str, current_season: Optional[str] = None, current_year: Optional[int] = None) -> Tuple[List[Order], List[str], Dict[str, Any]]:
    orders: List[Order] = []
    errors: List[str] = []
    meta: Dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("###"):
            continue
        # Header: Spring 1901 / Fall 1901
        hm = re.match(r"^(Spring|Fall)\s+(\d{4})$", line, re.I)
        if hm:
            meta["season"] = hm.group(1).title()
            meta["year"] = int(hm.group(2))
            continue
        if ":" not in line:
            continue
        country, order_blob = line.split(":", 1)
        power = canonical_power(country)
        if not power:
            errors.append(f"Unknown country line: {country}")
            continue
        for part in [p.strip() for p in order_blob.split(",") if p.strip()]:
            order = parse_single_order(power, part)
            if not order.valid:
                errors.append(f"{POWER_NAMES[power]}: {part}: {order.reason}")
            orders.append(order)
    if current_season and "season" in meta and meta["season"] != current_season:
        errors.append(f"Sheet is for {meta['season']}; current game season is {current_season}.")
    if current_year and "year" in meta and meta["year"] != current_year:
        errors.append(f"Sheet is for {meta['year']}; current game year is {current_year}.")
    return orders, errors, meta


# ---------------------------------------------------------------------------
# Adjudication
# ---------------------------------------------------------------------------

def units_by_loc(state: Dict[str, Any]) -> Dict[str, Unit]:
    out = {}
    for u in state["units"]:
        unit = Unit(**u)
        out[unit.loc] = unit
    return out

def unit_at(state: Dict[str, Any], loc: str) -> Optional[Unit]:
    return units_by_loc(state).get(loc)

def convoy_graph(orders: List[Order], state: Dict[str, Any]) -> Dict[str, Set[str]]:
    """Sea-region graph using only fleets that gave matching convoy orders."""
    graph: Dict[str, Set[str]] = {}
    locs = units_by_loc(state)
    for o in orders:
        if o.kind != "C" or not o.valid:
            continue
        u = locs.get(o.origin.province)
        if not u or u.type != "F" or u.loc not in SEAS:
            continue
        graph.setdefault(u.loc, set())
    for a in list(graph):
        for b in list(graph):
            if a != b and b in FLEET_ADJ.get(a, set()):
                graph[a].add(b)
    return graph

def convoy_possible_for(order: Order, orders: List[Order], state: Dict[str, Any]) -> bool:
    if order.kind != "M" or order.unit_type != "A" or not order.dest:
        return False
    # Land move needs no convoy unless explicitly specified.
    if legal_army_move(order.origin.province, order.dest.province) and not order.via_convoy:
        return False

    # Need at least one convoy order matching this army and destination.
    convoying = []
    locs = units_by_loc(state)
    for co in orders:
        if co.kind != "C" or co.support_unit_type != "A" or not co.support_origin or not co.support_dest:
            continue
        if co.support_origin.province == order.origin.province and co.support_dest.province == order.dest.province:
            u = locs.get(co.origin.province)
            if u and u.type == "F" and u.loc in SEAS:
                convoying.append(co.origin.province)
    if not convoying:
        return False

    graph = convoy_graph(orders, state)
    start_seas = [x for x in FLEET_ADJ if x in SEAS and x in FLEET_ADJ.get(order.origin.province, set()) and x in graph]
    end_seas = {x for x in FLEET_ADJ if x in SEAS and order.dest.province in FLEET_ADJ.get(x, set()) and x in graph}
    if not start_seas or not end_seas:
        return False
    q = list(start_seas)
    seen = set(q)
    while q:
        cur = q.pop(0)
        if cur in end_seas:
            return True
        for nxt in graph.get(cur, set()):
            if nxt not in seen:
                seen.add(nxt); q.append(nxt)
    return False


def order_signature(o: Order) -> Tuple[Any, ...]:
    """Comparable shape used only to detect conflicting implicit orders."""
    if o.kind == "M" and o.dest:
        return (o.kind, o.dest.province, o.dest.coast)
    if o.kind == "H":
        return (o.kind,)
    return (o.kind,)

def describe_order_short(o: Order) -> str:
    if o.kind == "M" and o.dest:
        return f"{o.unit_type} {o.origin.display()}-{o.dest.display()}"
    if o.kind == "H":
        return f"{o.unit_type} {o.origin.display()} H"
    return o.summary()

def synthesize_implicit_orders(state: Dict[str, Any], orders: List[Order]) -> Tuple[List[Order], List[str]]:
    """Add missing owner orders implied by that same owner's support/convoy orders.

    Explicit written orders always take precedence. If the same omitted unit is
    implied to do two different things, no order is synthesized and the normal
    default Hold order applies.
    """
    notes: List[str] = []
    by_loc = units_by_loc(state)

    explicit_locs: Set[str] = set()
    for o in orders:
        if o.origin.province in by_loc:
            explicit_locs.add(o.origin.province)

    proposed: Dict[str, List[Tuple[Order, str]]] = {}

    def add_proposal(loc: str, order: Order, source: str) -> None:
        if loc in explicit_locs:
            return
        proposed.setdefault(loc, []).append((order, source))

    for o in orders:
        if not o.valid:
            continue

        if o.kind == "S" and o.support_origin:
            target_unit = by_loc.get(o.support_origin.province)
            if not target_unit or target_unit.power != o.power or target_unit.type != o.support_unit_type:
                continue
            origin = target_unit.location()
            if o.support_dest:
                add_proposal(
                    target_unit.loc,
                    Order(
                        target_unit.power, target_unit.type, origin, "M",
                        dest=o.support_dest, raw=f"[implicit from {o.raw}]",
                    ),
                    o.raw,
                )
            else:
                add_proposal(
                    target_unit.loc,
                    Order(
                        target_unit.power, target_unit.type, origin, "H",
                        raw=f"[implicit from {o.raw}]",
                    ),
                    o.raw,
                )

        if o.kind == "C" and o.support_origin and o.support_dest:
            target_unit = by_loc.get(o.support_origin.province)
            if not target_unit or target_unit.power != o.power or target_unit.type != "A":
                continue
            add_proposal(
                target_unit.loc,
                Order(
                    target_unit.power, "A", target_unit.location(), "M",
                    dest=o.support_dest, via_convoy=True,
                    raw=f"[implicit from {o.raw}]",
                ),
                o.raw,
            )

    implicit: List[Order] = []
    for loc, items in sorted(proposed.items()):
        sigs = {order_signature(o) for o, _src in items}
        unit = by_loc.get(loc)
        if not unit:
            continue
        if len(sigs) > 1:
            refs = "; ".join(describe_order_short(o) for o, _src in items)
            notes.append(f"Ambiguous implicit order for {unit.type} {unit.location().display()}; treated as hold ({refs}).")
            continue
        chosen = copy.deepcopy(items[0][0])
        if chosen.kind == "M":
            chosen.via_convoy = any(o.via_convoy for o, _src in items)
        sources = "; ".join(src for _o, src in items)
        notes.append(f"Implicit order: {describe_order_short(chosen)} inferred from {sources}.")
        implicit.append(chosen)

    if not implicit:
        return orders, notes
    return [*orders, *implicit], notes

def validate_orders(state: Dict[str, Any], orders: List[Order]) -> Tuple[Dict[str, Order], List[str]]:
    orders, notes = synthesize_implicit_orders(state, orders)
    by_loc = units_by_loc(state)
    final: Dict[str, Order] = {}

    for o in orders:
        u = by_loc.get(o.origin.province)
        if not o.valid:
            notes.append(f"Invalid: {o.raw}: {o.reason}")
            continue
        if not u:
            o.valid = False; o.reason = "No unit at origin."
            notes.append(f"Invalid: {o.raw}: no unit at {o.origin.display()}.")
            continue
        if u.power != o.power:
            o.valid = False; o.reason = "Country does not control this unit."
            notes.append(f"Invalid: {o.raw}: {POWER_NAMES[o.power]} does not control {u.type} {u.location().display()}.")
            continue
        if u.type != o.unit_type:
            o.valid = False; o.reason = "Wrong unit type."
            notes.append(f"Invalid: {o.raw}: unit at {u.loc} is {u.type}, not {o.unit_type}.")
            continue
        if o.kind == "M":
            if o.unit_type == "F":
                o.dest = normalize_dest_for_fleet(u.location(), o.dest)
            conv = convoy_possible_for(o, orders, state)
            if not can_move(o.unit_type, u.location(), o.dest, conv):
                o.valid = False; o.reason = "Illegal move adjacency."
                notes.append(f"Invalid: {o.raw}: {o.unit_type} {o.origin.display()} cannot move to {o.dest.display()}.")
                continue
        if o.kind == "S":
            target = o.support_dest if o.support_dest else o.support_origin
            supporter = u
            if target and not support_can_reach(supporter, target):
                o.valid = False; o.reason = "Supporter cannot reach target province."
                notes.append(f"Invalid: {o.raw}: supporter cannot reach {target.display()}.")
                continue
        if o.kind == "C":
            if u.type != "F" or u.loc not in SEAS:
                o.valid = False; o.reason = "Only fleets in sea regions can convoy."
                notes.append(f"Invalid: {o.raw}: convoying unit must be a fleet in a sea province.")
                continue
        # Last order for same origin wins, matching normal order-sheet correction habits.
        final[o.origin.province] = o

    # Default holds for unordered units.
    for loc, u in by_loc.items():
        if loc not in final:
            final[loc] = Order(u.power, u.type, u.location(), "H", raw=f"{u.type} {u.location().display()} H")
    return final, notes

def resolve_movement(state: Dict[str, Any], orders: List[Order]) -> Tuple[Dict[str, Any], str]:
    new_state = copy.deepcopy(state)
    by_loc = units_by_loc(new_state)
    order_by_loc, notes = validate_orders(new_state, orders)
    log: List[str] = [f"{new_state['season']} {new_state['year']} Movement Resolution", ""]

    for n in notes:
        log.append("- " + n)

    moves = {loc: o for loc, o in order_by_loc.items() if o.kind == "M" and o.valid and o.dest}
    supports = [o for o in order_by_loc.values() if o.kind == "S" and o.valid]
    convoys = [o for o in order_by_loc.values() if o.kind == "C" and o.valid]

    # Validate support target consistency.
    for s in supports:
        if s.support_dest:
            target_order = order_by_loc.get(s.support_origin.province)
            if not target_order or target_order.kind != "M" or not target_order.dest or target_order.dest.province != s.support_dest.province:
                s.valid = False
                log.append(f"- Support ineffective: {s.summary()} (target unit did not make that move).")
        else:
            target_order = order_by_loc.get(s.support_origin.province)
            if target_order and target_order.kind == "M":
                s.valid = False
                log.append(f"- Support ineffective: {s.summary()} (target unit moved).")

    # Determine support cuts by attacks on the supporter.
    attacks_by_dest: Dict[str, List[Order]] = {}
    for m in moves.values():
        attacks_by_dest.setdefault(m.dest.province, []).append(m)

    support_cut: Set[str] = set()
    for s in supports:
        if not s.valid:
            continue
        supporter_loc = s.origin.province
        for attack in attacks_by_dest.get(supporter_loc, []):
            attacker = by_loc.get(attack.origin.province)
            supporter = by_loc.get(supporter_loc)
            if not attacker or not supporter or attacker.power == supporter.power:
                continue
            # Province against which support is directed does not cut support by
            # mere attack; it must dislodge, which we approximate in a second pass.
            protected_target = s.support_dest.province if s.support_dest else s.support_origin.province
            if attack.origin.province != protected_target:
                support_cut.add(supporter_loc)
                log.append(f"- Support cut: {s.summary()} by {attack.summary()}.")
                break

    def strength_for_move(m: Order) -> int:
        strength = 1
        for s in supports:
            if not s.valid or s.origin.province in support_cut or not s.support_dest:
                continue
            if s.support_origin.province == m.origin.province and s.support_dest.province == m.dest.province:
                strength += 1
        return strength

    def defense_strength(loc: str) -> int:
        unit = by_loc.get(loc)
        if not unit:
            return 0
        own_order = order_by_loc.get(loc)
        strength = 1
        if own_order and own_order.kind == "M":
            return strength
        for s in supports:
            if not s.valid or s.origin.province in support_cut or s.support_dest is not None:
                continue
            if s.support_origin.province == loc:
                strength += 1
        return strength

    move_strength = {loc: strength_for_move(o) for loc, o in moves.items()}
    defense = {loc: defense_strength(loc) for loc in by_loc}

    # One additional cut pass for attacks from the province being supported against:
    # if such an attack dislodges the supporter without that support, cut it.
    changed = True
    while changed:
        changed = False
        for s in supports:
            if not s.valid or s.origin.province in support_cut:
                continue
            protected_target = s.support_dest.province if s.support_dest else s.support_origin.province
            for attack in attacks_by_dest.get(s.origin.province, []):
                if attack.origin.province != protected_target:
                    continue
                attacker = by_loc.get(attack.origin.province)
                supporter = by_loc.get(s.origin.province)
                if not attacker or not supporter or attacker.power == supporter.power:
                    continue
                if move_strength.get(attack.origin.province, 1) > defense_strength(s.origin.province):
                    support_cut.add(s.origin.province)
                    log.append(f"- Support cut by dislodgement: {s.summary()} by {attack.summary()}.")
                    changed = True

    move_strength = {loc: strength_for_move(o) for loc, o in moves.items()}
    defense = {loc: defense_strength(loc) for loc in by_loc}

    # Destination contests.
    dest_to_moves: Dict[str, List[Order]] = {}
    for loc, m in moves.items():
        dest_to_moves.setdefault(m.dest.province, []).append(m)

    candidate_success: Dict[str, bool] = {loc: False for loc in moves}
    embattled: Set[str] = set()

    for dest, contenders in dest_to_moves.items():
        ranked = sorted(contenders, key=lambda m: move_strength[m.origin.province], reverse=True)
        top_strength = move_strength[ranked[0].origin.province]
        top = [m for m in ranked if move_strength[m.origin.province] == top_strength]
        if len(top) > 1:
            embattled.add(dest)
            log.append(f"- Standoff in {dest}: " + "; ".join(f"{m.summary()} ({move_strength[m.origin.province]})" for m in top))
            continue
        candidate = top[0]
        occupant = by_loc.get(dest)
        if occupant and occupant.power == by_loc[candidate.origin.province].power:
            # May enter only if own unit successfully leaves; decide after fixed-point.
            candidate_success[candidate.origin.province] = True
        elif occupant:
            # Tentatively allow the attack.  If the occupant does not leave, the
            # fixed-point pass below will require the attack to beat the defender's
            # strength.  This matters for ordinary moves into spaces vacated by a
            # successful enemy move: the moving unit is not still defending its
            # origin province and should not block an otherwise uncontested entry.
            candidate_success[candidate.origin.province] = True
        else:
            candidate_success[candidate.origin.province] = True

    # No direct swaps unless the move is a convoyed army.
    for loc, m in moves.items():
        other = moves.get(m.dest.province)
        if other and other.dest and other.dest.province == loc:
            if not (m.unit_type == "A" and m.via_convoy) and not (other.unit_type == "A" and other.via_convoy):
                if candidate_success.get(loc) or candidate_success.get(m.dest.province):
                    log.append(f"- Direct swap blocked: {m.summary()} and {other.summary()}.")
                candidate_success[loc] = False
                candidate_success[m.dest.province] = False
                embattled.add(loc); embattled.add(m.dest.province)

    # Resolve dependency on own/enemy occupant leaving.
    stable = False
    while not stable:
        stable = True
        for loc, m in moves.items():
            if not candidate_success.get(loc):
                continue
            occupant = by_loc.get(m.dest.province)
            if not occupant:
                continue
            occ_move = moves.get(occupant.loc)
            occ_leaves = bool(occ_move and candidate_success.get(occupant.loc))
            attacker = by_loc[loc]
            if occupant.power == attacker.power:
                if not occ_leaves:
                    candidate_success[loc] = False
                    stable = False
            else:
                if not occ_leaves and move_strength[loc] <= defense.get(m.dest.province, 1):
                    candidate_success[loc] = False
                    stable = False

    successful_moves = {loc: m for loc, m in moves.items() if candidate_success.get(loc)}
    dislodged: List[Dict[str, Any]] = []

    for loc, m in moves.items():
        strength = move_strength[loc]
        outcome = "succeeds" if loc in successful_moves else "fails"
        log.append(f"- {m.summary()} [{strength}] {outcome}.")

    # Compute post-move unit positions and dislodgements.
    units_after: List[Unit] = []
    for loc, unit in by_loc.items():
        if loc in successful_moves:
            # A unit that successfully moves away is no longer present at its
            # origin to be dislodged by an enemy entering the vacated province.
            # The moving unit will be added at its destination below.
            continue

        incoming = [m for m in successful_moves.values() if m.dest.province == loc]
        if incoming:
            attacker_order = incoming[0]
            attacker_unit = by_loc[attacker_order.origin.province]
            if attacker_unit.power != unit.power:
                # Unit displaced from a province it did not successfully leave.
                retreat_opts = legal_retreats(unit, attacker_order.origin.province, embattled, by_loc, successful_moves)
                dislodged.append({
                    "unit": unit.as_dict(),
                    "from": loc,
                    "attacker_from": attacker_order.origin.province,
                    "options": retreat_opts,
                })
                log.append(f"- {unit.type} {loc} ({POWER_NAMES[unit.power]}) dislodged by {attacker_order.summary()}.")
                continue
            # Own unit entering a space occupied by a friendly unit that failed
            # to leave cannot happen after the fixed-point pass, but leave the
            # guard here for defensive clarity.
        units_after.append(unit)

    for loc, m in successful_moves.items():
        u = by_loc[loc]
        coast = None
        if u.type == "F":
            dest = normalize_dest_for_fleet(u.location(), m.dest)
            coast = dest.coast
        units_after.append(Unit(u.id, u.power, u.type, m.dest.province, coast))

    new_state["units"] = [u.as_dict() for u in sorted(units_after, key=lambda x: (x.power, x.loc, x.id))]
    new_state["pending_retreats"] = [r for r in dislodged if r["options"]]
    auto_disband = [r for r in dislodged if not r["options"]]
    if auto_disband:
        for r in auto_disband:
            u = r["unit"]
            log.append(f"- {u['type']} {r['from']} ({POWER_NAMES[u['power']]}) has no legal retreat and is disbanded.")

    if new_state["pending_retreats"]:
        new_state["phase"] = "RETREAT"
        log.append("")
        log.append("Retreats required.")
    else:
        after_retreat_or_no_retreat(new_state, log)

    return new_state, "\n".join(log).strip()

def legal_retreats(unit: Unit, attacker_from: str, embattled: Set[str], before: Dict[str, Unit], successful_moves: Dict[str, Order]) -> List[str]:
    occupied_after = set()
    for loc, u in before.items():
        if loc in successful_moves:
            continue
        occupied_after.add(loc)
    for m in successful_moves.values():
        occupied_after.add(m.dest.province)

    opts = []
    if unit.type == "A":
        for dest in sorted(ARMY_ADJ.get(unit.loc, set())):
            if dest not in occupied_after and dest != attacker_from and dest not in embattled:
                opts.append(dest)
    else:
        for k in sorted(FLEET_ADJ.get(unit.location().key(), set())):
            dest_loc = Location.from_token(k)
            dest = dest_loc.province
            if dest in SEAS or dest in LAND:
                if dest not in occupied_after and dest != attacker_from and dest not in embattled:
                    opts.append(dest_loc.display())
    return opts

def after_retreat_or_no_retreat(state: Dict[str, Any], log: List[str]) -> None:
    if state["season"] == "Fall":
        update_supply_centers(state, log)
        compute_adjustments(state, log)
        if state.get("pending_adjustments"):
            state["phase"] = "ADJUSTMENT"
        else:
            advance_turn(state)
            state["phase"] = "DIPLOMACY"
    else:
        advance_turn(state)
        state["phase"] = "DIPLOMACY"

def update_supply_centers(state: Dict[str, Any], log: List[str]) -> None:
    occ = units_by_loc(state)
    for sc in sorted(SUPPLY_CENTERS):
        if sc in occ:
            old = state["centers"].get(sc, "in")
            new = occ[sc].power
            if old != new:
                state["centers"][sc] = new
                log.append(f"- Supply center {sc} now controlled by {POWER_NAMES[new]}.")

def compute_adjustments(state: Dict[str, Any], log: List[str]) -> None:
    counts = {p: 0 for p in HOME_CENTERS}
    scs = {p: 0 for p in HOME_CENTERS}
    for u in state["units"]:
        if u["power"] in counts:
            counts[u["power"]] += 1
    for sc, p in state["centers"].items():
        if p in scs:
            scs[p] += 1

    occupied = {u["loc"] for u in state["units"]}
    pending = {}
    for p in HOME_CENTERS:
        diff = scs[p] - counts[p]
        if diff > 0:
            sites = [x for x in HOME_CENTERS[p] if state["centers"].get(x) == p and x not in occupied]
            build_count = min(diff, len(sites))
            if build_count > 0:
                army_sites = list(sites)
                fleet_sites = []
                for site in sites:
                    if site in FLEET_ADJ or site.upper() in FLEET_ADJ:
                        fleet_sites.append(site)
                        if p == "ru" and site == "Stp":
                            fleet_sites.append("STP")
                pending[p] = {
                    "type": "build",
                    "count": build_count,
                    "sites": sites,
                    "build_sites": {"A": army_sites, "F": fleet_sites},
                    "scs": scs[p],
                    "units": counts[p],
                }
                log.append(f"- {POWER_NAMES[p]} may build {build_count} unit(s).")
        elif diff < 0:
            pending[p] = {"type": "disband", "count": -diff, "scs": scs[p], "units": counts[p]}
            log.append(f"- {POWER_NAMES[p]} must disband {-diff} unit(s).")
    state["pending_adjustments"] = pending

def advance_turn(state: Dict[str, Any]) -> None:
    if state["season"] == "Spring":
        state["season"] = "Fall"
    else:
        state["season"] = "Spring"
        state["year"] += 1
    state["orders_text"] = ""
    state["pending_retreats"] = []
    state["pending_adjustments"] = {}

def apply_retreats(state: Dict[str, Any], decisions: Dict[str, str]) -> Tuple[Dict[str, Any], str]:
    new_state = copy.deepcopy(state)
    log = [f"{state['season']} {state['year']} Retreat Resolution", ""]
    retreats = new_state.get("pending_retreats", [])
    if not retreats:
        log.append("No retreats pending.")
        return new_state, "\n".join(log)

    chosen: Dict[str, List[Dict[str, Any]]] = {}
    survivors = [Unit(**u) for u in new_state["units"]]
    for r in retreats:
        u = Unit(**r["unit"])
        choice = decisions.get(u.id, "DISBAND")
        if choice == "DISBAND" or choice not in r["options"]:
            log.append(f"- {u.type} {r['from']} ({POWER_NAMES[u.power]}) disbanded.")
            continue
        chosen.setdefault(choice, []).append(r)

    for dest, rs in chosen.items():
        if len(rs) > 1:
            log.append(f"- Multiple retreats to {dest}; all are disbanded.")
            for r in rs:
                u = r["unit"]
                log.append(f"  - {u['type']} {r['from']} ({POWER_NAMES[u['power']]}) disbanded.")
            continue
        r = rs[0]
        u = Unit(**r["unit"])
        dl = Location.from_token(dest)
        survivors.append(Unit(u.id, u.power, u.type, dl.province, dl.coast if u.type == "F" else None))
        log.append(f"- {u.type} {r['from']} retreats to {dest}.")

    new_state["units"] = [u.as_dict() for u in sorted(survivors, key=lambda x: (x.power, x.loc, x.id))]
    new_state["pending_retreats"] = []
    after_retreat_or_no_retreat(new_state, log)
    return new_state, "\n".join(log).strip()

def apply_adjustments(state: Dict[str, Any], builds: List[Dict[str, str]], disbands: List[str]) -> Tuple[Dict[str, Any], str]:
    new_state = copy.deepcopy(state)
    pending = new_state.get("pending_adjustments", {})
    units = [Unit(**u) for u in new_state["units"]]
    log = [f"{state['season']} {state['year']} Unit Count Adjustment", ""]

    by_id = {u.id: u for u in units}
    occupied = {u.loc for u in units}

    # Disbands
    to_remove = set(disbands)
    for p, adj in pending.items():
        if adj["type"] != "disband":
            continue
        owned = [u for u in units if u.power == p]
        chosen = [uid for uid in disbands if uid in by_id and by_id[uid].power == p]
        if len(chosen) < adj["count"]:
            # deterministic fallback: farthest from home is not computed; remove sorted tail.
            chosen += [u.id for u in sorted(owned, key=lambda x: x.loc) if u.id not in chosen][:adj["count"] - len(chosen)]
        to_remove.update(chosen[:adj["count"]])
    if to_remove:
        kept = []
        for u in units:
            if u.id in to_remove:
                log.append(f"- {POWER_NAMES[u.power]} disbands {u.type} {u.location().display()}.")
                occupied.discard(u.loc)
            else:
                kept.append(u)
        units = kept

    # Builds
    seq = int(new_state.get("unit_seq", 1000))
    builds_by_power: Dict[str, List[Dict[str, str]]] = {}
    for b in builds:
        builds_by_power.setdefault(b.get("power", ""), []).append(b)
    for p, adj in pending.items():
        if adj["type"] != "build":
            continue
        allowed = set(adj["sites"])
        count = 0
        for b in builds_by_power.get(p, []):
            if count >= adj["count"]:
                break
            loc = Location.from_token(b.get("loc", ""))
            utype = b.get("type", "A").upper()
            if loc.province not in allowed or loc.province in occupied:
                log.append(f"- Illegal build ignored for {POWER_NAMES[p]} at {b.get('loc')}.")
                continue
            if utype not in {"A", "F"}:
                continue
            if utype == "F" and loc.province not in FLEET_ADJ and loc.province.upper() not in FLEET_ADJ:
                log.append(f"- Illegal fleet build ignored at landlocked {loc.province}.")
                continue
            seq += 1
            coast = loc.coast if utype == "F" else None
            units.append(Unit(f"u{seq:03d}", p, utype, loc.province, coast))
            occupied.add(loc.province)
            count += 1
            log.append(f"- {POWER_NAMES[p]} builds {utype} {Location(loc.province, coast).display()}.")
        if count < adj["count"]:
            log.append(f"- {POWER_NAMES[p]} forfeits {adj['count'] - count} build(s).")

    new_state["unit_seq"] = seq
    new_state["units"] = [u.as_dict() for u in sorted(units, key=lambda x: (x.power, x.loc, x.id))]
    new_state["pending_adjustments"] = {}
    advance_turn(new_state)
    new_state["phase"] = "DIPLOMACY"
    return new_state, "\n".join(log).strip()

def victory_status(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    counts = {p: 0 for p in HOME_CENTERS}
    for sc, p in state["centers"].items():
        if p in counts:
            counts[p] += 1
    winners = [p for p, n in counts.items() if n >= 18]
    if winners:
        p = winners[0]
        return {"power": p, "name": POWER_NAMES[p], "centers": counts[p]}
    return None


# ---------------------------------------------------------------------------
# SVG mutation
# ---------------------------------------------------------------------------

def turn_label(state: Dict[str, Any]) -> str:
    return f"{state.get('season', 'Spring').upper()} {int(state.get('year', 1901))}"

def render_svg(template_svg: Path, state: Dict[str, Any]) -> str:
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    tree = ET.parse(template_svg)
    root = tree.getroot()

    id_index = {}
    for elem in root.iter():
        eid = elem.attrib.get("id")
        if eid:
            id_index[eid] = elem

    # Board turn label.
    if "turn" in id_index:
        id_index["turn"].text = turn_label(state)

    # Hide all unit positions.
    for eid, elem in id_index.items():
        if "_pos_" in eid:
            elem.set("class", "unoccupied")

    for u in state["units"]:
        unit = Unit(**u)
        cls = f"unit_{unit.power}"
        if unit.type == "A":
            eid = f"{unit.loc}_pos_A"
        else:
            suffix = "Fs" if unit.coast == "s" and unit.loc in SPECIAL_COASTS else "F"
            eid = f"{unit.loc}_pos_{suffix}"
        if eid in id_index:
            id_index[eid].set("class", cls)

    # Supply centers.
    for sc, owner in state.get("centers", {}).items():
        eid = f"{sc}_sc"
        if eid in id_index:
            id_index[eid].set("class", f"unit_{owner}")

    # Optional land-control fill. Only mutate paths inside a province group, and
    # do not overwrite sea/impassable/unusable paths.
    if state.get("settings", {}).get("colour_controlled_land"):
        ns = "{http://www.w3.org/2000/svg}"
        for sc, owner in state.get("centers", {}).items():
            g = id_index.get(sc)
            if g is None:
                continue
            for child in list(g):
                tag = child.tag.split("}")[-1]
                if tag != "path":
                    continue
                klass = child.attrib.get("class", "")
                if klass in {"sea", "impassable", "unusable"}:
                    continue
                child.set("class", f"ctrl_{owner}")

    return ET.tostring(root, encoding="unicode")

def _atomic_write_text(path: Path, text: str) -> None:
    """Write text via same-directory replace to avoid empty/partial files."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    if not raw.strip():
        return None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _atomic_write_json(path: Path, value: Dict[str, Any], *, keep_backup: bool = False) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if keep_backup and path.exists() and path.stat().st_size > 0:
        if _read_json(path) is not None:
            shutil.copy2(path, path.with_name(path.name + ".bak"))
    _atomic_write_text(path, json.dumps(value, indent=2, sort_keys=True))


def write_board(template_svg: Path, state: Dict[str, Any], out_path: Path) -> None:
    _atomic_write_text(out_path, render_svg(template_svg, state))


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class GameStore:
    def __init__(self, root: Path, template_svg: Path):
        self.root = Path(root)
        self.template_svg = Path(template_svg)
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.root / "state.json"
        self.current_svg_path = self.root / "current_board.svg"
        if not self.state_path.exists():
            self.save(initial_state(), snapshot=False)

    def load(self) -> Dict[str, Any]:
        state = _read_json(self.state_path)
        if state is None:
            # This can occur if the dev server is interrupted during a write,
            # or if the browser polls /api/history while state.json is empty.
            # Prefer the last known-good backup; otherwise recreate a clean game.
            state = _read_json(self.state_path.with_name(self.state_path.name + ".bak"))
            if state is None:
                state = initial_state()
            self.save(state, snapshot=False)
            return state

        original = json.dumps(state, sort_keys=True)
        state = normalize_loaded_state(state)
        if json.dumps(state, sort_keys=True) != original:
            self.save(state, snapshot=False)
        return state

    def save(self, state: Dict[str, Any], snapshot: bool = False, orders_text: str = "", log_text: str = "") -> None:
        _atomic_write_json(self.state_path, state, keep_backup=True)
        write_board(self.template_svg, state, self.current_svg_path)
        if snapshot:
            self.snapshot(state, orders_text, log_text)

    def reset(self) -> Dict[str, Any]:
        state = initial_state()
        self.save(state, snapshot=False)
        return state

    def snapshot(self, state: Dict[str, Any], orders_text: str, log_text: str) -> None:
        stamp = f"{state['year']}_{state['season'].lower()}_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        hist_dir = self.root / "history" / stamp
        hist_dir.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(hist_dir / "state.json", state)
        _atomic_write_text(hist_dir / "orders.md", orders_text or state.get("orders_text", ""))
        _atomic_write_text(hist_dir / "log.md", log_text)
        write_board(self.template_svg, state, hist_dir / "board.svg")
        state.setdefault("history", []).append({
            "id": stamp,
            "label": f"{state['season']} {state['year']}",
            "phase": state["phase"],
            "created": _dt.datetime.now().isoformat(timespec="seconds"),
        })
        _atomic_write_json(self.state_path, state, keep_backup=True)

    def history_items(self) -> List[Dict[str, Any]]:
        state = self.load()
        return state.get("history", [])

    def append_log(self, state: Dict[str, Any], text: str) -> None:
        state.setdefault("logs", []).append({
            "turn": f"{state['season']} {state['year']}",
            "phase": state.get("phase", ""),
            "text": text,
            "created": _dt.datetime.now().isoformat(timespec="seconds"),
        })


def state_summary(state: Dict[str, Any]) -> Dict[str, Any]:
    counts = {p: {"units": 0, "centers": 0} for p in HOME_CENTERS}
    for u in state["units"]:
        if u["power"] in counts:
            counts[u["power"]]["units"] += 1
    for sc, p in state["centers"].items():
        if p in counts:
            counts[p]["centers"] += 1
    return {
        "turn": f"{state['season']} {state['year']}",
        "phase": state["phase"],
        "counts": counts,
        "victory": victory_status(state),
    }
