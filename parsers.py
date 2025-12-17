import re
import pdfplumber
from constants import COMPANIES
from utils import norm

def identify_company(text: str) -> str:
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    for i, line in enumerate(lines):
        if line.upper().startswith("VENDOR"):
            # Look forward a few lines for ABN
            for j in range(i, min(i + 10, len(lines))):
                digits = re.sub(r"\D", "", lines[j])
                if digits in COMPANIES:
                    return COMPANIES[digits]

    # Fallback: old method
    clean = re.sub(r"\D", "", text)
    for abn, company in COMPANIES.items():
        if abn in clean:
            return company

    return "Unknown"


def parse_valleyfresh(text: str):
    inv = re.search(r"TAX INVOICE\s+(\d+)", text, re.IGNORECASE)
    invoice_no = inv.group(1) if inv else None

    po = re.search(r"Cust\.?\s*Ord(?:er)?\s*No\.?\s*:?[\s]*([A-Za-z0-9\-]+)", text, re.IGNORECASE)
    cust_po = po.group(1).split("-")[0] if po else None

    date_m = re.search(r"Date\s*[: ]\s*(\d{1,2}/\d{1,2}/\d{4})", text, re.IGNORECASE)
    invoice_date = date_m.group(1) if date_m else None

    lines = text.splitlines()

    total_trays = 0
    charges = {"Logistics": 0.0, "Freight": 0.0}

    i = 0
    while i < len(lines) - 1:
        line = lines[i].strip()
        next_line = lines[i + 1].strip()

        parts = line.split()

        # Check if numeric tail is present on line
        if len(parts) >= 5:
            try:
                qty   = float(parts[-4])
                price = float(parts[-3])
                tax   = float(parts[-2])
                amt   = float(parts[-1])

                up = line.upper()

                # Freight
                if "FREIGHT" in up:
                    charges["Freight"] += amt

                # Logistics (this line ALSO contains the product qty!)
                elif "LOGISTIC" in up:
                    charges["Logistics"] += amt

                    # Product code is on NEXT line → treat as product
                    total_trays += int(round(qty))

                # Unexpected numeric-looking line → ignore

            except:
                pass

        i += 1

    # Clean empty charges
    charges = {k: v for k, v in charges.items() if v}

    return invoice_no, cust_po, invoice_date, charges, total_trays


def parse_deluca(text: str):
    inv = re.search(r"Tax Invoice No[: ]+(\d+)", text, re.IGNORECASE)
    invoice_no = inv.group(1) if inv else None

    po = re.search(r"Cust(?:omer)?\s*Order\s*No.*?\n([A-Za-z0-9\-]+)", text, re.IGNORECASE)
    cust_po = po.group(1).split("-")[0] if po else None

    date_m = re.search(r"Date\s+(\d{1,2}/\d{1,2}/\d{4})", text, re.IGNORECASE)
    invoice_date = date_m.group(1) if date_m else None

    total_trays = 0
    logistics_ex = 0
    freight_ex = 0

    for line in text.splitlines():
        up = line.upper()

        if "BLUEBERRIES" in up:
            nums = re.findall(r"\d+(?:\.\d+)?", line)
            if len(nums) >= 5:
                qty = float(nums[-5])
                amount_ex = float(nums[-3])
                logistics_ex += amount_ex
                total_trays += int(round(qty))

        elif "TSPT" in up or " DD " in f" {up} " or "FREIGHT" in up:
            nums = re.findall(r"\d+(?:\.\d+)?", line)
            if len(nums) >= 5:
                amount_ex = float(nums[-3])
                freight_ex += amount_ex

    charges = {}
    if logistics_ex:
        charges["Logistics"] = round(logistics_ex, 2)
    if freight_ex:
        charges["Freight"] = round(freight_ex, 2)

    return invoice_no, cust_po, invoice_date, charges, total_trays

def parse_bache(text: str):
    # Normalise PDF whitespace FIRST
    text = text.replace("\xa0", " ")

    # ---------- Invoice number ----------
    inv = re.search(
        r"Invoice Number\s*(?:\n\s*)?([A-Z]{2,5}-\d+)",
        text,
        re.IGNORECASE
    )
    invoice_no = inv.group(1) if inv else None

    # ---------- Invoice date (SAME STRUCTURE) ----------
    date_m = re.search(
        r"Invoice Date\s*(?:\n\s*)?(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})",
        text,
        re.IGNORECASE
    )
    invoice_date = date_m.group(1) if date_m else None

    # ---------- Reference / PO ----------
    po = re.search(
        r"Reference\s*(?:\n\s*)?([A-Za-z0-9\-]+)",
        text,
        re.IGNORECASE
    )
    cust_po = po.group(1) if po else None

    charges = {}
    total_trays = 0

    for line in text.splitlines():
        up = line.upper()

        if "BERRY" in up and "BLUE" in up:
            nums = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", line)]
            if len(nums) >= 6:
                total_trays += int(round(nums[2]))
                charges["Logistics"] = charges.get("Logistics", 0) + nums[-1]

        elif "FREIGHT" in up:
            nums = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", line)]
            if nums:
                charges["Freight"] = charges.get("Freight", 0) + nums[-1]

    return invoice_no, cust_po, invoice_date, charges, total_trays



def parse_pdf_filelike(file_like):
    with pdfplumber.open(file_like) as pdf:
        text = "\n".join([p.extract_text() or "" for p in pdf.pages])
    company = identify_company(text)
    if company == "FRESHMAX NATIONAL PTY LTD":
        return company, parse_valleyfresh(text)
    elif company == "De Luca Banana Marketing":
        return company, parse_deluca(text)
    elif company == "Bache Bros Pty Ltd":
        return company, parse_bache(text)
    return company, (None, None, None, {}, 0)
