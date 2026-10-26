"""
Module 12: Engineering Intelligence Layer

Detectors for engineering-specific terminology, formulas, units, standards, tables,
and figure references. All processing is offline/CPU-only.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Domain Classification
# ---------------------------------------------------------------------------

class EngineeringDomain(str, Enum):
    CIVIL = "Civil Engineering"
    MECHANICAL = "Mechanical Engineering"
    ELECTRICAL = "Electrical Engineering"
    COMPUTER = "Computer Engineering"
    GENERAL = "General Engineering"


_DOMAIN_KEYWORDS: dict[EngineeringDomain, list[str]] = {
    EngineeringDomain.CIVIL: [
        "beam", "column", "footing", "slab", "foundation", "shear", "bending moment",
        "rebar", "concrete", "steel", "compressive strength", "flexure", "deflection",
        "soil", "retaining wall", "truss", "load factor", "dead load", "live load",
        "seismic", "earthquake", "pile", "geotechnical", "excavation", "reinforcement",
    ],
    EngineeringDomain.MECHANICAL: [
        "torque", "stress", "strain", "fatigue", "fracture", "thermodynamics",
        "fluid dynamics", "viscosity", "heat transfer", "conduction", "convection",
        "radiation", "pressure", "velocity", "turbine", "piston", "shaft",
        "gear", "bearing", "rpm", "power", "efficiency", "combustion",
    ],
    EngineeringDomain.ELECTRICAL: [
        "voltage", "current", "resistance", "capacitance", "inductance", "impedance",
        "ohm", "ampere", "watt", "circuit", "transformer", "rectifier", "diode",
        "transistor", "mosfet", "op-amp", "frequency", "bandwidth", "power factor",
        "load flow", "protection relay", "bus bar",
    ],
    EngineeringDomain.COMPUTER: [
        "algorithm", "data structure", "complexity", "big-o", "binary", "cache",
        "memory", "cpu", "gpu", "network", "protocol", "tcp/ip", "bandwidth",
        "latency", "database", "sql", "compiler", "operating system", "thread",
        "process", "api", "microservice", "kubernetes", "docker",
    ],
}


def detect_domain(text: str) -> EngineeringDomain:
    """Classify text into an engineering domain by keyword frequency."""
    text_lower = text.lower()
    scores: dict[EngineeringDomain, int] = {d: 0 for d in EngineeringDomain}

    for domain, keywords in _DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                scores[domain] += 1

    best = max(scores, key=lambda d: scores[d])
    if scores[best] == 0:
        return EngineeringDomain.GENERAL
    return best


# ---------------------------------------------------------------------------
# 2. Formula Detection
# ---------------------------------------------------------------------------

@dataclass
class DetectedFormula:
    raw: str
    description: Optional[str] = None


# Patterns: lines containing an '=' with surrounding mathematical characters,
# or display-like patterns (numbered equations, Greek letters spelled out).
_FORMULA_PATTERN = re.compile(
    r"""
    (?:(?:eq\.|equation|formula)\s*\(?[\d]+\)?\s*:?\s*)?
    (?:[A-Za-z\u03B1-\u03C9_]+\s*(?:[\^_]{1}\{?[\w\d]+\}?)?\s*)
    (?:[=+\-*/^±≈≤≥])\s*
    (?:[0-9A-Za-z\u03B1-\u03C9\s+\-*/^.()\[\]{}]+)
    """,
    re.VERBOSE | re.MULTILINE
)


def detect_formulas(text: str) -> List[DetectedFormula]:
    """Extract mathematical formulas from engineering text."""
    matches = _FORMULA_PATTERN.findall(text)
    results = [DetectedFormula(raw=m.strip()) for m in matches if len(m.strip()) > 4]
    logger.debug(f"Detected {len(results)} formula(s).")
    return results


# ---------------------------------------------------------------------------
# 3. Standards & Code Detection
# ---------------------------------------------------------------------------

@dataclass
class DetectedStandard:
    raw: str
    standard_type: str  # IS, ASTM, IEEE, ISO, etc.
    code: str


_STANDARDS_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("IS",   re.compile(r"\bIS\s*[:\-]?\s*\d[\d\-:]*\b", re.IGNORECASE)),
    ("ASTM", re.compile(r"\bASTM\s+[A-Z]\d+(?:\s*/\s*[A-Z]\d+M?)?\b", re.IGNORECASE)),
    ("IEEE", re.compile(r"\bIEEE\s+(?:Std\.?\s*)?\d+[\w.\-]*\b", re.IGNORECASE)),
    ("ISO",  re.compile(r"\bISO\s*[\-/]?\s*\d[\d\-:]*\b", re.IGNORECASE)),
    ("IEC",  re.compile(r"\bIEC\s*[\-/]?\s*\d[\d\-:]*\b", re.IGNORECASE)),
]


def detect_standards(text: str) -> List[DetectedStandard]:
    """Extract engineering standards and code references from text."""
    results = []
    for std_type, pattern in _STANDARDS_PATTERNS:
        for match in pattern.finditer(text):
            results.append(DetectedStandard(
                raw=match.group().strip(),
                standard_type=std_type,
                code=match.group().strip()
            ))
    logger.debug(f"Detected {len(results)} standard(s).")
    return results


# ---------------------------------------------------------------------------
# 4. Unit Intelligence
# ---------------------------------------------------------------------------

@dataclass
class DetectedUnit:
    value: str
    unit: str
    raw: str


# Map of unit symbol -> canonical name for display
UNIT_REGISTRY: dict[str, str] = {
    # Force / Pressure
    "N": "Newton", "kN": "Kilonewton", "MN": "Meganewton",
    "Pa": "Pascal", "kPa": "Kilopascal", "MPa": "Megapascal", "GPa": "Gigapascal",
    # Length
    "mm": "Millimeter", "cm": "Centimeter", "m": "Meter", "km": "Kilometer",
    "in": "Inch", "ft": "Feet",
    # Mass / Weight
    "kg": "Kilogram", "g": "Gram", "t": "Tonne", "lb": "Pound",
    # Electrical
    "V": "Volt", "kV": "Kilovolt", "A": "Ampere", "mA": "Milliampere",
    "W": "Watt", "kW": "Kilowatt", "MW": "Megawatt",
    "Ω": "Ohm", "kΩ": "Kilohm", "MΩ": "Megohm",
    "Hz": "Hertz", "kHz": "Kilohertz", "MHz": "Megahertz",
    "F": "Farad", "μF": "Microfarad", "pF": "Picofarad",
    "H": "Henry", "mH": "Millihenry",
    # Temperature
    "°C": "Celsius", "°F": "Fahrenheit", "K": "Kelvin",
    # RPM / Speed
    "rpm": "RPM", "m/s": "Metres/sec", "km/h": "km/h",
}

_UNIT_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(" + "|".join(re.escape(u) for u in UNIT_REGISTRY) + r")\b"
)


def detect_units(text: str) -> List[DetectedUnit]:
    """Extract numeric values with engineering units from text."""
    results = []
    for match in _UNIT_PATTERN.finditer(text):
        results.append(DetectedUnit(
            value=match.group(1),
            unit=UNIT_REGISTRY.get(match.group(2), match.group(2)),
            raw=match.group().strip()
        ))
    logger.debug(f"Detected {len(results)} unit reference(s).")
    return results


def convert_unit(value: float, from_unit: str, to_unit: str) -> Optional[float]:
    """
    Simple unit conversion helper for common engineering units.
    Returns None if the conversion is not supported.
    """
    conversions: dict[tuple[str, str], float] = {
        ("MPa", "kPa"): 1000,
        ("kPa", "MPa"): 0.001,
        ("kN", "N"): 1000,
        ("N", "kN"): 0.001,
        ("m", "mm"): 1000,
        ("mm", "m"): 0.001,
        ("m", "cm"): 100,
        ("cm", "m"): 0.01,
        ("°C", "K"):  lambda v: v + 273.15,
        ("K", "°C"):  lambda v: v - 273.15,
        ("°C", "°F"): lambda v: v * 9/5 + 32,
        ("°F", "°C"): lambda v: (v - 32) * 5/9,
    }
    factor = conversions.get((from_unit, to_unit))
    if factor is None:
        return None
    if callable(factor):
        return factor(value)
    return value * factor


# ---------------------------------------------------------------------------
# 5. Table Detection (Heuristic)
# ---------------------------------------------------------------------------

@dataclass
class DetectedTable:
    raw_text: str
    row_count: int
    column_count: int
    page_number: Optional[int] = None


def detect_tables(text: str, page_number: Optional[int] = None) -> List[DetectedTable]:
    """
    Heuristic table detector. Identifies grid-like structures using
    repeated delimiter characters (|, multiple spaces/tabs) across consecutive lines.
    """
    results = []
    lines = text.splitlines()
    table_lines: List[str] = []
    in_table = False

    for line in lines:
        stripped = line.strip()
        # A "table row" heuristic: 2+ pipe chars OR 2+ tab-separated values
        is_row = stripped.count("|") >= 2 or len(stripped.split("\t")) >= 2 or (
            len(stripped.split("  ")) >= 3 and any(c.isalpha() for c in stripped)
        )

        if is_row:
            in_table = True
            table_lines.append(stripped)
        elif in_table:
            if table_lines:
                # Estimate columns from first row
                first_row = table_lines[0]
                cols = max(
                    len(first_row.split("|")),
                    len(first_row.split("\t")),
                    len(first_row.split("  "))
                )
                results.append(DetectedTable(
                    raw_text="\n".join(table_lines),
                    row_count=len(table_lines),
                    column_count=cols,
                    page_number=page_number
                ))
            table_lines = []
            in_table = False

    if in_table and table_lines:
        first_row = table_lines[0]
        cols = max(
            len(first_row.split("|")),
            len(first_row.split("\t")),
            len(first_row.split("  "))
        )
        results.append(DetectedTable(
            raw_text="\n".join(table_lines),
            row_count=len(table_lines),
            column_count=cols,
            page_number=page_number
        ))

    logger.debug(f"Detected {len(results)} table(s).")
    return results


# ---------------------------------------------------------------------------
# 6. Diagram / Figure Reference Detection
# ---------------------------------------------------------------------------

@dataclass
class DetectedReference:
    raw: str
    ref_type: str   # "figure" | "table" | "appendix" | "equation"
    number: str
    page_hint: Optional[int] = None


_REF_PATTERN = re.compile(
    r"\b(fig(?:ure)?|table|appendix|eq(?:uation)?|plate|diagram)\.?\s*(\d+[a-zA-Z]?(?:\.\d+)?)",
    re.IGNORECASE
)


def detect_references(text: str, page_hint: Optional[int] = None) -> List[DetectedReference]:
    """Detect references to figures, tables, appendices, and equations in text."""
    results = []
    for match in _REF_PATTERN.finditer(text):
        ref_type_raw = match.group(1).lower()
        ref_type = "figure" if "fig" in ref_type_raw or "diagram" in ref_type_raw else ref_type_raw
        results.append(DetectedReference(
            raw=match.group().strip(),
            ref_type=ref_type,
            number=match.group(2),
            page_hint=page_hint
        ))
    logger.debug(f"Detected {len(results)} figure/table reference(s).")
    return results
