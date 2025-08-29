import re

def norm(s: str) -> str:
    return re.sub(r"\s+", "", str(s)).upper()

def digits_only(s: str) -> str:
    return re.sub(r"\D", "", str(s))

def make_payload_key(company: str, invoice_no: str, cust_po: str) -> str:
    """Stable key used to save/retrieve overrides per invoice."""
    return f"{str(company).strip()}|{str(invoice_no).strip()}|{str(cust_po).strip()}"