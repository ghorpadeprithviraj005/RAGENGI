import pytest
from app.intelligence.detectors import (
    detect_domain, EngineeringDomain,
    detect_formulas, detect_standards, detect_units,
    detect_tables, detect_references, convert_unit,
)
from app.intelligence.analyzer import EngineeringAnalyzer
from app.intelligence.formatter import EngineeringFormatter, EngineeringAnswer

# ──────────────────────────────────────────────
# 1. Domain Detection Tests
# ──────────────────────────────────────────────

def test_detect_civil_domain():
    text = "The concrete beam has a bending moment of 150 kNm and shear force of 75 kN."
    assert detect_domain(text) == EngineeringDomain.CIVIL

def test_detect_mechanical_domain():
    text = "The turbine shaft experiences high torque and fatigue due to cyclic stress."
    assert detect_domain(text) == EngineeringDomain.MECHANICAL

def test_detect_electrical_domain():
    text = "The transformer has a voltage ratio of 11kV/415V with a power factor of 0.85."
    assert detect_domain(text) == EngineeringDomain.ELECTRICAL

def test_detect_computer_domain():
    text = "The algorithm runs in O(n log n) time and uses a binary search tree data structure."
    assert detect_domain(text) == EngineeringDomain.COMPUTER

def test_detect_general_domain():
    text = "This document is an overview."
    assert detect_domain(text) == EngineeringDomain.GENERAL

# ──────────────────────────────────────────────
# 2. Formula Detection Tests
# ──────────────────────────────────────────────

def test_detect_formula_basic_equation():
    text = "The bending moment is calculated as M = F * L / 4"
    formulas = detect_formulas(text)
    assert any("M" in f.raw and "=" in f.raw for f in formulas)

def test_detect_formula_empty_text():
    assert detect_formulas("") == []

def test_detect_formula_no_match():
    assert detect_formulas("This is a plain sentence with no equations.") == []

# ──────────────────────────────────────────────
# 3. Standards Detection Tests
# ──────────────────────────────────────────────

def test_detect_is_code():
    text = "Design per IS 456:2000 for reinforced concrete structures."
    standards = detect_standards(text)
    assert any(s.standard_type == "IS" for s in standards)

def test_detect_astm_code():
    text = "Material tested as per ASTM A615 for deformed steel bars."
    standards = detect_standards(text)
    assert any(s.standard_type == "ASTM" for s in standards)

def test_detect_ieee_code():
    text = "Protection scheme follows IEEE Std 242 for industrial installations."
    standards = detect_standards(text)
    assert any(s.standard_type == "IEEE" for s in standards)

def test_detect_iso_code():
    text = "Quality management as per ISO 9001:2015 standards."
    standards = detect_standards(text)
    assert any(s.standard_type == "ISO" for s in standards)

# ──────────────────────────────────────────────
# 4. Unit Intelligence Tests
# ──────────────────────────────────────────────

def test_detect_units_mpa():
    text = "Compressive strength is 25 MPa."
    units = detect_units(text)
    assert any(u.unit == "Megapascal" for u in units)

def test_detect_units_voltage():
    text = "Supply voltage of 415 V at 50 Hz."
    units = detect_units(text)
    unit_names = [u.unit for u in units]
    assert "Volt" in unit_names or "Hertz" in unit_names

def test_unit_conversion_mpa_to_kpa():
    result = convert_unit(25.0, "MPa", "kPa")
    assert result == pytest.approx(25000.0)

def test_unit_conversion_celsius_to_kelvin():
    result = convert_unit(100.0, "°C", "K")
    assert result == pytest.approx(373.15)

def test_unit_conversion_unsupported():
    assert convert_unit(10.0, "MPa", "°C") is None

# ──────────────────────────────────────────────
# 5. Table Detection Tests
# ──────────────────────────────────────────────

def test_detect_pipe_table():
    text = "| Member | Force (kN) | Stress (MPa) |\n| A | 100 | 25 |\n| B | 200 | 50 |\n"
    tables = detect_tables(text)
    assert len(tables) >= 1

def test_detect_no_table():
    text = "This is a regular paragraph with no tabular data."
    assert detect_tables(text) == []

# ──────────────────────────────────────────────
# 6. Reference Detection Tests
# ──────────────────────────────────────────────

def test_detect_figure_reference():
    text = "As shown in Figure 3.2, the stress distribution is parabolic."
    refs = detect_references(text)
    assert any(r.ref_type == "figure" and r.number == "3.2" for r in refs)

def test_detect_table_reference():
    text = "Refer to Table 5 for the load combinations."
    refs = detect_references(text)
    assert any(r.ref_type == "table" for r in refs)

# ──────────────────────────────────────────────
# 7. Analyzer Integration Test
# ──────────────────────────────────────────────

def test_analyzer_full_integration():
    text = (
        "The reinforced concrete beam is designed as per IS 456:2000. "
        "The bending moment formula is M = W * L^2 / 8. "
        "The maximum stress is 25 MPa. See Figure 2 for the cross-section details."
    )
    analyzer = EngineeringAnalyzer()
    annotation = analyzer.analyze(text, page_number=5)

    assert annotation.domain == EngineeringDomain.CIVIL
    assert len(annotation.standards) >= 1
    assert len(annotation.units) >= 1
    assert len(annotation.references) >= 1

def test_analyzer_empty_text():
    analyzer = EngineeringAnalyzer()
    annotation = analyzer.analyze("  ")
    assert annotation.domain == EngineeringDomain.GENERAL

# ──────────────────────────────────────────────
# 8. Formatter Tests
# ──────────────────────────────────────────────

def test_formatter_builds_answer():
    from app.intelligence.analyzer import EngineeringAnnotation
    from app.intelligence.detectors import DetectedStandard, DetectedUnit, DetectedFormula

    annotation = EngineeringAnnotation(
        domain=EngineeringDomain.CIVIL,
        formulas=[DetectedFormula(raw="M = W * L^2 / 8")],
        standards=[DetectedStandard(raw="IS 456:2000", standard_type="IS", code="IS 456:2000")],
        units=[DetectedUnit(value="25", unit="Megapascal", raw="25 MPa")],
        tables=[],
        references=[]
    )

    formatter = EngineeringFormatter()
    answer = formatter.format_answer(
        raw_answer="The beam should be designed for a BM of 150 kNm.",
        annotations=[annotation],
        citations=[{"chunk_id": 1, "page_number": 5, "document_name": "IS_456_Guide.pdf"}],
    )

    assert answer.domain == EngineeringDomain.CIVIL
    assert "M = W * L^2 / 8" in answer.formulas
    assert "IS: IS 456:2000" in answer.standards
    assert "25 Megapascal" in answer.units
    assert len(answer.citations) == 1

def test_formatter_no_annotations():
    formatter = EngineeringFormatter()
    answer = formatter.format_answer(raw_answer="Some answer.", annotations=[])
    assert answer.domain == EngineeringDomain.GENERAL
    assert answer.technical_summary == "Some answer."
