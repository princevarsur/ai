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
        "required_elements": [
            {"id": "icc_exists", "text": "Company has constituted an Internal Complaints Committee", "weight": 1.0},
            {"id": "presiding_officer", "text": "ICC has a Presiding Officer who is a senior woman employee", "weight": 1.0},
            {"id": "employee_members", "text": "ICC has at least two employee members committed to the cause of women", "weight": 1.0},
            {"id": "external_member", "text": "ICC has one external member from an NGO or association", "weight": 1.0}
        ],
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
        "keywords_regex": r"(external member|NGO|non.?governmental|women.?s? (organization|association)|complaints? (panel|committee)|icc|internal committee)",
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
        "required_elements": [
            {"id": "inquiry_90_days", "text": "The inquiry into a complaint must be completed within 90 days", "weight": 1.0},
            {"id": "action_60_days", "text": "Employer must act on the ICC recommendations within 60 days", "weight": 1.0}
        ],
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
        "required_elements": [
            {"id": "explicit_consent", "text": "Personal data processing requires free specific informed and unambiguous consent", "weight": 1.0},
            {"id": "specified_purpose", "text": "Consent notice must clearly specify the purpose of data collection", "weight": 1.0}
        ],
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
        "section": "Section 12 (Right to Correction & Erasure)",
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
        "section": "Section 13 (Right of Grievance Redressal)",
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
        "section": "Section 8(6) (Personal Data Breach Notification)",
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
            "Data Principals without unreasonable delay in accordance with "
            "prescribed statutory timelines. The notification shall include "
            "the nature and extent of the breach, data compromised, and "
            "remedial measures taken."
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

    # ─────────────────────────────────────────────────────────────────────
    # 7. Comprehensive Labour Codes & Employment Safeguards (2020 Codes & Precedents)
    # ─────────────────────────────────────────────────────────────────────
    {
        "law_name": "Industrial Relations Code, 2020",
        "section": "Section 77 (Natural Justice & Inquiry)",
        "category": "labour",
        "requirement_text": (
            "No employee or worker shall be dismissed or terminated for misconduct without "
            "a documented inquiry and a reasonable opportunity to be heard (audi alteram partem). "
            "Clauses permitting termination for misconduct 'with or without inquiry' violate natural justice."
        ),
        "keywords_regex": r"(with or without inquiry|terminate.*without inquiry|dismiss.*without inquiry|audi alteram partem|natural justice)",
        "severity_weight": 10,
        "template_fix": (
            "An employee alleging misconduct or indiscipline shall be issued a formal show-cause notice "
            "and provided a minimum of 7 days to respond. Termination of service for misconduct shall only "
            "occur after conducting a documented domestic inquiry in accordance with principles of natural justice."
        ),
    },
    {
        "law_name": "Industrial Relations Code, 2020",
        "section": "Standing Orders (Deemed Resignation)",
        "category": "labour",
        "requirement_text": (
            "Clauses deeming an employee to have automatically quit or resigned after a period of "
            "unauthorized absence (e.g. 15 consecutive work days) without notice and opportunity to explain "
            "are unlawful terminations in disguise under Indian employment jurisprudence."
        ),
        "keywords_regex": r"(deemed to have quit|deemed resignation|abandonment of service|absent for \d+ consecutive.*quit|deemed.*terminated)",
        "severity_weight": 9,
        "template_fix": (
            "If an employee remains unauthorizedly absent for more than 10 consecutive working days, the Company "
            "shall issue a written show-cause notice to the employee's registered address calling upon them to explain "
            "the absence within 7 days. Only upon failure to respond or report without valid explanation shall separation proceedings initiate."
        ),
    },
    {
        "law_name": "Industrial Relations Code, 2020",
        "section": "Section 4 (Trade Union & Collective Action)",
        "category": "labour",
        "requirement_text": (
            "Employees retain lawful rights to form or join trade unions and engage in collective bargaining. "
            "Vague grounds terminating employees for general 'group activity' or 'anti-organizational activity' "
            "without defining unlawful conduct violate statutory labor rights."
        ),
        "keywords_regex": r"(anti-organizational activity|group activity against|group activity.*liable|unionization|collective action)",
        "severity_weight": 8,
        "template_fix": (
            "Disciplinary action may be initiated against employees engaging in illegal strikes, physical vandalism, "
            "incitement to violence, or breach of proprietary confidentiality. Nothing in this policy shall abridge "
            "lawful collective bargaining or associational rights protected under Indian labor codes."
        ),
    },
    {
        "law_name": "Code on Wages, 2019",
        "section": "Section 18 (Fines & Tardiness Deductions)",
        "category": "labour",
        "requirement_text": (
            "Salary deductions or fines for tardiness or late arrival (such as 1/8th day or half-day pay cuts) "
            "must comply with statutory fine ceilings, display of permissible fine acts, and cannot arbitrarily "
            "dock earned wages without procedural safeguards."
        ),
        "keywords_regex": r"(late comings?|lateness|repeated lateness|attendance incentive|incentive reduction|deduct.*1/8|deduct.*half day|deduct.*late|tardiness|late.*deduct|late.*reduction)",
        "severity_weight": 9,
        "template_fix": (
            "Employees arriving after designated working hours may be subject to compensatory hour adjustment or "
            "leave deductions in accordance with statutory wage principles. No monetary deduction exceeding statutory "
            "permissible ceilings under Section 18 of the Code on Wages shall be imposed."
        ),
    },
    {
        "law_name": "Code on Wages, 2019",
        "section": "Section 21 (Ceiling on Wage Deductions)",
        "category": "labour",
        "requirement_text": (
            "The total amount of deductions from wages (including recovery of salary advances, interest-free loans, "
            "fines, and tax withholdings) shall not exceed 50% of the total wages payable to an employee in any wage period."
        ),
        "keywords_regex": r"(loan recovery|monthly installments.*salary|recover.*from salary|salary advance|deduct.*salary|salary.*deduct|deduct.*half|deduct.*days?|50%.*ceiling)",
        "severity_weight": 8,
        "template_fix": (
            "Recovery of employee loans, advances, or authorized payroll deductions shall be scheduled in structured monthly installments. "
            "In accordance with Section 21 of the Code on Wages, cumulative deductions in any single wage period shall not exceed "
            "50 percent of the employee's gross wages."
        ),
    },
    {
        "law_name": "Industrial Relations Code, 2020",
        "section": "Section 4 (Grievance Redressal Committee)",
        "category": "labour",
        "requirement_text": (
            "Every industrial establishment employing 20 or more workers must constitute a formal Grievance Redressal Committee "
            "(GRC) with equal representation of employer and worker nominees and a time-bound 30-day resolution protocol."
        ),
        "keywords_regex": r"(grievance redressal committee|GRC|worker nominee|grievance procedure|speak up process|grievance.*lodge)",
        "severity_weight": 8,
        "template_fix": (
            "The Company has established a structured Grievance Redressal Committee (GRC) comprising equal representations of "
            "management and employee nominees. Grievances submitted in writing shall be investigated and resolved within a strict "
            "30-day timeline, with right of appeal to senior leadership."
        ),
    },
    {
        "law_name": "Code on Social Security, 2020",
        "section": "Section 53 (Gratuity for Fixed-Term & Continuous Service)",
        "category": "employee_benefits",
        "requirement_text": (
            "Gratuity is payable to permanent employees upon completion of 5 years of continuous service, and to fixed-term "
            "contractual employees upon completion of 1 year of service without requiring the 5-year threshold."
        ),
        "keywords_regex": r"(gratuity.*5 years|gratuity.*fixed term|bonus & gratuity|payment of gratuity|gratuity as per law)",
        "severity_weight": 8,
        "template_fix": (
            "Gratuity shall be paid to regular employees upon completion of five years of continuous service upon separation or retirement. "
            "For fixed-term contractual employees, gratuity shall be computed and paid upon completion of one year of continuous fixed-term "
            "service under Section 53 of the Code on Social Security."
        ),
    },

    # ─────────────────────────────────────────────────────────────────────
    # 8. Detailed POSH Act 2013 Mandates (Committees, Windows, Protections)
    # ─────────────────────────────────────────────────────────────────────
    {
        "law_name": "POSH Act, 2013",
        "section": "Section 9 (Complaint Window)",
        "category": "workplace_safety",
        "requirement_text": (
            "An aggrieved woman must be granted a statutory window of at least 3 months from the date of incident "
            "(extendable up to 6 months by the ICC) to file a sexual harassment complaint. Policy limits requiring complaints "
            "'within 10 days' or other short windows violate statutory rights."
        ),
        "keywords_regex": r"(within \d+ days|preferably within \d+ days|complaint window|3 months.*incident|time limit.*complaint|complaints panel)",
        "severity_weight": 9,
        "template_fix": (
            "An aggrieved employee may file a written complaint of sexual harassment to the Internal Complaints Committee (ICC) "
            "within three (3) months from the date of the incident (and in case of a series of incidents, within three months from "
            "the date of the last incident), extendable by the ICC for good cause."
        ),
    },
    {
        "law_name": "POSH Act, 2013",
        "section": "Section 16 (Confidentiality Mandate)",
        "category": "workplace_safety",
        "requirement_text": (
            "The identity and addresses of the aggrieved woman, respondent, and witnesses, as well as the conciliation and inquiry "
            "proceedings and recommendations, must be kept strictly confidential and shall not be published or disclosed."
        ),
        "keywords_regex": r"(confidentiality.*posh|identity.*aggrieved|prohibition of publication|section 16.*posh|secret.*proceeding)",
        "severity_weight": 8,
        "template_fix": (
            "In mandatory accordance with Section 16 of the POSH Act, all matters pertaining to complaints, witness testimonies, "
            "identities of parties, inquiry proceedings, and ICC recommendations shall be maintained in strict confidentiality. "
            "Any unauthorized breach of confidentiality shall attract statutory penalties and disciplinary action."
        ),
    },
    {
        "law_name": "POSH Act, 2013",
        "section": "Section 12 (Interim Relief During Inquiry)",
        "category": "workplace_safety",
        "requirement_text": (
            "During the pendency of a POSH inquiry, the Internal Committee may recommend interim relief measures including transferring "
            "the aggrieved woman or respondent to another workplace, or granting up to 3 months of paid leave to the complainant."
        ),
        "keywords_regex": r"(interim relief|transfer of.*respondent|leave.*during inquiry|pendency of inquiry|interim measures)",
        "severity_weight": 7,
        "template_fix": (
            "During the pendency of an inquiry, the ICC may recommend interim relief measures upon written request by the complainant, "
            "including transfer of the complainant or respondent to another location, or granting leave up to three months (in addition "
            "to standard accrued leave entitlements)."
        ),
    },
    {
        "law_name": "POSH Act, 2013",
        "section": "Section 14 (Malicious & False Complaints)",
        "category": "workplace_safety",
        "requirement_text": (
            "Disciplinary action for a false or malicious complaint under Section 14 requires explicit proof of malicious intent and "
            "fabricated evidence established through an inquiry. Mere inability to substantiate a complaint or lack of proof cannot "
            "justify punishment or retaliation against the complainant."
        ),
        "keywords_regex": r"(false complaint|malicious complaint|unsubstantiated complaint|found to be false|action against complainant)",
        "severity_weight": 8,
        "template_fix": (
            "If the ICC concludes after a formal inquiry that a complaint was made with demonstrated malicious intent or supported by "
            "intentionally forged/fabricated evidence, disciplinary action may be recommended. As explicitly enacted under Section 14, "
            "mere inability to substantiate a complaint or lack of adequate evidence shall never attract disciplinary action."
        ),
    },

    # ─────────────────────────────────────────────────────────────────────
    # 9. DPDP Act 2023 & Privacy Jurisprudence (Employee Background Checks)
    # ─────────────────────────────────────────────────────────────────────
    {
        "law_name": "DPDP Act, 2023",
        "section": "Section 5 & 7 (Background & Aadhaar Verification)",
        "category": "data_privacy",
        "requirement_text": (
            "Collection and processing of sensitive personal employee data—such as Aadhaar identification numbers, credit reports, and "
            "criminal background checks—must be accompanied by a transparent Data Principal notice, specific lawful purpose limitation, "
            "and unambiguous consent. Mandating Aadhaar as the sole ID option without alternatives risks statutory privacy non-compliance."
        ),
        "keywords_regex": r"(aadhaar|credit check|criminal background|background check|police verification|verification.*data)",
        "severity_weight": 9,
        "template_fix": (
            "Prior to conducting background verification or requesting identification documents, the Company shall provide a DPDP-compliant "
            "privacy notice detailing the data collected and specific purposes. Submission of Aadhaar shall remain voluntary alongside "
            "alternative valid Government ID options (such as Passport, Voter ID, or Driving License), and all background reports shall "
            "be secured and disposed of per retention policies."
        ),
    },

    # ─────────────────────────────────────────────────────────────────────
    # 7. Comprehensive Indian Corporate, IT & Cyber Use Rules
    # ─────────────────────────────────────────────────────────────────────
    {
        "law_name": "IT Act, 2000",
        "section": "Section 43 (Damage to Computers & Acceptable Use)",
        "category": "data_privacy",
        "requirement_text": (
            "Employees and authorized users must abide by corporate acceptable usage policies regarding IT resources. Any unauthorized "
            "access, sharing of accounts/passwords, network disruption, extraction of source code, or introduction of contaminants into "
            "company computers is prohibited under Section 43 of the Information Technology Act, 2000."
        ),
        "keywords_regex": r"(unauthorized (use|access)|password.*(share|acquire)|hacking|cracking|it resources|computer accounts|software license|network.*permit|interrupt.*communication|cyber laws)",
        "severity_weight": 8,
        "template_fix": (
            "All corporate IT resources, accounts, and network infrastructure are meant solely for authorized professional duties. "
            "Unauthorized sharing of login credentials, accessing unauthorized files or networks, and installing unapproved software "
            "are strictly prohibited and subject to disciplinary action and statutory liability under Section 43 of the IT Act, 2000."
        ),
    },
    {
        "law_name": "IT Act, 2000",
        "section": "Section 66E (Workplace Privacy & CCTV Surveillance)",
        "category": "data_privacy",
        "requirement_text": (
            "Workplace digital monitoring, email tracking, or CCTV video surveillance must respect reasonable personal privacy expectations "
            "under Section 66E of the IT Act, 2000 and DPDP Act, 2023. Employers must explicitly notify employees of monitored zones and "
            "cannot monitor private personal spaces or personal devices without informed consent."
        ),
        "keywords_regex": r"(surveillance|monitoring.*email|monitor.*computer|cctv|camera|tracking|intercept.*communication|privacy.*monitoring|keystroke|internet usage.*monitor)",
        "severity_weight": 9,
        "template_fix": (
            "The Company employs digital network monitoring and CCTV surveillance in designated operational areas strictly for security "
            "and legitimate business protection. In compliance with Section 66E of the IT Act, no surveillance shall be conducted in "
            "private zones, and employee monitoring shall be conducted transparently."
        ),
    },
    {
        "law_name": "DPDP Act, 2023",
        "section": "Section 6 (Consent for Biometrics & Sensitive Data)",
        "category": "data_privacy",
        "requirement_text": (
            "Collection and processing of biometric identifiers (such as fingerprint attendance or facial recognition) and sensitive "
            "employee records require clear Data Principal consent accompanied by an itemized privacy notice under Section 6 of the DPDP Act, 2023."
        ),
        "keywords_regex": r"(biometric|fingerprint|facial recognition|attendance.*biometric|personal data.*consent|sensitive personal data|health record|medical data.*collect)",
        "severity_weight": 9,
        "template_fix": (
            "Before capturing biometric attendance or collecting sensitive personal records, the Company shall present an explicit DPDP "
            "consent declaration detailing the exact scope, processing mechanism, and security controls applied to employee data."
        ),
    },
    {
        "law_name": "Indian Contract Act, 1872",
        "section": "Section 27 (Void Non-Compete & Restraint of Trade)",
        "category": "contracts",
        "requirement_text": (
            "Under Section 27 of the Indian Contract Act, 1872, post-termination restraint of trade agreements prohibiting employees from "
            "joining competitors or working in the same trade/profession after employment termination are legally void and unenforceable in India."
        ),
        "keywords_regex": r"(non.?compete|join.*competitor|restraint of trade|prohibit.*working.*after|restriction after termination|post.?termination.*employment|not engage in.*same business)",
        "severity_weight": 10,
        "template_fix": (
            "During employment, employees shall devote full-time professional efforts to the Company and avoid conflict of interest. "
            "Upon separation, while post-employment trade competition is not lawfully restricted under Section 27 of the Contract Act, "
            "employees remain strictly bound by confidentiality and non-solicitation covenants regarding proprietary clients and IP."
        ),
    },
    {
        "law_name": "Shops & Establishments Acts",
        "section": "State Rules (Leave Encashment & Carry Forward)",
        "category": "labour",
        "requirement_text": (
            "Applicable State Shops and Establishments rules govern earned/privilege leave carry-forward limits and mandatory leave encashment "
            "upon resignation or retirement. Arbitrary forfeiture of earned leave without encashment benefits violates state statutory entitlements."
        ),
        "keywords_regex": r"(earned leave|privilege leave|leave encashment|carry forward.*leave|forfeit.*leave|lapse.*leave|encashment.*resignation|unavail(ed)? leave)",
        "severity_weight": 8,
        "template_fix": (
            "Employees are entitled to annual privilege leave carry-forward up to statutory ceilings under applicable State Shops and "
            "Establishments Rules. Upon separation from service, unutilized earned leave shall be legally encashed as per extant wage formulas."
        ),
    },
    {
        "law_name": "Shops & Establishments Acts",
        "section": "State Rules (Working Hours, Overtime & Night Shifts)",
        "category": "labour",
        "requirement_text": (
            "Standard working hours must not exceed 9 hours daily or 48 hours weekly. All mandatory hours beyond statutory limits must be "
            "compensated at double overtime rates. Establishments running night shifts involving female staff must mandatorily provide "
            "doorstep transport and verified security escorts after designated evening hours."
        ),
        "keywords_regex": r"(working hours|48 hours|overtime|ot compensation|night shift|transport.*women|drop.*women|after 8.*pm|after 10.*pm|cab.*facility)",
        "severity_weight": 9,
        "template_fix": (
            "Normal working hours shall conform to statutory ceilings (48 hours/week). Overtime duty shall be remunerated as per State Shops "
            "Rules. For female staff assigned to evening/night shifts ending after 8:00 PM, the Company shall arrange secure, company-verified "
            "door-to-door cab transport."
        ),
    },
    {
        "law_name": "Code on Wages, 2019",
        "section": "Section 14 (Prohibition of Salary Forfeiture)",
        "category": "labour",
        "requirement_text": (
            "Earned salary for days actually worked is an absolute statutory right under the Code on Wages. Clauses asserting total forfeiture "
            "of unpaid salary, accrued benefits, or earned wages upon resignation without serving full notice are unlawful. Any recovery is strictly "
            "limited to the agreed notice pay shortfall."
        ),
        "keywords_regex": r"(forfeit.*salary|forfeit.*wages|withheld.*salary.*notice|non-payment of dues|forfeit.*earned|salary will be forfeited|wages.*forfeited)",
        "severity_weight": 10,
        "template_fix": (
            "In the event of short notice resignation, the Company may recover notice pay equivalent to the shortfall period as stipulated "
            "in the appointment agreement. Earned wages for days actually worked shall not be withheld or forfeited under any circumstance."
        ),
    },
    {
        "law_name": "Maternity Benefit Act, 2017 Amendment",
        "section": "Section 12 (Protection from Dismissal during Maternity)",
        "category": "labour",
        "requirement_text": (
            "Under Section 12 of the Maternity Benefit Act, employers are strictly prohibited from issuing notice of termination, discharge, "
            "or dismissal to a female employee during or on account of her absence on statutory maternity leave."
        ),
        "keywords_regex": r"(terminate.*maternity|dismiss.*maternity|discharge.*pregnancy|maternity.*absence.*terminate|service condition.*maternity)",
        "severity_weight": 10,
        "template_fix": (
            "In strict compliance with Section 12 of the Maternity Benefit Act, no female employee shall be issued notice of discharge, "
            "dismissal, or service disadvantage during or on account of availing statutory maternity leave."
        ),
    },
    {
        "law_name": "DPDP Act, 2023",
        "section": "Section 8(4) (Post-Employment Data Erasure)",
        "category": "data_privacy",
        "requirement_text": (
            "Upon separation of an employee, employers are legally obligated under Section 8(4) of the DPDP Act to erase personal employee "
            "records once the legitimate employment purpose has expired and statutory record-keeping periods have concluded."
        ),
        "keywords_regex": r"(retention.*employee data|delete.*after resignation|data.*exit|erase.*personnel record|destroy.*data.*resignation|storage.*post.?employment)",
        "severity_weight": 8,
        "template_fix": (
            "Personal data collected during employment shall be archived securely upon separation and securely deleted upon expiration "
            "of mandated corporate and statutory labor retention timelines as mandated by Section 8(4) of the DPDP Act, 2023."
        ),
    },
    {
        "law_name": "POSH Act, 2013",
        "section": "Section 19 & 21 (Employer Obligations & Statutory Displays)",
        "category": "workplace_safety",
        "requirement_text": (
            "Employers are required under Sections 19 and 21 of the POSH Act to conspicuously display penal consequences of harassment and "
            "ICC committee contact details across workplace notices and portals, and submit an annual compliance summary report to the District Officer."
        ),
        "keywords_regex": r"(annual report.*posh|district officer|display.*posh|display.*icc|notice board.*posh|submit.*report.*posh)",
        "severity_weight": 8,
        "template_fix": (
            "The Company shall conspicuously display posters and intranet notices detailing POSH guidelines, penal consequences of sexual "
            "harassment, and Internal Committee roster contacts. The ICC shall file an annual summary compliance report with the designated District Officer."
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

        # Remove historical mis-cited rules if present
        LegalRule.objects.filter(law_name="Industrial Relations Code, 2020", section__istartswith="Chapter III").delete()
        LegalRule.objects.filter(law_name="DPDP Act, 2023", section__in=["Section 8", "Section 10", "Section 13"]).delete()

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
                        "required_elements": entry.get("required_elements") or [{"id": "element_1", "text": entry["requirement_text"], "weight": 1.0}],
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
