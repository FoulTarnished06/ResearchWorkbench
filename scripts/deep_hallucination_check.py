import os
import re
import docx

def extract_doc_data(filepath):
    doc = docx.Document(filepath)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    full_text = "\n".join(paragraphs)
    words = len(full_text.split())
    
    # Extract headings
    headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading") or (len(p.text) < 80 and re.match(r'^\d+\.', p.text))]
    
    # Extract citations
    bracket_cits = re.findall(r'\[(?:[0-9]+|[A-Za-z]+(?:\s+et\s+al\.)?,?\s*\d{4})\]', full_text)
    
    # Extract bibliography
    refs = []
    in_refs = False
    for p in paragraphs:
        if re.match(r'^(References|Bibliography|Works Cited|Sources)', p, re.I):
            in_refs = True
            continue
        if in_refs:
            refs.append(p)
            
    # Check tables
    tables_count = len(doc.tables)
    
    return {
        "text": full_text,
        "paragraphs": paragraphs,
        "words": words,
        "headings": headings,
        "citations": bracket_cits,
        "refs": refs,
        "tables_count": tables_count
    }

def main():
    base = "archive/outputs"
    systems = ["systemA", "systemB", "systemc"]
    
    # Prompts mapping
    prompts = {
        "Neural_Hawkes": {
            "title": "Neural Hawkes Processes vs Deep Transformers for LOB",
            "files": {
                "systemA": "Neural_Hawkes_processes_vs_deep_transformer_systemA.docx",
                "systemB": "Neural_Hawkes_processes_vs_deep_transformer_systemb.docx",
                "systemc": "Neural_Hawkes_processes_vs_deep_transformer_systemc.docx"
            }
        },
        "Recursive_zk": {
            "title": "Recursive ZK-Rollup Proof Verification vs Optimistic Dispute Windows",
            "files": {
                "systemA": "Recursive_zero-knowledge_rollup_proof_ve_systema.docx",
                "systemB": "Recursive_zero-knowledge_rollup_proof_ve_systemB.docx",
                "systemc": "Recursive_zero-knowledge_rollup_proof_ve_systemC.docx"
            }
        },
        "CBDC": {
            "title": "CBDC Two-Tier Architecture: Quantity Caps vs Wholesale Settlement",
            "files": {
                "systemA": "Central_bank_digital_currency_two-tier_a_systemA.docx",
                "systemB": "Central_bank_digital_currency_two-tier_a_systemB.docx",
                "systemc": "Central_bank_digital_currency_two-tier_a_systemC.docx"
            }
        },
        "PROTAC": {
            "title": "PROTAC Ternary Complex Thermodynamics vs Molecular Glues",
            "files": {
                "systemA": "PROTAC_ternary_complex_thermodynamic_sta_systemA.docx",
                "systemB": "PROTAC_ternary_complex_thermodynamic_sta_systemB.docx",
                "systemc": "PROTAC_ternary_complex_thermodynamic_sta_systemC.docx"
            }
        },
        "Cu_Cu_bonding": {
            "title": "Direct Cu-Cu Hybrid Bonding vs Micro-Bump CoWoS Interposers",
            "files": {
                "systemA": "Direct_copper-to-copper_dielectric_hybri_systemA.docx",
                "systemB": "Direct_copper-to-copper_dielectric_hybri_systemB.docx",
                "systemc": "Direct_copper-to-copper_dielectric_hybri_systemC.docx"
            }
        },
        "Solid_Oxide": {
            "title": "High-Temperature Solid Oxide Electrolysis vs PEM",
            "files": {
                "systemA": "High-temperature_solid_oxide_electrolysi_systemA.docx",
                "systemB": "High-temperature_solid_oxide_electrolysi_systemB.docx",
                "systemc": "High-temperature_solid_oxide_electrolysi_systemC.docx"
            }
        }
    }
    
    with open("scripts/detailed_eval_dump.txt", "w", encoding="utf-8") as out:
        for pkey, pinfo in prompts.items():
            out.write(f"\n{'='*90}\nTOPIC: {pinfo['title']}\n{'='*90}\n")
            for sys_name, fname in pinfo["files"].items():
                fpath = os.path.join(base, sys_name, fname)
                if not os.path.exists(fpath):
                    out.write(f"System: {sys_name} - File {fname} not found!\n")
                    continue
                d = extract_doc_data(fpath)
                out.write(f"\n--- {sys_name.upper()} ({fname}) ---\n")
                out.write(f"Word count: {d['words']} | Paragraphs: {len(d['paragraphs'])} | Tables: {d['tables_count']}\n")
                out.write(f"Citations count: {len(d['citations'])} | References count: {len(d['refs'])}\n")
                out.write(f"Headings: {d['headings'][:6]}\n")
                # Sample text from first 2 paragraphs and middle paragraph
                out.write("First 200 chars:\n" + d['text'][:200].replace('\n', ' ') + "\n")
                if len(d['paragraphs']) > 5:
                    out.write("Mid paragraph excerpt:\n" + d['paragraphs'][len(d['paragraphs'])//2][:250] + "\n")
    print("Detailed eval dump written to scripts/detailed_eval_dump.txt")

if __name__ == '__main__':
    main()
