"""
OCR pipeline service for the renewable energy PDF processing pipeline.

This module provides OCR processing capabilities using ocrmypdf + Tesseract (default)
with AWS Textract as a feature flag option. Handles scanned PDFs and generates
is_ocr_generated flags for content.
"""

import asyncio
import logging
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF for PDF analysis
from pydantic import BaseModel, Field

from ..config.settings import settings

logger = logging.getLogger(__name__)


class OCRError(Exception):
    """Base exception for OCR operations."""
    
    def __init__(self, message: str, error_type: str = "ocr_error", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_type = error_type
        self.details = details or {}
        super().__init__(message)


class ProcessingError(OCRError):
    """Exception raised when OCR processing fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "processing_error", details)


class ValidationError(OCRError):
    """Exception raised when OCR validation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "validation_error", details)


class TextBlock(BaseModel):
    """Represents a block of text extracted via OCR with confidence and location."""
    
    page_number: int = Field(..., description="Page number in document", gt=0)
    text: str = Field(..., description="Extracted text content", min_length=1)
    confidence_score: float = Field(..., description="OCR confidence score", ge=0.0, le=1.0)
    bounding_box: Dict[str, float] = Field(
        ..., description="Bounding box coordinates {x0, y0, x1, y1}"
    )
    language: str = Field(default="eng", description="Detected language code")


class OCRResult(BaseModel):
    """Result of OCR processing operation."""
    
    success: bool = Field(..., description="Whether OCR processing succeeded")
    confidence_avg: float = Field(..., description="Average confidence across all text blocks", ge=0.0, le=1.0)
    pages_processed: int = Field(..., description="Number of pages processed", ge=0)
    text_blocks: List[TextBlock] = Field(default_factory=list, description="Extracted text blocks with metadata")
    processing_time: float = Field(..., description="Processing time in seconds", ge=0.0)
    error_message: Optional[str] = Field(default=None, description="Error message if processing failed")


