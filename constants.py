COMPANIES = {
    "45105141553": "De Luca Banana Marketing",
    "29612732064": "Bache Bros Pty Ltd",
    "61050197343": "Valley Fresh (Freshmax Australia)",
}

CARD_NAMES = {
    "De Luca Banana Marketing": "De Luca Banana Marketing Pty Ltd",
    "Bache Bros Pty Ltd": "Bache Bros Pty Ltd",
    "Valley Fresh (Freshmax Australia)": "Valley Fresh Pty Ltd",
}

# Excel column names (single source of truth)
CONSIGNOR_COL = "Consignor"
SUPPLIER_COL  = "Supplier"
PO_COL        = "TBC Ref. (Po No)"
TRAYS_COL     = "Trays"
CROP_COL      = "Crop"

# Strict company→consignors
COMPANY_CONSIGNORS = {
    "Valley Fresh (Freshmax Australia)": ["Valley Fresh Sydney", "Valley Fresh Melbourne"],
    "De Luca Banana Marketing": ["Valley Fresh Brisbane"],
    "Bache Bros Pty Ltd": ["Bache Bros Warehouse"],
}