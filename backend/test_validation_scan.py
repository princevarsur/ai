"""
Out-of-sample validation test script for THEMIS compliance engine.
Scans the 10-clause Indian IT Company sample policy under the recalibrated 0.58 relevance floor.
"""

import os
import sys
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "themis.settings")
import django
django.setup()

from django.contrib.auth import get_user_model
from policies.models import Policy
from compliance.engine import run_compliance_scan, invalidate_law_cache
from compliance.models import ScanReport, FlaggedIssue

User = get_user_model()

POLICY_TEXT = """INDIAN IT COMPANY - EMPLOYEE POLICY (Sample)
Company Name: ABC Tech Solutions Pvt. Ltd.
Version: 1.0
1. Working Hours  
Employees shall work 8 hours per day and 5 days a week. Any overtime shall be compensated according to applicable state laws and company policy.
2. Equal Employment Opportunity  
The company provides equal employment opportunities without discrimination based on gender, religion, caste, disability, age, or any other protected characteristic under applicable Indian laws.
3. Leave Policy  
Employees are entitled to paid leave, sick leave, and public holidays as prescribed by applicable labour laws and company policy.
4. Workplace Safety  
The company is committed to providing a safe and healthy workplace and will comply with all applicable occupational safety requirements.
5. Prevention of Sexual Harassment  
The company follows the Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013, and maintains an Internal Committee to address complaints.
6. Data Privacy and Confidentiality  
Employees must protect company and customer confidential information and comply with applicable data protection and information security requirements.
7. Performance Management  
Employee performance shall be evaluated fairly using objective business criteria. Performance reviews shall not be discriminatory or retaliatory.
8. Remote Work Policy  
Employees may work remotely with manager approval while complying with company security, attendance, and productivity requirements.
9. Attendance Policy 
Employees who arrive more than 10 minutes late on three occasions in a month may lose one day's attendance incentive. The policy must be applied fairly, proportionately, and in compliance with applicable labour laws.
10. Salary Deduction for Resignation Without Notice 
If an employee resigns without serving the notice period, the company will permanently withhold all earned salary and accrued wages.
End of Policy Document"""

def main():
    user, _ = User.objects.get_or_create(
        username="validation_user",
        defaults={"email": "val@themis.dev", "role": "compliance_officer"},
    )

    filename = "indian_it_policy_validation.txt"
    media_dir = os.path.join(os.path.dirname(__file__), "media", "policies")
    os.makedirs(media_dir, exist_ok=True)
    dest_path = os.path.join(media_dir, filename)

    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(POLICY_TEXT)

    policy, _ = Policy.objects.get_or_create(
        title="[VALIDATION] Indian IT Company Employee Policy",
        uploaded_by=user,
        defaults={
            "file": f"policies/{filename}",
            "category": "general",
            "extracted_text": POLICY_TEXT,
            "file_type": "txt",
            "clause_count": 10,
        },
    )
    policy.extracted_text = POLICY_TEXT
    policy.file = f"policies/{filename}"
    policy.save(update_fields=["extracted_text", "file"])

    invalidate_law_cache()

    print("=" * 75)
    print("EXECUTING OUT-OF-SAMPLE VALIDATION SCAN (Relevance Floor = 0.58)")
    print("=" * 75)

    report = run_compliance_scan(policy.id, user)
    issues = FlaggedIssue.objects.filter(report=report)

    status_counts = {}
    for issue in issues:
        s = issue.status.upper()
        status_counts[s] = status_counts.get(s, 0) + 1

    print("\n" + "=" * 75)
    print("SCAN SUMMARY")
    print("=" * 75)
    print(f"Overall Score:     {report.overall_score:.1f}%")
    print(f"Risk Level:        {report.risk_level.upper()}")
    print(f"Total Clauses:     {report.total_clauses}")
    print(f"Compliant Clauses: {report.compliant_clauses}")
    print(f"Flagged Issues:    {report.flagged_clauses}")
    print(f"Scan Duration:     {report.scan_duration_seconds:.2f}s")

    print("\nSTATUS BREAKDOWN:")
    for status_label in ["MISSING", "CONFLICT", "GAP"]:
        count = status_counts.get(status_label, 0)
        print(f"  {status_label:<12}: {count}")
    print(f"  {'TOTAL':<12}: {sum(status_counts.values())}")

    print("\n" + "=" * 75)
    print("DETAILED ISSUE BREAKDOWN")
    print("=" * 75)
    for issue in issues:
        clause_preview = issue.clause_text[:110].replace("\n", " ")
        print(f"[{issue.status.upper():<8}] Sev={issue.severity_score:>3} | Rule: {issue.legal_rule.law_name} {issue.legal_rule.section}")
        print(f"  Matched Clause: \"{clause_preview}\"")
        print(f"  Explanation: {issue.description[:140]}...")
        print("-" * 75)

if __name__ == "__main__":
    main()
