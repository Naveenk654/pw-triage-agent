"""Knowledge base parsing and chunking utility."""

import os
import re
import yaml
from typing import List
from src.models import KBChunk


def load_and_chunk_kb(kb_dir: str) -> List[KBChunk]:
    """
    Parses markdown policy documents into distinct section-level chunks.
    Extracts numbered sections and common questions accurately.
    """
    chunks: List[KBChunk] = []
    
    if not os.path.exists(kb_dir):
        raise FileNotFoundError(f"Knowledge base directory '{kb_dir}' not found.")
        
    for fname in sorted(os.listdir(kb_dir)):
        if not fname.endswith(".md"):
            continue
            
        fpath = os.path.join(kb_dir, fname)
        doc_name = fname[:-3]
        
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
            
        metadata = {}
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    metadata = yaml.safe_load(parts[1]) or {}
                except Exception:
                    pass
                content = parts[2].strip()
            
        # Match ## Header pattern
        sections = re.split(r"\n(?=##\s+)", content)
        
        for idx, sec in enumerate(sections):
            sec_str = sec.strip()
            if not sec_str or sec_str.startswith("# Policy:") or sec_str.startswith("# SAMPLE"):
                continue
                
            lines = sec_str.split("\n", 1)
            header_line = lines[0].replace("##", "").strip()
            body_text = lines[1].strip() if len(lines) > 1 else ""
            
            chunk_id = f"{doc_name}_sec_{idx}"
            full_chunk_text = f"[{doc_name.upper()} - {header_line}]\n{body_text}"
            
            chunks.append(
                KBChunk(
                    chunk_id=chunk_id,
                    document=doc_name,
                    section_title=header_line,
                    section_index=idx,
                    content=full_chunk_text,
                    metadata=metadata,
                )
            )
            
    return chunks
