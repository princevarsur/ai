"""
Management command to seed the LegalRule database with Indian law requirements.

Usage:
    python manage.py seed_laws          # Upsert all rules (idempotent)
    python manage.py seed_laws --clear  # Wipe existing rules first, then seed
"""

from django.core.management.base import BaseCommand
from laws.models import LegalRule


SEED_DATA = [
    # ─────────────────────────────────────────────────────────────────────
    # 1. POSH Act, 2013 — Workplace Safety
    # ─────────────────────────────────────────────────────────────────────
    {
        "law_name": "POSH Act, 2013",
        "section": "Section 4",
        "category": "workplace_safety",
        "requirement_text": (
            "Every employer with 10 or more employees must constitute an "
            "Internal Complaints Committee (ICC) with a Presiding Officer, "
            "employee members, and an external member."
        ),
        "keywords_regex": r"(internal complaints? committee|ICC|complaints? committee|presiding officer)",
        "severity_weight": 10,
        "template_fix": (
            "The Company has constituted an Internal Complaints Committee (ICC) "
            "under the Sexual Harassment of Women at Workplace (Prevention, "
            "Prohibition, and Redressal) Act, 2013. The ICC comprises a "
            "Presiding Officer who is a senior woman employee, not less than "
            "two employee members committed to the cause of women, and one "
            "external member from an NGO or association. Complaints may be "
            "filed within 3 months of the incident."
        ),
    },
    {
        "law_name": "POSH Act, 2013",
        "section": "Section 19",
        "category": "workplace_safety",
        "requirement_text": (
            "The employer must organize regular awareness programmes and "
            "workshops to sensitize employees about the provisions of the "
            "Act and the right to a harassment-free workplace."
        ),
        "keywords_regex": r"(awareness program|workshop|training.*sexual harassment|posh training|sensitization)",
        "severity_weight": 7,
        "template_fix": (
            "The Company shall conduct mandatory POSH awareness workshops for "
            "all employees on a semi-annual basis. New joiners shall complete "
            "sensitization training within 30 days of onboarding. Records of "
            "attendance and training content shall be maintained by the HR "
            "department for a minimum of three years."
        ),
    },
    {
        "law_name": "POSH Act, 2013",
        "section": "Section 4(1)(c)",
        "category": "workplace_safety",
        "requirement_text": (
            "The ICC must include at least one external member from a "
            "non-governmental organization or association committed to the "
            "cause of women."
        ),
        "keywords_regex": r"(external member|NGO|non.?governmental|women.?s? (organization|association))",
        "severity_weight": 8,
        "template_fix": (
            "The Internal Complaints Committee shall include an external "
            "member nominated from a registered NGO or women's organization "
            "with demonstrable experience in handling sexual harassment "
            "matters. The appointment shall be reviewed annually and renewed "
            "or replaced as necessary."
        ),
    },
    {
        "law_name": "POSH Act, 2013",
        "section": "Section 13",
        "category": "workplace_safety",
        "requirement_text": (
            "The inquiry into a complaint must be completed within 90 days, "
            "and the employer must act on the ICC recommendations within "
            "60 days of receiving the report."
        ),
        "keywords_regex": r"(60 days|sixty days|time.?bound|inquiry.*complete)",
        "severity_weight": 8,
        "template_fix": (
            "Upon receipt of a formal complaint, the ICC shall complete its "
            "inquiry within 90 days. The employer shall implement the "
            "recommendations of the ICC within 60 days of receiving the "
            "inquiry report. Failure to act within the stipulated period "
            "shall be escalated to the Managing Director."
        ),
    },

    # ─────────────────────────────────────────────────────────────────────
    # 2. DPDP Act, 2023 — Data Privacy
    # ─────────────────────────────────────────────────────────────────────
    {
        "law_name": "DPDP Act, 2023",
        "section": "Section 6",
        "category": "data_privacy",
        "requirement_text": (
            "Personal data shall be processed only after obtaining free, "
            "specific, informed, and unambiguous consent from the Data "
            "Principal for a specified purpose."
        ),
        "keywords_regex": r"(explicit consent|informed consent|data principal.*consent|freely given.*consent|consent.*purpose)",
        "severity_weight": 10,
        "template_fix": (
            "The Company shall obtain explicit, informed, and freely given "
            "consent from every Data Principal prior to the collection or "
            "processing of their personal data. Consent notices shall clearly "
            "state the purpose, scope, and duration of processing. Data "
            "Principals may withdraw consent at any time through a "
            "documented mechanism."
        ),
    },
    {
        "law_name": "DPDP Act, 2023",
        "section": "Section 12",
        "category": "data_privacy",
        "requirement_text": (
            "Personal data collected for a specified purpose shall not be "
            "processed for any other purpose without fresh consent from the "
            "Data Principal (purpose limitation)."
        ),
        "keywords_regex": r"(purpose limitation|specified purpose|data.*purpose|lawful purpose)",
        "severity_weight": 9,
        "template_fix": (
            "All personal data collected by the Company shall be processed "
            "solely for the specific, lawful purpose communicated to the "
            "Data Principal at the time of collection. Any secondary usage "
            "shall require fresh, explicit consent and shall be documented "
            "in the Company's data processing register."
        ),
    },
    {
        "law_name": "DPDP Act, 2023",
        "section": "Section 13",
        "category": "data_privacy",
        "requirement_text": (
            "The Data Principal has the right to request erasure of their "
            "personal data once the specified purpose has been fulfilled or "
            "consent is withdrawn (right to be forgotten)."
        ),
        "keywords_regex": r"(data erasure|right to (be )?forgotten|delete.*data|erasure request|data deletion)",
        "severity_weight": 9,
        "template_fix": (
            "Data Principals may submit a request for erasure of their "
            "personal data when the purpose for processing is no longer "
            "applicable or consent has been withdrawn. The Company shall "
            "process such requests within 30 days and confirm deletion in "
            "writing, unless retention is required by law."
        ),
    },
    {
        "law_name": "DPDP Act, 2023",
        "section": "Section 8",
        "category": "data_privacy",
        "requirement_text": (
            "Data Principals have the right to access their personal data, "
            "request correction of inaccurate data, and file grievances "
            "with the Data Fiduciary."
        ),
        "keywords_regex": r"(data principal.*rights|right to access|right to correct|grievance redressal|data.*grievance)",
        "severity_weight": 8,
        "template_fix": (
            "The Company recognizes the rights of Data Principals to access "
            "their personal data held by the Company, to request correction "
            "of inaccurate or incomplete data, and to file grievances with "
            "the designated Grievance Officer. Requests shall be addressed "
            "within 15 business days."
        ),
    },
    {
        "law_name": "DPDP Act, 2023",
        "section": "Section 10",
        "category": "data_privacy",
        "requirement_text": (
            "The Data Fiduciary must notify the Data Protection Board and "
            "affected Data Principals of any personal data breach without "
            "unreasonable delay."
        ),
        "keywords_regex": r"(data breach.*notif|breach notification|report.*breach|inform.*breach|security incident)",
        "severity_weight": 9,
        "template_fix": (
            "In the event of a personal data breach, the Company shall "
            "notify the Data Protection Board of India and all affected "
            "Data Principals within 72 hours of becoming aware of the "
            "breach. The notification shall include the nature and extent "
            "of the breach, data compromised, and remedial measures taken."
        ),
    },

    # ─────────────────────────────────────────────────────────────────────
    # 3. Maternity Benefit Act, 2017 Amendment — Employee Benefits
    # ─────────────────────────────────────────────────────────────────────
    {
        "law_name": "Maternity Benefit Act, 2017 Amendment",
        "section": "Section 5(3)",
        "category": "employee_benefits",
        "requirement_text": (
            "Every female employee who has worked for at least 80 days in "
            "the preceding 12 months is entitled to 26 weeks of paid "
            "maternity leave for the first two children, and 12 weeks for "
            "subsequent children."
        ),
        "keywords_regex": r"(26 weeks|twenty.?six weeks|maternity.*leave.*26|maternity benefit.*26)",
        "severity_weight": 10,
        "required_value": 26.0,
        "required_unit": "weeks",
        "comparison_type": "min",
        "template_fix": (
            "Every female employee who has worked for at least 80 days in "
            "the 12 months preceding the expected delivery date is entitled "
            "to maternity benefit of 26 weeks of paid leave for the first "
            "two children, and 12 weeks for subsequent children, in "
            "accordance with the Maternity Benefit (Amendment) Act, 2017."
        ),
    },
    {
        "law_name": "Maternity Benefit Act, 2017 Amendment",
        "section": "Section 11A",
        "category": "employee_benefits",
        "requirement_text": (
            "Every establishment with 50 or more employees shall provide "
            "a crèche facility within a prescribed distance, either "
            "individually or as a common facility."
        ),
        "keywords_regex": r"(crèche|creche|cr[eè]che facility|child care|daycare|day care)",
        "severity_weight": 7,
        "template_fix": (
            "The Company shall provide a crèche facility within a "
            "reasonable distance from the workplace for employees with "
            "children below the age of six years. Employees shall be "
            "permitted to visit the crèche up to four times daily. "
            "The facility shall comply with all applicable safety and "
            "hygiene standards."
        ),
    },
    {
        "law_name": "Maternity Benefit Act, 2017 Amendment",
        "section": "Section 5(5)",
        "category": "employee_benefits",
        "requirement_text": (
            "The employer may permit a woman to work from home after the "
            "period of maternity leave, if the nature of work allows, on "
            "mutually agreed terms."
        ),
        "keywords_regex": r"(work from home|remote work.*maternity|flexible.*maternity|wfh.*after.*leave)",
        "severity_weight": 5,
        "template_fix": (
            "Upon expiry of maternity leave, the Company may offer a "
            "work-from-home arrangement on mutually agreed terms, subject "
            "to the nature of the employee's role. Requests shall be "
            "submitted to the reporting manager and approved within "
            "7 business days."
        ),
    },

    # ─────────────────────────────────────────────────────────────────────
    # 4. IT Act, 2000 — Cyber Security
    # ─────────────────────────────────────────────────────────────────────
    {
        "law_name": "IT Act, 2000",
        "section": "Section 43A",
        "category": "cyber_security",
        "requirement_text": (
            "Any body corporate possessing, dealing, or handling sensitive "
            "personal data must implement reasonable security practices and "
            "procedures, and is liable to compensate affected persons for "
            "negligence."
        ),
        "keywords_regex": r"(reasonable security|security practices|data protection.*measures|encryption|cyber security policy|information security)",
        "severity_weight": 9,
        "template_fix": (
            "The Company shall implement and maintain reasonable security "
            "practices and procedures as prescribed under IS/ISO/IEC 27001 "
            "for the protection of sensitive personal data. Security "
            "measures shall include encryption of data at rest and in "
            "transit, access controls, and periodic vulnerability "
            "assessments conducted at least annually."
        ),
    },
    {
        "law_name": "IT Act, 2000",
        "section": "Section 72A",
        "category": "cyber_security",
        "requirement_text": (
            "Any person who discloses personal information obtained under a "
            "lawful contract, without the consent of the data subject and "
            "with the intent to cause harm, is punishable with imprisonment "
            "and/or fine."
        ),
        "keywords_regex": r"(confidential.*data|data confidentiality|non.?disclosure.*data|breach of contract.*data)",
        "severity_weight": 8,
        "template_fix": (
            "All employees, contractors, and third-party vendors shall "
            "execute a non-disclosure agreement covering personal and "
            "confidential data accessed during the course of their duties. "
            "Unauthorized disclosure of such data shall constitute a "
            "breach of contract and may result in disciplinary action, "
            "termination, and legal proceedings under Section 72A of the "
            "IT Act, 2000."
        ),
    },
    {
        "law_name": "IT Act, 2000",
        "section": "Section 79",
        "category": "cyber_security",
        "requirement_text": (
            "An intermediary must observe due diligence as prescribed and "
            "appoint a Grievance Officer to address user complaints within "
            "specified timelines."
        ),
        "keywords_regex": r"(due diligence|intermediary|content.*takedown|grievance officer)",
        "severity_weight": 7,
        "template_fix": (
            "The Company, in its capacity as an intermediary, shall observe "
            "due diligence requirements including publishing its terms of "
            "service, appointing a Grievance Officer with publicly "
            "available contact details, and acknowledging user complaints "
            "within 24 hours. Content takedown requests shall be processed "
            "within 36 hours of receipt."
        ),
    },

    # ─────────────────────────────────────────────────────────────────────
    # 5. Labour Codes, 2020 — Labour Law
    # ─────────────────────────────────────────────────────────────────────
    {
        "law_name": "Labour Codes, 2020",
        "section": "Code on Wages",
        "category": "labour",
        "requirement_text": (
            "Wages shall be paid before the expiry of the 7th day after the "
            "last day of the wage period for establishments with fewer than "
            "1000 workers, and before the 10th day for others."
        ),
        "keywords_regex": r"(timely payment|payment of wages|wage.*7 days|salary.*within|payment.*period)",
        "severity_weight": 8,
        "required_value": 7.0,
        "required_unit": "days",
        "comparison_type": "max",
        "template_fix": (
            "The Company shall ensure that wages are credited to each "
            "employee's designated bank account no later than the 7th day "
            "following the end of the wage period. Wage slips detailing all "
            "components, deductions, and net pay shall be provided "
            "electronically on the date of payment."
        ),
    },
    {
        "law_name": "Labour Codes, 2020",
        "section": "Code on Social Security",
        "category": "labour",
        "requirement_text": (
            "The employer must contribute to the Employees' Provident Fund "
            "at 12% of basic wages for all eligible employees, and ensure "
            "timely remittance to the EPFO."
        ),
        "keywords_regex": r"(provident fund|PF.*12%|EPF|employees.*provident|12%.*basic)",
        "severity_weight": 9,
        "required_value": 12.0,
        "required_unit": "percent",
        "comparison_type": "min",
        "template_fix": (
            "The Company shall deduct and contribute 12% of each eligible "
            "employee's basic wages towards the Employees' Provident Fund "
            "(EPF) and remit the combined contribution (employer + employee) "
            "to the EPFO by the 15th of each month. Employees shall receive "
            "a monthly statement of PF contributions."
        ),
    },
    {
        "law_name": "Labour Codes, 2020",
        "section": "Code on Industrial Relations",
        "category": "labour",
        "requirement_text": (
            "Termination of an employee who has been in continuous service "
            "for at least one year requires a minimum notice period as "
            "prescribed, or wages in lieu thereof."
        ),
        "keywords_regex": r"(notice period|termination.*notice|prior (notice|intimation)|30 days.*notice|one month.*notice)",
        "severity_weight": 8,
        "required_value": 30.0,
        "required_unit": "days",
        "comparison_type": "min",
        "template_fix": (
            "Either party may terminate the employment relationship by "
            "providing a minimum of 30 days' written notice or payment of "
            "30 days' gross salary in lieu thereof. During the notice period, "
            "the employee shall continue to discharge duties unless "
            "otherwise directed by the Company."
        ),
    },
    {
        "law_name": "Labour Codes, 2020",
        "section": "Code on OSH",
        "category": "labour",
        "requirement_text": (
            "The employer must provide free annual health check-ups for "
            "workers above a prescribed age and maintain records of "
            "occupational health examinations."
        ),
        "keywords_regex": r"(annual health|health check|medical examination|occupational health|workplace safety)",
        "severity_weight": 7,
        "template_fix": (
            "The Company shall arrange free annual health check-ups for all "
            "employees, with mandatory occupational health screening for "
            "employees engaged in hazardous processes. Medical records "
            "shall be maintained confidentially for a minimum of five years "
            "and made available to the employee upon request."
        ),
    },

    # ─────────────────────────────────────────────────────────────────────
    # 6. Companies Act, 2013 — Corporate Governance
    # ─────────────────────────────────────────────────────────────────────
    {
        "law_name": "Companies Act, 2013",
        "section": "Section 135",
        "category": "corporate_governance",
        "requirement_text": (
            "Every company with a net worth of INR 500 crore or more, "
            "turnover of INR 1000 crore or more, or net profit of INR 5 "
            "crore or more must spend at least 2% of its average net profit "
            "on CSR activities."
        ),
        "keywords_regex": r"(CSR|corporate social responsibility|2%.*net profit|social responsibility)",
        "severity_weight": 7,
        "required_value": 2.0,
        "required_unit": "percent",
        "comparison_type": "min",
        "template_fix": (
            "The Company shall constitute a Corporate Social Responsibility "
            "Committee comprising three or more directors, of whom at least "
            "one shall be an independent director. The Company shall spend "
            "a minimum of 2% of its average net profits of the preceding "
            "three financial years on CSR activities as specified in "
            "Schedule VII of the Companies Act, 2013."
        ),
    },
    {
        "law_name": "Companies Act, 2013",
        "section": "Section 177",
        "category": "corporate_governance",
        "requirement_text": (
            "Every listed company and prescribed classes of companies must "
            "constitute an Audit Committee of the Board comprising a minimum "
            "of three directors, with a majority being independent directors."
        ),
        "keywords_regex": r"(audit committee|independent director|statutory audit)",
        "severity_weight": 8,
        "template_fix": (
            "The Board of Directors shall constitute an Audit Committee "
            "comprising a minimum of three directors, with at least "
            "two-thirds being independent directors. The chairperson of the "
            "Audit Committee shall be an independent director with financial "
            "expertise. The Committee shall oversee financial reporting, "
            "internal controls, and the statutory audit process."
        ),
    },
    {
        "law_name": "Companies Act, 2013",
        "section": "Section 166",
        "category": "corporate_governance",
        "requirement_text": (
            "A director must act in good faith to promote the objects of "
            "the company, exercise due care and diligence, and avoid "
            "situations involving direct or indirect conflict of interest."
        ),
        "keywords_regex": r"(good faith|conflict of interest|fiduciary|director.*duties|code of conduct.*director)",
        "severity_weight": 7,
        "template_fix": (
            "All directors of the Company shall act in good faith and in "
            "the best interest of the Company, its employees, shareholders, "
            "and the community. Directors shall disclose any material "
            "interest or conflict of interest at the earliest Board meeting "
            "and abstain from voting on related resolutions. A Code of "
            "Conduct for Directors shall be reviewed and affirmed annually."
        ),
    },
]


