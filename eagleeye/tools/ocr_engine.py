"""
OCR Engine - EasyOCR wrapper for scanned document processing.
"""

from typing import Optional
from pathlib import Path
from loguru import logger
import numpy as np

# Lazy imports to save memory
_reader: Optional["easyocr.Reader"] = None


def get_ocr_reader(languages: list[str] = None, gpu: bool = False) -> "easyocr.Reader":
    """
    Get or create OCR reader (singleton for memory efficiency).

    Args:
        languages: List of language codes (default: ['ch_sim', 'en'])
        gpu: Whether to use GPU (default: False for Mac Mini)

    Returns:
        EasyOCR Reader instance
    """
    global _reader

    if _reader is None:
        import easyocr
        languages = languages or ["ch_sim", "en"]
        logger.info(f"Initializing EasyOCR with languages: {languages}, GPU: {gpu}")
        _reader = easyocr.Reader(languages, gpu=gpu)

    return _reader


class OCREngine:
    """
    EasyOCR-based text extraction for scanned PDFs.
    Optimized for Chinese financial documents.
    """

    def __init__(
        self,
        languages: list[str] = None,
        gpu: bool = False
    ):
        """
        Initialize OCR engine.

        Args:
            languages: OCR language codes
            gpu: Use GPU acceleration
        """
        self.languages = languages or ["ch_sim", "en"]
        self.gpu = gpu
        self._reader = None

    @property
    def reader(self):
        """Lazy load OCR reader."""
        if self._reader is None:
            self._reader = get_ocr_reader(self.languages, self.gpu)
        return self._reader

    def extract_text_from_image(
        self,
        image: np.ndarray | str | Path,
        detail: int = 0
    ) -> str:
        """
        Extract text from a single image.

        Args:
            image: Image as numpy array or file path
            detail: 0 for text only, 1 for boxes and confidence

        Returns:
            Extracted text string
        """
        logger.debug(f"OCR processing image")

        try:
            if isinstance(image, (str, Path)):
                image = str(image)

            results = self.reader.readtext(image, detail=detail)

            if detail == 0:
                return "\n".join(results)
            else:
                # Extract text from detailed results
                return "\n".join([r[1] for r in results])

        except Exception as e:
            logger.error(f"OCR extraction error: {e}")
            return ""

    def extract_text_from_images(
        self,
        images: list[np.ndarray | str | Path]
    ) -> list[str]:
        """
        Extract text from multiple images.

        Args:
            images: List of images

        Returns:
            List of extracted text strings
        """
        results = []
        for i, image in enumerate(images):
            logger.info(f"OCR processing image {i + 1}/{len(images)}")
            text = self.extract_text_from_image(image)
            results.append(text)
        return results

    def extract_structured_text(
        self,
        image: np.ndarray | str | Path
    ) -> list[dict]:
        """
        Extract text with bounding boxes and confidence scores.

        Args:
            image: Input image

        Returns:
            List of dicts with 'text', 'bbox', 'confidence'
        """
        if isinstance(image, (str, Path)):
            image = str(image)

        try:
            results = self.reader.readtext(image, detail=1)

            structured = []
            for bbox, text, confidence in results:
                structured.append({
                    "text": text,
                    "bbox": bbox,
                    "confidence": confidence
                })

            return structured

        except Exception as e:
            logger.error(f"Structured OCR error: {e}")
            return []

    def extract_table_regions(
        self,
        image: np.ndarray,
        min_confidence: float = 0.5
    ) -> list[dict]:
        """
        Extract text organized by spatial regions (for table detection).

        Args:
            image: Input image as numpy array
            min_confidence: Minimum confidence threshold

        Returns:
            List of text regions with positions
        """
        structured = self.extract_structured_text(image)

        # Filter by confidence
        filtered = [
            item for item in structured
            if item["confidence"] >= min_confidence
        ]

        # Sort by vertical position (top to bottom)
        filtered.sort(key=lambda x: x["bbox"][0][1])

        return filtered

    def pdf_page_to_text(
        self,
        pdf_path: str | Path,
        page_number: int,
        dpi: int = 200
    ) -> str:
        """
        Convert a single PDF page to text via OCR.

        Args:
            pdf_path: Path to PDF file
            page_number: Page number (0-indexed)
            dpi: Resolution for conversion

        Returns:
            Extracted text
        """
        from pdf2image import convert_from_path

        logger.debug(f"Converting PDF page {page_number} to image (DPI: {dpi})")

        try:
            images = convert_from_path(
                str(pdf_path),
                first_page=page_number + 1,
                last_page=page_number + 1,
                dpi=dpi
            )

            if images:
                # Convert PIL Image to numpy array
                image_array = np.array(images[0])
                return self.extract_text_from_image(image_array)

            return ""

        except Exception as e:
            logger.error(f"PDF to OCR error: {e}")
            return ""
