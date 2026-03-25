from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.datamodel.base_models import InputFormat
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from collections import defaultdict

class DoclingExtractor:
    def __init__(self):
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False
        pipeline_options.images_scale = 1.0
        pipeline_options.generate_page_images = False
        pipeline_options.generate_picture_images = False
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
        pipeline_options.table_structure_options.do_cell_matching = True

        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,
                    backend=PyPdfiumDocumentBackend,
                )
            }
        )

    def _page_text_from_docling(self, doc) -> dict[int, str]:
        from docling_core.types.doc.document import TableItem, PictureItem
        page_texts: dict[int, list[str]] = defaultdict(list)
        for item, _level in doc.iterate_items():
            if not hasattr(item, "prov") or not item.prov:
                continue
            page_no = item.prov[0].page_no  
            if isinstance(item, TableItem):
                md = item.export_to_markdown()
                if md:
                    page_texts[page_no].append(md)
            elif isinstance(item, PictureItem):
                pass
            else:
                text = getattr(item, "text", "") or ""
                if text.strip():
                    page_texts[page_no].append(text)
        return {pno: "\n".join(parts) for pno, parts in page_texts.items()}

    def extract_pages(self, pdf_path: str) -> dict[int, str]:
        conv_result = self.converter.convert(pdf_path)
        return self._page_text_from_docling(conv_result.document)
    
docling_extractor = DoclingExtractor()