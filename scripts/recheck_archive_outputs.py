import os
import re
import docx

base_dir = r"archive/outputs"

# Let's map topic keys
topics = [
    ("Neural_Hawkes", "Neural Hawkes vs Transformers LOB"),
    ("Recursive_zero-knowledge", "Recursive ZK-Rollup vs Optimistic Dispute Windows"),
    ("Central_bank_digital_currency", "CBDC Two-Tier Architecture"),
    ("PROTAC_ternary_complex", "PROTAC Ternary Complex vs Molecular Glues"),
    ("Direct_copper-to-copper", "Direct Cu-Cu Hybrid Bonding vs CoWoS"),
    ("High-temperature_solid_oxide", "High-Temperature Solid Oxide Electrolysis"),
    ("Amine-functionalized", "Amine-Functionalized Solid Sorbents"),
    ("Deterministic_transactional", "Deterministic Transactional Execution Engines"),
    ("Dielectric_barrier_discharge", "Dielectric Barrier Discharge Plasma Actuators")
]

def get_text_and_stats(filepath):
    doc = docx.Document(filepath)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    full_text = "\n".join(paragraphs)
    words = len(full_text.split())
    
    # Extract references
    refs = []
    in_refs = False
    for p in paragraphs:
        if re.match(r'^(References|Bibliography|Works Cited|Sources)', p, re.I):
            in_refs = True
            continue
        if in_refs:
            refs.append(p)
            
    # Extract bracket citations [1], [Author 2024], etc.
    citations = re.findall(r'\[(?:[0-9]+|[A-Za-z]+(?:\s+et\s+al\.)?,?\s*\d{4})\]', full_text)
    
    # Specific hallucination / drift patterns
    drift_patterns = {
        "parking": bool(re.search(r'\bparking\b', full_text, re.I)),
        "social_media": bool(re.search(r'\bsocial media\b', full_text, re.I)),
        "patient_care": bool(re.search(r'\bpatient[- ]care\b', full_text, re.I)),
        "fabricated_cbdc_crisis_data": bool(re.search(r'(empirical crisis data demonstrates|crisis stress-test data confirms|during the \d{4} bank run crisis)', full_text, re.I)),
        "phantom_citations": bool(re.search(r'\[(?:1|2|3|4|5)\]', full_text)) and len(refs) == 0,
        "collapsed_stub": words < 150
    }
    
    return {
        "words": words,
        "paragraphs_count": len(paragraphs),
        "citations_count": len(citations),
        "references_count": len(refs),
        "references": refs[:5],
        "drift_patterns": drift_patterns,
        "tables_count": len(doc.tables),
        "sample_start": full_text[:300].replace("\n", " "),
        "sample_end": full_text[-300:].replace("\n", " ") if len(full_text) > 300 else ""
    }

def run_recheck():
    results = {}
    for sys_name in ["systemA", "systemB", "systemc"]:
        s_dir = os.path.join(base_dir, sys_name)
        if not os.path.exists(s_dir):
            continue
        results[sys_name] = {}
        for f in sorted(os.listdir(s_dir)):
            if f.endswith(".docx"):
                path = os.path.join(s_dir, f)
                data = get_text_and_stats(path)
                results[sys_name][f] = data
                
    with open("scripts/recheck_summary.txt", "w", encoding="utf-8") as out:
        for sys_name, files in results.items():
            out.write(f"\n{'='*80}\nSYSTEM: {sys_name}\n{'='*80}\n")
            for fname, d in files.items():
                out.write(f"\n--- {fname} ---\n")
                out.write(f"Words: {d['words']} | Paras: {d['paragraphs_count']} | Citations: {d['citations_count']} | Refs: {d['references_count']} | Tables: {d['tables_count']}\n")
                out.write(f"Drift/Flags: {d['drift_patterns']}\n")
                out.write(f"Start: {d['sample_start']}...\n")
                if d['references']:
                    out.write(f"Sample Refs ({len(d['references'])} total):\n")
                    for r in d['references'][:3]:
                        out.write(f"  * {r[:100]}\n")
    print("Recheck summary written to scripts/recheck_summary.txt")

if __name__ == "__main__":
    run_recheck()
