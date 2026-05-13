"""
CSV / Excel Loader — uses pandas to read tabular data.
Each sheet / file is converted to a Markdown table chunk plus a text
description of the data schema and statistics.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd

from loaders.base_loader import BaseLoader
from models.document import DocumentChunk, Modality, SourceType


class CSVLoader(BaseLoader):
    """Load .csv, .tsv, .xlsx, .xls files as table + schema chunks."""

    async def load(self, source: str, **kwargs) -> List[DocumentChunk]:
        path = Path(source)
        ext = path.suffix.lower()
        chunks: List[DocumentChunk] = []
        source_name = path.name

        if ext in {".xlsx", ".xls"}:
            xf = pd.ExcelFile(str(path))
            for sheet_name in xf.sheet_names:
                df = xf.parse(sheet_name)
                chunks.extend(self._df_to_chunks(df, str(path), source_name, sheet_name))
        else:
            sep = "\t" if ext == ".tsv" else ","
            df = pd.read_csv(str(path), sep=sep, on_bad_lines="warn")
            chunks.extend(self._df_to_chunks(df, str(path), source_name, "Sheet1"))

        return chunks

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _df_to_chunks(
        df: pd.DataFrame, source_id: str, source_name: str, sheet: str
    ) -> List[DocumentChunk]:
        if df.empty:
            return []
        chunks: List[DocumentChunk] = []

        # Schema + stats description
        schema_lines = [f"Sheet: {sheet}", f"Rows: {len(df)}, Columns: {len(df.columns)}"]
        schema_lines.append("Columns: " + ", ".join(df.columns.tolist()))
        desc = df.describe(include="all").to_string()
        schema_lines.append(f"\nStatistics:\n{desc}")

        chunks.append(
            DocumentChunk(
                content="\n".join(schema_lines),
                modality=Modality.TEXT,
                source_type=SourceType.CSV,
                source_id=source_id,
                source_name=source_name,
                metadata={"sheet": sheet, "chunk_type": "schema"},
            )
        )

        # Table in markdown (split into 50-row pages to avoid huge chunks)
        page_size = 50
        for page_idx, start in enumerate(range(0, len(df), page_size)):
            chunk_df = df.iloc[start : start + page_size]
            md = chunk_df.to_markdown(index=False)
            if md:
                chunks.append(
                    DocumentChunk(
                        content=md,
                        modality=Modality.TABLE,
                        source_type=SourceType.CSV,
                        source_id=source_id,
                        source_name=source_name,
                        page_number=page_idx + 1,
                        metadata={"sheet": sheet, "row_start": start},
                    )
                )
        return chunks
