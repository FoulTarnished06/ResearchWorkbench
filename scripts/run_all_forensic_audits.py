import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import glob
from evals.forensic_audit import audit_document

def main():
    files = sorted(glob.glob('archive/outputs/*/*.docx'))
    if os.path.exists('report/forensic_verified/Recursive_zero-knowledge_rollup_proof_ve_systemA_CORRECTED.docx'):
        files.append('report/forensic_verified/Recursive_zero-knowledge_rollup_proof_ve_systemA_CORRECTED.docx')

    print(f"Auditing {len(files)} files...\n")
    results = []
    for f in files:
        res = audit_document(f)
        sys_name = os.path.basename(os.path.dirname(f)) if 'forensic_verified' not in f else 'System A (Upgraded)'
        results.append({
            'sys': sys_name,
            'file': os.path.basename(f),
            'score': res['score_percent'],
            'passed': res['passed_checks'],
            'total': res['total_checks'],
            'all_passed': res['all_passed'],
            'details': res['checks']
        })

    print(f"{'SYSTEM':<22} | {'SCORE':<7} | {'CHECKS':<8} | {'FILE'}")
    print("-" * 95)
    for r in results:
        status = "[PASS]" if r['all_passed'] else "[FAIL]"
        print(f"{r['sys']:<22} | {r['score']}% | {r['passed']}/{r['total']} {status:<6} | {r['file']}")
        
    print("\n" + "=" * 95)
    print("SYSTEM SUMMARY AVERAGES:")
    print("=" * 95)
    by_sys = {}
    for r in results:
        by_sys.setdefault(r['sys'], []).append(r['score'])
    for sys_name, scores in by_sys.items():
        avg = sum(scores) / len(scores)
        print(f"  * {sys_name:<22}: Average Forensic Score = {avg:.1f}% ({len(scores)} documents)")

if __name__ == '__main__':
    main()
