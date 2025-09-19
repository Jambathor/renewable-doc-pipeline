"""
OCR processing pipeline for renewable energy PDF documents.

This package provides OCR capabilities using ocrmypdf and Tesseract,
with support for confidence scoring and AWS Textract integration.

Components:
    OCRService: Main OCR processing pipeline
    TextBlock: Extracted text with confidence and positioning data
    OCRResult: Complete OCR processing results with metrics

The OCR pipeline detects scanned content, applies OCR when needed,
and generates confidence scores for quality metrics tracking.
"""

from .ocr_service import OCRService, OCRResult, TextBlock, OCRError

__all__ = [
    "OCRService",
    "OCRResult", 
    "TextBlock",
    "OCRError",
]