package com.example.ragengi.data.model

data class EngineeringAnnotation(
    val domain: String,
    val formulas: List<String> = emptyList(),
    val standards: List<String> = emptyList(),
    val units: List<String> = emptyList(),
    val figureReferences: List<String> = emptyList()
)

data class EngineeringAnswer(
    val rawAnswer: String,
    val domain: String,
    val technicalSummary: String,
    val formulas: List<String> = emptyList(),
    val standards: List<String> = emptyList(),
    val units: List<String> = emptyList(),
    val figureReferences: List<String> = emptyList(),
    val citations: List<Citation> = emptyList()
)