class Command(BaseCommand):
    help = "Seed the LegalRule database with comprehensive Indian law requirements."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            default=False,
            help="Delete all existing LegalRule rows before seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            deleted_count, _ = LegalRule.objects.all().delete()
            self.stdout.write(self.style.WARNING(
                f"Cleared {deleted_count} existing legal rule(s)."
            ))

        created_count = 0
        updated_count = 0
        law_names = set()
        errors = []

        for entry in SEED_DATA:
            try:
                _, created = LegalRule.objects.update_or_create(
                    law_name=entry["law_name"],
                    section=entry["section"],
                    defaults={
                        "category": entry["category"],
                        "requirement_text": entry["requirement_text"],
                        "keywords_regex": entry["keywords_regex"],
                        "severity_weight": entry["severity_weight"],
                        "template_fix": entry["template_fix"],
                        "required_value": entry.get("required_value"),
                        "required_unit": entry.get("required_unit", ""),
                        "comparison_type": entry.get("comparison_type", "min"),
                        "is_active": True,
                    },
                )
                law_names.add(entry["law_name"])
                if created:
                    created_count += 1
                else:
                    updated_count += 1
            except Exception as exc:
                errors.append(f"{entry['law_name']} {entry['section']}: {exc}")
                self.stderr.write(self.style.ERROR(
                    f"Error seeding {entry['law_name']} {entry['section']}: {exc}"
                ))

        total = created_count + updated_count
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {total} legal rules across {len(law_names)} laws "
            f"({created_count} created, {updated_count} updated)."
        ))

        if errors:
            self.stderr.write(self.style.ERROR(
                f"{len(errors)} error(s) encountered during seeding."
            ))
