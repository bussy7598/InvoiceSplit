import re
import pdfplumber
from constants import COMPANIES
from utils import norm

def identify_company(text: str) -> str:
    clean = text.replace(" ", "").replace("-", "")
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

    charges, total_trays = {}, 0
    for line in text.splitlines():
        if "Logistic" in line:
            parts = line.split()
            try:
                charges["Logistics"] = float(parts[-1])
                total_trays = int(round(float(parts[-4])))
            except: pass
        if "Freight" in line:
            parts = line.split()
            try:
                charges["Freight"] = float(parts[-1])
            except: pass

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
    inv = re.search(r"Invoice Number\s+([A-Za-z0-9\-]+)", text, re.IGNORECASE)
    invoice_no = inv.group(1) if inv else None
    po = re.search(r"Reference\s+([A-Za-z0-9\-]+)", text, re.IGNORECASE)
    cust_po = po.group(1).split("-")[0] if po else None
    date_m = re.search(r"Invoice Date\s+(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})", text, re.IGNORECASE)
    invoice_date = date_m.group(1) if date_m else None

    charges, total_trays = {}, 0
    for line in text.splitlines():
        up = line.upper()
        if "BERRY" in up and "BLUE" in up:
            tail = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", line)][-5:]
            if len(tail) >= 5:
                qty = tail[1]; amount = tail[-1]
                total_trays = int(round(qty))
                charges["Logistics"] = float(amount)
        if "FREIGHT" in up:
            nums = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", line)]
            if nums: charges["Freight"] = float(nums[-1])
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
