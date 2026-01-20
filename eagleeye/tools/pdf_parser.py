"""
PDF Parser - Dual-track parsing with pdfplumber and OCR fallback.
"""

from typing import Optional
from pathlib import Path
from loguru import logger
import pdfplumber

import sys
sys.path.insert(0, str(__file__).rsplit("\\", 3)[0])

from config.settings import settings
from eagleeye.tools.ocr_engine import OCREngine
from eagleeye.models.document import Document, TableData, FinancialData


class PDFParser:
    """
    Hybrid PDF parser with automatic detection of digital vs scanned documents.
    Uses pdfplumber for digital PDFs and EasyOCR for scanned documents.
    """

    def __init__(
        self,
        text_density_threshold: int = None,
        ocr_languages: list[str] = None,
        ocr_gpu: bool = None,
        dpi: int = None
    ):
        """
        Initialize PDF parser.

        Args:
            text_density_threshold: Chars per page to consider digital
            ocr_languages: Languages for OCR
            ocr_gpu: Use GPU for OCR
            dpi: DPI for PDF to image conversion
        """
        self.text_density_threshold = text_density_threshold or settings.pdf.text_density_threshold
        self.ocr_languages = ocr_languages or settings.pdf.ocr_languages
        self.ocr_gpu = ocr_gpu if ocr_gpu is not None else settings.pdf.ocr_gpu
        self.dpi = dpi or settings.pdf.dpi

        self._ocr_engine: Optional[OCREngine] = None

    @property
    def ocr_engine(self) -> OCREngine:
        """Lazy load OCR engine."""
        if self._ocr_engine is None:
            self._ocr_engine = OCREngine(
                languages=self.ocr_languages,
                gpu=self.ocr_gpu
            )
        return self._ocr_engine

    def parse(self, pdf_path: str | Path) -> Document:
        """
        Parse a PDF file and extract content.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Parsed Document object
        """
        pdf_path = Path(pdf_path)
        logger.info(f"Parsing PDF: {pdf_path.name}")

        # Try digital extraction first
        is_digital, total_pages, sample_text = self._detect_pdf_type(pdf_path)

        if is_digital:
            logger.info("Detected digital PDF, using pdfplumber")
            return self._parse_digital(pdf_path, total_pages)
        else:
            logger.info("Detected scanned PDF, using OCR")
            return self._parse_scanned(pdf_path, total_pages)

    def _detect_pdf_type(self, pdf_path: Path) -> tuple[bool, int, str]:
        """
        Detect if PDF is digital (text-based) or scanned (image-based).

        Returns:
            (is_digital, total_pages, sample_text)
        """
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)

            # Sample first few pages
            sample_pages = min(3, total_pages)
            total_chars = 0
            sample_text = ""

            for i in range(sample_pages):
                text = pdf.pages[i].extract_text() or ""
                total_chars += len(text)
                sample_text += text + "\n"

            avg_density = total_chars / sample_pages if sample_pages > 0 else 0
            is_digital = avg_density >= self.text_density_threshold

            logger.debug(f"PDF detection: pages={total_pages}, avg_density={avg_density:.0f}, is_digital={is_digital}")

            return is_digital, total_pages, sample_text

    def _parse_digital(self, pdf_path: Path, total_pages: int) -> Document:
        """Parse digital PDF using pdfplumber."""
        all_text = []
        all_tables = []

        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Extract text
                text = page.extract_text() or ""
                all_text.append(text)

                # Extract tables
                tables = page.extract_tables()
                for table_idx, table in enumerate(tables):
                    if table and len(table) > 0:
                        # First row as headers if it looks like headers
                        headers = table[0] if table else []
                        rows = table[1:] if len(table) > 1 else []

                        table_data = TableData(
                            page_number=page_num,
                            table_index=table_idx,
                            headers=[str(h) if h else "" for h in headers],
                            rows=[[str(c) if c else "" for c in row] for row in rows],
                            raw_text=str(table)
                        )
                        all_tables.append(table_data)

        raw_text = "\n\n".join(all_text)

        doc = Document(
            file_path=str(pdf_path),
            file_name=pdf_path.name,
            total_pages=total_pages,
            parse_method="pdfplumber",
            raw_text=raw_text,
            tables=all_tables
        )

        # Extract financial data from tables
        doc.financial_data = self._extract_financial_data(doc)

        return doc

    def _parse_scanned(self, pdf_path: Path, total_pages: int) -> Document:
        """Parse scanned PDF using OCR."""
        from pdf2image import convert_from_path
        import numpy as np

        all_text = []

        try:
            # Convert all pages to images
            logger.info(f"Converting {total_pages} pages to images...")
            images = convert_from_path(str(pdf_path), dpi=self.dpi)

            for page_num, image in enumerate(images):
                logger.info(f"OCR processing page {page_num + 1}/{total_pages}")
                image_array = np.array(image)
                text = self.ocr_engine.extract_text_from_image(image_array)
                all_text.append(text)

        except Exception as e:
            logger.error(f"OCR parsing error: {e}")

        raw_text = "\n\n".join(all_text)

        doc = Document(
            file_path=str(pdf_path),
            file_name=pdf_path.name,
            total_pages=total_pages,
            parse_method="ocr",
            raw_text=raw_text,
            tables=[]  # OCR doesn't extract structured tables
        )

        # Extract financial data from text
        doc.financial_data = self._extract_financial_data(doc)

        return doc

    def _extract_financial_data(self, doc: Document) -> FinancialData:
        """
        Extract financial data from document content.
        Uses pattern matching and table parsing.
        """
        financial_data = FinancialData()

        # Extract from tables first
        for table in doc.tables:
            self._extract_from_table(table, financial_data)

        # Extract from raw text using patterns
        self._extract_from_text(doc.raw_text, financial_data)

        return financial_data

    def _extract_from_table(self, table: TableData, data: FinancialData):
        """Extract financial values from a table."""
        import re

        def parse_number(value: str) -> Optional[float]:
            """Parse a number from string, handling Chinese notation."""
            if not value:
                return None
            # Remove commas, spaces, and convert Chinese units
            value = value.strip().replace(",", "").replace(" ", "")
            value = value.replace("万", "0000").replace("亿", "00000000")

            try:
                # Handle parentheses for negative numbers
                if value.startswith("(") and value.endswith(")"):
                    value = "-" + value[1:-1]
                return float(value)
            except ValueError:
                return None

        # Map common row labels to fields
        field_mapping = {
            "货币资金": "货币资金",
            "应收账款": "应收账款",
            "其他应收款": "其他应收款",
            "预付账款": "预付账款",
            "存货": "存货",
            "在建工程": "在建工程",
            "固定资产": "固定资产",
            "无形资产": "无形资产",
            "资产总计": "资产总额",
            "资产合计": "资产总额",
            "短期借款": "短期借款",
            "长期借款": "长期借款",
            "应付债券": "应付债券",
            "一年内到期的非流动负债": "一年内到期的非流动负债",
            "其他应付款": "其他应付款",
            "递延收益": "递延收益_期末",
            "所有者权益合计": "净资产",
            "净资产": "净资产",
            "营业收入": "营业收入",
            "营业成本": "营业成本",
            "财务费用": "财务费用_利息支出",
            "政府补助": "营业外收入_政府补助",
            "利润总额": "利润总额",
            "净利润": "净利润",
            "经营活动产生的现金流量净额": "经营活动现金流量净额",
            "投资活动产生的现金流量净额": "投资活动现金流出",
        }

        for row in table.rows:
            if len(row) >= 2:
                label = row[0].strip() if row[0] else ""
                value_str = row[-1].strip() if row[-1] else ""

                # Check if label matches any known field
                for pattern, field_name in field_mapping.items():
                    if pattern in label:
                        value = parse_number(value_str)
                        if value is not None and hasattr(data, field_name):
                            setattr(data, field_name, value)
                        break

    def _extract_from_text(self, text: str, data: FinancialData):
        """Extract financial values from raw text using patterns."""
        import re

        # Pattern for Chinese currency amounts
        patterns = [
            (r"货币资金[：:\s]*([0-9,.]+)\s*(?:万|元|亿)?", "货币资金"),
            (r"资产负债率[：:\s]*([0-9.]+)\s*%?", "资产负债率"),
            (r"净资产收益率[：:\s]*([0-9.]+)\s*%?", "净资产收益率_ROE"),
            (r"存货周转率[：:\s]*([0-9.]+)", "存货周转率"),
        ]

        for pattern, field_name in patterns:
            match = re.search(pattern, text)
            if match and hasattr(data, field_name):
                try:
                    value = float(match.group(1).replace(",", ""))
                    # Convert percentage to decimal if needed
                    if "率" in field_name and value > 1:
                        value = value / 100
                    setattr(data, field_name, value)
                except ValueError:
                    pass

    def extract_text_only(self, pdf_path: str | Path) -> str:
        """
        Quick text extraction without full parsing.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Raw text content
        """
        pdf_path = Path(pdf_path)

        with pdfplumber.open(pdf_path) as pdf:
            texts = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                texts.append(text)

            combined = "\n\n".join(texts)

            # Fall back to OCR if no text found
            if len(combined.strip()) < self.text_density_threshold * len(pdf.pages):
                logger.info("Insufficient text, falling back to OCR")
                doc = self._parse_scanned(pdf_path, len(pdf.pages))
                return doc.raw_text

            return combined
