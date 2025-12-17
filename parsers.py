import re
import pdfplumber
from constants import COMPANIES


# ============================================================
# Text normalisation
# ============================================================

def normalise_text(text: str) -> str:
    """
    Make PDF text predictable:
    - replace NBSP
    - collapse all whitespace
    """
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ============================================================
# Generic helpers
# ============================================================

def extract_labeled_value(text: str, label: str, value_pattern: str):
    """
    Extract value that follows a label, either:
        LABEL
        value
    or:
        LABEL value
    """
    pattern = rf"{label}\s*(?:\n\s*)?({value_pattern})"
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1) if m else None


# ============================================================
# Company detection
# ============================================================

def identify_company(text: str) -> str:
    """
    Identify company by ABN anywhere in document.
    """
    digits = re.sub(r"\D", "", text)
    for abn, company in COMPANIES.items():
        if abn in digits:
            return company
    return "Unknown"


# ============================================================
# Supplier-specific date extraction
# ============================================================

def extract_bache_invoice_date(text: str):
    """
    Bache invoices:
    - Invoice Date appears BEFORE Invoice Number
    - PDF text is flattened into a single stream
    Rule:
        Take the FIRST valid date AFTER 'Invoice Date'
    """
    idx = text.lower().find("invoice date")
    if idx == -1:
        return None

    # Look ahead a small window to avoid Due Date
    tail = text[idx: idx + 150]

    m = re.search(r"\d{1,2}\s+[A-Za-z]{3}\s+\d{4}", tail)
    return m.group(0) if m else None


# ============================================================
# Parsers
# ============================================================

def parse_valleyfresh(text: str):
    text = normalise_text(text)

    invoice_no   = extract_labeled_value(text, r"TAX INVOICE", r"\d+")
    cust_po      = extract_labeled_value(text, r"Cust\.?\s*Ord(?:er)?\s*No\.?", r"[A-Za-z0-9\-]+")
    invoice_date = extract_labeled_value(text, r"Date", r"\d{1,2}/\d{1,2}/\d{4}")

    total_trays = 0
    charges = {"Logistics": 0.0, "Freight": 0.0}

    for line in text.splitlines():
        nums = re.findall(r"\d+(?:\.\d+)?", line)
        if len(nums) < 4:
            continue

        qty = float(nums[-4])
        amt = float(nums[-1])
        up = line.upper()

        if "FREIGHT" in up:
            charges["Freight"] += amt
        elif "LOGISTIC" in up:
            charges["Logistics"] += amt
            total_trays += int(round(qty))

    charges = {k: v for k, v in charges.items() if v}
    return invoice_no, cust_po, invoice_date, charges, total_trays


def parse_deluca(text: str):
    text = normalise_text(text)

    invoice_no   = extract_labeled_value(text, r"Tax Invoice No", r"\d+")
    cust_po      = extract_labeled_value(text, r"Order\s*No", r"[A-Za-z0-9\-]+")
    invoice_date = extract_labeled_value(text, r"Date", r"\d{1,2}/\d{1,2}/\d{4}")

    total_trays = 0
    charges = {}

    for line in text.splitlines():
        nums = re.findall(r"\d+(?:\.\d+)?", line)
        up = line.upper()

        if "BLUEBERRIES" in up and len(nums) >= 5:
            total_trays += int(round(float(nums[-5])))
            charges["Logistics"] = charges.get("Logistics", 0) + float(nums[-3])

        elif ("TSPT" in up or "FREIGHT" in up) and len(nums) >= 5:
            charges["Freight"] = charges.get("Freight", 0) + float(nums[-3])

    return invoice_no, cust_po, invoice_date, charges, total_trays


def parse_bache(text: str):
    """
    Bache invoices are structurally different.
    - Date is BEFORE invoice number
    - Right-hand column is flattened
    """
    text = normalise_text(text)

    invoice_no = extract_labeled_value(
        text, r"Invoice Number", r"[A-Z]{2,5}-\d+"
    )

    invoice_date = extract_bache_invoice_date(text)

    cust_po = extract_labeled_value(
        text, r"Reference", r"[A-Za-z0-9\-]+"
    )

    charges = {}
    total_trays = 0

    for line in text.splitlines():
        nums = re.findall(r"\d+(?:\.\d+)?", line)
        up = line.upper()

        if "BERRY" in up and "BLUE" in up:
            nums = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", line)]

            # Heuristic for Bache:
            # - tray qty is the largest integer >= 10 and <= 1000
            # - amount is the largest value with decimals near the end
            tray_candidates = [n for n in nums if n.is_integer() and 10 <= n <= 1000]

            if tray_candidates:
                trays = int(max(tray_candidates))
                total_trays += trays

                amount = nums[-1]
                charges["Logistics"] = charges.get("Logistics", 0) + amount


        elif "FREIGHT" in up and nums:
            charges["Freight"] = charges.get("Freight", 0) + float(nums[-1])

    return invoice_no, cust_po, invoice_date, charges, total_trays


# ============================================================
# Entry point
# ============================================================

def parse_pdf_filelike(file_like):
    with pdfplumber.open(file_like) as pdf:
        raw_text = "\n".join(p.extract_text() or "" for p in pdf.pages)

    company = identify_company(raw_text)

    if company == "FRESHMAX NATIONAL PTY LTD":
        return company, parse_valleyfresh(raw_text)

    if company == "De Luca Banana Marketing":
        return company, parse_deluca(raw_text)

    if company == "Bache Bros Pty Ltd":
        return company, parse_bache(raw_text)

    return company, (None, None, None, {}, 0)
