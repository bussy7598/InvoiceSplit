import io
import pandas as pd

def group_with_blank_lines(df: pd.DataFrame, group_col: str = "Supplier Invoice No.") -> pd.DataFrame:
    out = df.copy()
    out["_grp"] = out[group_col].astype(str)
    lines = []
    for _, g in out.groupby("_grp", sort=False):
        lines.extend(g.drop(columns=["_grp"]).to_dict("records"))
        lines.append({})  # blank
    return pd.DataFrame(lines)

def to_tab_delimited_with_header(df_export: pd.DataFrame) -> str:
    buf = io.StringIO()
    buf.write("{}\n")  # MYOB header row required
    df_export.to_csv(buf, sep="\t", index=False, lineterminator="\r\n")
    return buf.getvalue()