class OCRService:
    """OCR pipeline service using ocrmypdf + Tesseract with optional AWS Textract."""
    
    def __init__(self):
        self.ocr_engine = settings.ocr_engine
        self.tesseract_language = settings.tesseract_language
        self.confidence_threshold = settings.ocr_confidence_threshold
        
    async def detect_scanned_content(self, pdf_path: str) -> bool:
        """
        Determine if PDF needs OCR processing by analyzing text content.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            True if PDF appears to be scanned and needs OCR, False otherwise
            
        Raises:
            ValidationError: If PDF file is invalid or unreadable
        """
        try:
            pdf_path_obj = Path(pdf_path)
            if not pdf_path_obj.exists():
                raise ValidationError(f"PDF file not found: {pdf_path}")
                
            # Use PyMuPDF to analyze text content
            doc = fitz.open(pdf_path)
            
            if len(doc) == 0:
                raise ValidationError("PDF document has no pages")
                
            total_text_length = 0
            total_pages = len(doc)
            
            # Sample first 10 pages or all pages if less than 10
            sample_pages = min(10, total_pages)
            
            for page_num in range(sample_pages):
                page = doc[page_num]
                text = page.get_text()
                total_text_length += len(text.strip())
                
            doc.close()
            
            # Heuristic: If average text per page is very low, likely scanned
            avg_text_per_page = total_text_length / sample_pages
            needs_ocr = avg_text_per_page < 100  # Less than 100 chars per page
            
            logger.info(
                f"PDF analysis: {total_pages} pages, avg {avg_text_per_page:.1f} chars/page, "
                f"needs_ocr={needs_ocr}"
            )
            
            return needs_ocr
            
        except Exception as e:
            if isinstance(e, OCRError):
                raise
            raise ValidationError(f"Failed to analyze PDF: {str(e)}")
    
    async def process_with_ocr(self, pdf_path: str, output_path: str) -> OCRResult:
        """
        Process PDF with OCR and return detailed results.
        
        Args:
            pdf_path: Input PDF file path
            output_path: Output PDF file path with OCR text layer
            
        Returns:
            OCRResult with processing details and extracted text blocks
            
        Raises:
            ProcessingError: If OCR processing fails
            ValidationError: If input parameters are invalid
        """
        start_time = time.time()
        
        try:
            # Validate inputs
            input_path = Path(pdf_path)
            if not input_path.exists():
                raise ValidationError(f"Input PDF not found: {pdf_path}")
                
            output_path_obj = Path(output_path)
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            if self.ocr_engine == "tesseract":
                result = await self._process_with_tesseract(pdf_path, output_path)
            elif self.ocr_engine == "textract":
                result = await self._process_with_textract(pdf_path, output_path)
            else:
                raise ValidationError(f"Unsupported OCR engine: {self.ocr_engine}")
                
            processing_time = time.time() - start_time
            result.processing_time = processing_time
            
            logger.info(
                f"OCR completed: {result.pages_processed} pages, "
                f"avg confidence {result.confidence_avg:.3f}, "
                f"time {processing_time:.2f}s"
            )
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            if isinstance(e, OCRError):
                raise
            raise ProcessingError(
                f"OCR processing failed: {str(e)}",
                details={"processing_time": processing_time}
            )
    
    async def _process_with_tesseract(self, pdf_path: str, output_path: str) -> OCRResult:
        """Process PDF using ocrmypdf + Tesseract."""
        try:
            # Run ocrmypdf command
            cmd = [
                "ocrmypdf",
                "--language", self.tesseract_language,
                "--output-type", "pdf",
                "--optimize", "1",
                "--jpeg-quality", "95",
                "--force-ocr",
                pdf_path,
                output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown OCR error"
                raise ProcessingError(f"ocrmypdf failed: {error_msg}")
                
            # Extract text blocks with confidence scores
            text_blocks = await self._extract_text_blocks_tesseract(output_path)
            
            # Calculate metrics
            if text_blocks:
                confidence_avg = sum(block.confidence_score for block in text_blocks) / len(text_blocks)
                pages_processed = max(block.page_number for block in text_blocks)
            else:
                confidence_avg = 0.0
                pages_processed = 0
                
            return OCRResult(
                success=True,
                confidence_avg=confidence_avg,
                pages_processed=pages_processed,
                text_blocks=text_blocks,
                processing_time=0.0  # Will be set by caller
            )
            
        except Exception as e:
            if isinstance(e, OCRError):
                raise
            raise ProcessingError(f"Tesseract OCR failed: {str(e)}")
    
    async def _process_with_textract(self, pdf_path: str, output_path: str) -> OCRResult:
        """Process PDF using AWS Textract (feature flag implementation)."""
        # Placeholder for future AWS Textract integration
        # For now, fall back to Tesseract
        logger.warning("Textract not yet implemented, falling back to Tesseract")
        return await self._process_with_tesseract(pdf_path, output_path)
    
    async def _extract_text_blocks_tesseract(self, pdf_path: str) -> List[TextBlock]:
        """Extract text blocks with confidence scores from OCR'd PDF."""
        text_blocks = []
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Get text blocks with bounding boxes
                text_dict = page.get_text("dict")
                
                for block in text_dict.get("blocks", []):
                    if "lines" not in block:
                        continue
                        
                    for line in block["lines"]:
                        line_text = ""
                        line_bbox = line.get("bbox", [0, 0, 0, 0])
                        
                        for span in line.get("spans", []):
                            line_text += span.get("text", "")
                            
                        if line_text.strip():
                            # Estimate confidence based on text characteristics
                            # This is a heuristic since PyMuPDF doesn't provide OCR confidence
                            confidence = self._estimate_confidence(line_text)
                            
                            text_block = TextBlock(
                                page_number=page_num + 1,
                                text=line_text.strip(),
                                confidence_score=confidence,
                                bounding_box={
                                    "x0": line_bbox[0],
                                    "y0": line_bbox[1], 
                                    "x1": line_bbox[2],
                                    "y1": line_bbox[3]
                                },
                                language=self.tesseract_language
                            )
                            text_blocks.append(text_block)
                            
            doc.close()
            return text_blocks
            
        except Exception as e:
            logger.error(f"Failed to extract text blocks: {str(e)}")
            return []
    
    def _estimate_confidence(self, text: str) -> float:
        """Estimate OCR confidence based on text characteristics."""
        if not text.strip():
            return 0.0
            
        # Simple heuristics for confidence estimation
        confidence = 0.8  # Base confidence
        
        # Adjust based on text characteristics
        alpha_ratio = sum(c.isalpha() for c in text) / len(text)
        digit_ratio = sum(c.isdigit() for c in text) / len(text)
        space_ratio = sum(c.isspace() for c in text) / len(text)
        special_ratio = sum(not c.isalnum() and not c.isspace() for c in text) / len(text)
        
        # Higher confidence for more alphabetic characters
        confidence += alpha_ratio * 0.15
        
        # Lower confidence for too many special characters
        confidence -= special_ratio * 0.3
        
        # Ensure confidence is within bounds
        return max(0.0, min(1.0, confidence))
    
    async def extract_text_with_confidence(self, pdf_path: str) -> List[TextBlock]:
        """
        Extract text blocks with confidence scores from PDF.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of TextBlock objects with confidence scores
            
        Raises:
            ValidationError: If PDF file is invalid
            ProcessingError: If text extraction fails
        """
        try:
            if not Path(pdf_path).exists():
                raise ValidationError(f"PDF file not found: {pdf_path}")
                
            # Check if OCR is needed
            needs_ocr = await self.detect_scanned_content(pdf_path)
            
            if needs_ocr:
                # Process with OCR first
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                    temp_output = tmp_file.name
                    
                try:
                    result = await self.process_with_ocr(pdf_path, temp_output)
                    return result.text_blocks
                finally:
                    Path(temp_output).unlink(missing_ok=True)
            else:
                # Extract text directly
                return await self._extract_text_blocks_tesseract(pdf_path)
                
        except Exception as e:
            if isinstance(e, OCRError):
                raise
            raise ProcessingError(f"Text extraction failed: {str(e)}")
    
    async def get_ocr_confidence_metrics(self, pdf_path: str) -> float:
        """
        Get average OCR confidence for a PDF.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Average confidence score (0.0 to 1.0)
            
        Raises:
            ValidationError: If PDF file is invalid
            ProcessingError: If confidence calculation fails
        """
        try:
            text_blocks = await self.extract_text_with_confidence(pdf_path)
            
            if not text_blocks:
                return 0.0
                
            total_confidence = sum(block.confidence_score for block in text_blocks)
            return total_confidence / len(text_blocks)
            
        except Exception as e:
            if isinstance(e, OCRError):
                raise
            raise ProcessingError(f"Confidence calculation failed: {str(e)}")
    
    async def enhance_pdf_text(self, input_path: str, output_path: str) -> bool:
        """
        Enhance PDF with OCR text layer if needed.
        
        Args:
            input_path: Source PDF file path
            output_path: Enhanced PDF output path
            
        Returns:
            True if enhancement was applied, False if not needed
            
        Raises:
            ValidationError: If input parameters are invalid
            ProcessingError: If enhancement fails
        """
        try:
            if not Path(input_path).exists():
                raise ValidationError(f"Input PDF not found: {input_path}")
                
            # Check if OCR is needed
            needs_ocr = await self.detect_scanned_content(input_path)
            
            if needs_ocr:
                # Apply OCR enhancement
                result = await self.process_with_ocr(input_path, output_path)
                return result.success
            else:
                # Copy file without OCR
                import shutil
                shutil.copy2(input_path, output_path)
                logger.info(f"PDF already has text content, copied without OCR: {output_path}")
                return False
                
        except Exception as e:
            if isinstance(e, OCRError):
                raise
            raise ProcessingError(f"PDF enhancement failed: {str(e)}")


# Global OCR service instance
ocr_service = OCRService()