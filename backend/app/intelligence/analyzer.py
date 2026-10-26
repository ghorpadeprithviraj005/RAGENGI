"""
Module 12: Engineering Intelligence Layer

EngineeringAnalyzer orchestrates all detectors against a single chunk of text,
returning a rich EngineeringAnnotation that can be stored alongside the chunk
metadata and surfaced to the answer formatter.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from app.intelligence.detectors import (
    DetectedFormula,
    DetectedReference,
    DetectedStandard,
    DetectedTable,
    DetectedUnit,
    EngineeringDomain,
    detect_domain,
    detect_formulas,
    detect_references,
    detect_standards,
    detect_tables,
    detect_units,
)

logger = logging.getLogger(__name__)


@dataclass
class EngineeringAnnotation:
    """All engineering intelligence extracted from a single chunk of text."""
    domain: EngineeringDomain
    formulas: List[DetectedFormula] = field(default_factory=list)
    standards: List[DetectedStandard] = field(default_factory=list)
    units: List[DetectedUnit] = field(default_factory=list)
    tables: List[DetectedTable] = field(default_factory=list)
    references: List[DetectedReference] = field(default_factory=list)


class EngineeringAnalyzer:
    """
    Runs the full suite of engineering intelligence extractors against text.
    Designed to be called once per chunk during the ingestion pipeline.
    Fully offline and CPU-only.
    """

    def analyze(self, text: str, page_number: Optional[int] = None) -> EngineeringAnnotation:
        """
        Analyze a text chunk and return an EngineeringAnnotation.

        Args:
            text: The raw text content of the chunk.
            page_number: Optional page number, used to add context to tables and references.

        Returns:
            EngineeringAnnotation with all detected entities.
        """
        if not text or not text.strip():
            logger.warning("Empty text passed to EngineeringAnalyzer. Returning default annotation.")
            return EngineeringAnnotation(domain=EngineeringDomain.GENERAL)

        try:
            annotation = EngineeringAnnotation(
                domain=detect_domain(text),
                formulas=detect_formulas(text),
                standards=detect_standards(text),
                units=detect_units(text),
                tables=detect_tables(text, page_number=page_number),
                references=detect_references(text, page_hint=page_number),
            )
            logger.debug(
                f"Analysis complete | Domain: {annotation.domain.value} | "
                f"Formulas: {len(annotation.formulas)} | Standards: {len(annotation.standards)} | "
                f"Units: {len(annotation.units)} | Tables: {len(annotation.tables)} | "
                f"References: {len(annotation.references)}"
            )
            return annotation
        except Exception as e:
            logger.error(f"EngineeringAnalyzer failed: {e}")
            raise
