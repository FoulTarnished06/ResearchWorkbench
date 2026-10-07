"""
Concept Decomposer Module (Tier 1 Retrieval Innovation)
Deconstructs complex, multi-faceted research queries into distinct sub-questions
and entity-specific queries for isolated retrieval across academic repositories.
"""

import re
from typing import List, Dict, Any, Optional

def decompose_research_query(query: str) -> List[Dict[str, Any]]:
    """
    Deconstructs a complex comparative or multi-faceted academic query into
    atomic sub-concepts for targeted per-concept retrieval.
    
    Returns a list of structured concept descriptors:
    [
      {
        "id": "concept_1",
        "category": "architecture_a",
        "label": "Architecture A",
        "query_string": "Spatial Message Passing Neural Networks edge-conditioned convolutions",
        "focus_terms": ["MPNN", "message passing", "edge-conditioned"]
      },
      ...
    ]
    """
    clean_q = query.strip()
    concepts: List[Dict[str, Any]] = []

    # Check for comparative format "A vs B" or "A versus B"
    vs_match = re.search(r'^(.*?)\s+(?:vs\.?|versus|compared to)\s+(.*?)(?::\s*(.*))?$', clean_q, re.IGNORECASE)
    
    if vs_match:
        part_a = vs_match.group(1).strip()
        rest = vs_match.group(2).strip()
        mechanisms_and_benchmarks = vs_match.group(3).strip() if vs_match.group(3) else ""
        
        # In rest, there might be "for <task>: <mechanisms>"
        part_b = rest
        task_context = ""
        for_match = re.search(r'^(.*?)\s+for\s+(.*?)$', rest, re.IGNORECASE)
        if for_match:
            part_b = for_match.group(1).strip()
            task_context = for_match.group(2).strip()

        # Concept 1: Subject / Architecture A
        query_a = f"{part_a} {task_context}".strip()
        concepts.append({
            "id": "concept_arch_a",
            "category": "architecture_a",
            "label": f"Subject A ({part_a[:40]})",
            "query_string": query_a,
            "focus_terms": [w for w in re.findall(r'[A-Za-z0-9\-]+', part_a) if len(w) > 2]
        })

        # Concept 2: Subject / Architecture B
        query_b = f"{part_b} {task_context}".strip()
        concepts.append({
            "id": "concept_arch_b",
            "category": "architecture_b",
            "label": f"Subject B ({part_b[:40]})",
            "query_string": query_b,
            "focus_terms": [w for w in re.findall(r'[A-Za-z0-9\-]+', part_b) if len(w) > 2]
        })

        # Split mechanisms and benchmarks if present
        details = []
        if mechanisms_and_benchmarks:
            details.extend([d.strip() for d in re.split(r'[,;]|\band\b', mechanisms_and_benchmarks) if d.strip()])
        elif task_context:
            details.append(task_context)

        # Distribute into mechanism and benchmark concepts
        mech_parts = []
        bench_parts = []
        for d in details:
            if re.search(r'benchmark|dataset|qm9|zinc|imagenet|glue|squad|eval|scaling|inference', d, re.IGNORECASE):
                bench_parts.append(d)
            else:
                mech_parts.append(d)

        if mech_parts:
            mech_query = " ".join(mech_parts)
            concepts.append({
                "id": "concept_mechanism",
                "category": "theoretical_mechanism",
                "label": "Theoretical Mechanisms",
                "query_string": f"{mech_query} {task_context}".strip(),
                "focus_terms": [w for w in re.findall(r'[A-Za-z0-9\-]+', mech_query) if len(w) > 2]
            })

        if bench_parts:
            bench_query = " ".join(bench_parts)
            concepts.append({
                "id": "concept_benchmark",
                "category": "empirical_benchmark",
                "label": "Empirical Benchmarks & Scaling",
                "query_string": f"{bench_query} {part_a.split()[0]} {part_b.split()[0]}".strip(),
                "focus_terms": [w for w in re.findall(r'[A-Za-z0-9\-]+', bench_query) if len(w) > 2]
            })

    else:
        # Non-comparative query: split by clauses or punctuation
        clauses = [c.strip() for c in re.split(r'[:;]|\bwith\b|\band\b', clean_q) if len(c.strip()) > 8]
        if len(clauses) >= 2:
            for i, clause in enumerate(clauses[:4]):
                concepts.append({
                    "id": f"concept_{i+1}",
                    "category": "topic_facet",
                    "label": f"Facet {i+1}: {clause[:30]}",
                    "query_string": clause,
                    "focus_terms": [w for w in re.findall(r'[A-Za-z0-9\-]+', clause) if len(w) > 3]
                })
        else:
            # Fallback to single primary concept + refined keywords
            keywords = [w for w in re.findall(r'[A-Za-z0-9\-]+', clean_q) if len(w) > 3]
            concepts.append({
                "id": "concept_primary",
                "category": "primary_domain",
                "label": "Primary Inquiry",
                "query_string": clean_q,
                "focus_terms": keywords[:6]
            })

    # Always ensure at least 2 distinct search facets if query is complex
    if len(concepts) < 2 and len(clean_q.split()) > 5:
        half = len(clean_q.split()) // 2
        words = clean_q.split()
        concepts.append({
            "id": "concept_secondary",
            "category": "complementary_facet",
            "label": "Complementary Sub-domain",
            "query_string": " ".join(words[half:]),
            "focus_terms": words[half:]
        })

    return concepts
