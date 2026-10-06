import os
import re
import docx

base = 'archive/outputs'
systems = ['systemA', 'systemB', 'systemc']

def analyze_doc(path):
    doc = docx.Document(path)
    full_text = '\n'.join([p.text for p in doc.paragraphs if p.text.strip()])
    words = len(full_text.split())
    # find bracket citations
    bracket_cits = re.findall(r'\[(?:[0-9]+|[A-Za-z]+(?:\s+et\s+al\.)?,?\s*\d{4})\]', full_text)
    # equations / math symbols
    math_symbols = len(re.findall(r'(\\\w+|[λμαβγδεθσΩΔ]|K_D|Q_\{|R_\{|O\(|\$.*?\$)', full_text))
    # references section
    has_refs = bool(re.search(r'(References|Bibliography|Works Cited)', full_text, re.IGNORECASE))
    drift_words = ['parking', 'social media', 'traffic accident', 'urban mobility']
    drift_found = [w for w in drift_words if w in full_text.lower()]
    
    # Check tables
    num_tables = len(doc.tables)
    
    return {
        'words': words,
        'cits_count': len(bracket_cits),
        'math_density': math_symbols,
        'has_refs': has_refs,
        'tables': num_tables,
        'drift': drift_found,
        'first_100': full_text[:120].replace('\n', ' ')
    }

def main():
    print(f"{'System':<10} | {'Filename':<45} | {'Words':<6} | {'Cits':<5} | {'Math':<5} | {'Tables':<6} | {'Drift/Anomalies'}")
    print("-" * 105)
    for s in systems:
        s_dir = os.path.join(base, s)
        if not os.path.exists(s_dir):
            continue
        for f in sorted(os.listdir(s_dir)):
            if f.endswith('.docx'):
                filepath = os.path.join(s_dir, f)
                res = analyze_doc(filepath)
                drift_str = ", ".join(res['drift']) if res['drift'] else "None"
                print(f"{s:<10} | {f[:45]:<45} | {res['words']:<6} | {res['cits_count']:<5} | {res['math_density']:<5} | {res['tables']:<6} | {drift_str}")

if __name__ == '__main__':
    main()
