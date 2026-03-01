"""Parse the Google Sheet's side-by-side month layout into normalized records."""

import re
from dataclasses import dataclass


@dataclass
class RawSheetRecord:
    merchant_name: str
    month: str          # YYYY-MM
    date_str: str       # original date string from sheet
    amount_str: str     # original amount string from sheet
    sheet_tab: str
    row_index: int      # 0-based row index in the sheet


MONTH_MAP = {
    "jan": "01", "january": "01",
    "feb": "02", "february": "02",
    "mar": "03", "march": "03",
    "apr": "04", "april": "04",
    "may": "05",
    "jun": "06", "june": "06",
    "jul": "07", "july": "07",
    "aug": "08", "august": "08",
    "sep": "09", "sept": "09", "september": "09",
    "oct": "10", "october": "10",
    "nov": "11", "november": "11",
    "dec": "12", "december": "12", "decemeber": "12",  # known typo in sheet
}


def _cell(row, col):
    """Safely get a cell value, returning '' if out of bounds."""
    if col < len(row):
        return row[col].strip()
    return ""


def _parse_month_name(total_label):
    """Extract month number from a total label like 'Jan Total', 'October Total',
    or 'FebruaryTotal' (no space). Returns month as '01'-'12', or None."""
    m = re.match(r"(\w+?)\s*Total", total_label, re.IGNORECASE)
    if not m:
        return None
    name = m.group(1).lower()
    return MONTH_MAP.get(name)


def _find_sections(data):
    """Find year sections in the sheet data.

    Each section starts with a row where cell[0] is a 4-digit year.
    Returns list of (year, start_row) tuples.
    """
    sections = []
    for i, row in enumerate(data):
        if row and row[0].strip().isdigit() and len(row[0].strip()) == 4:
            sections.append((row[0].strip(), i))
    return sections


def _find_header_row(data, start_row, end_row):
    """Find the header row containing 'Merchant' within the given range.
    Returns the row index, or None."""
    for i in range(start_row, min(end_row, len(data))):
        row = data[i]
        if any(c.strip() == "Merchant" for c in row):
            return i
    return None


def _get_block_positions(header_row):
    """From a header row, find the column positions of each month block.

    Each block is 3 columns: Merchant, Due Date, Amount.
    Returns list of (merchant_col, date_col, amount_col) tuples.
    """
    blocks = []
    for i, cell in enumerate(header_row):
        if cell.strip() == "Merchant":
            blocks.append((i, i + 1, i + 2))
    return blocks


def _get_month_labels(data, total_row_index, blocks):
    """Extract month labels from the total row for each block.

    The total row has entries like 'Jan Total' in the date column of each block.
    Returns list of month strings ('01', '02', etc.), one per block.
    """
    if total_row_index < 0 or total_row_index >= len(data):
        return [None] * len(blocks)
    total_row = data[total_row_index]
    months = []
    for _, date_col, _ in blocks:
        label = _cell(total_row, date_col)
        months.append(_parse_month_name(label))
    return months


def parse_sheet(data, sheet_tab):
    """Parse the full sheet data into a list of RawSheetRecord.

    Args:
        data: 2D list of strings from the Google Sheets API.
        sheet_tab: Name of the sheet tab (e.g. 'Expense').

    Returns:
        List of RawSheetRecord.
    """
    if not data:
        return []

    sections = _find_sections(data)
    if not sections:
        return []

    records = []

    for sec_idx, (year, sec_start) in enumerate(sections):
        # Section ends at the next section or end of data
        sec_end = sections[sec_idx + 1][1] if sec_idx + 1 < len(sections) else len(data)

        header_idx = _find_header_row(data, sec_start, sec_end)
        if header_idx is None:
            continue

        header_row = data[header_idx]
        blocks = _get_block_positions(header_row)
        if not blocks:
            continue

        # The total row is typically 1 row above the header row
        total_row_idx = header_idx - 1
        month_nums = _get_month_labels(data, total_row_idx, blocks)

        # Parse data rows (starting after header, until blank row or section end)
        for row_idx in range(header_idx + 1, sec_end):
            row = data[row_idx]
            if not row or all(c.strip() == "" for c in row):
                break  # Blank row = end of data for this section

            for block_idx, (merch_col, date_col, amt_col) in enumerate(blocks):
                merchant = _cell(row, merch_col)
                date_str = _cell(row, date_col)
                amount_str = _cell(row, amt_col)

                if not merchant:
                    continue

                month_num = month_nums[block_idx] if block_idx < len(month_nums) else None
                if month_num:
                    month = f"{year}-{month_num}"
                else:
                    month = year  # Fallback — shouldn't happen with well-formed data

                records.append(RawSheetRecord(
                    merchant_name=merchant,
                    month=month,
                    date_str=date_str,
                    amount_str=amount_str,
                    sheet_tab=sheet_tab,
                    row_index=row_idx,
                ))

    return records


def get_available_months(records):
    """Extract unique months from parsed records, sorted chronologically.

    Returns list of dicts: [{"month": "2026-01", "label": "Jan 2026"}, ...]
    """
    MONTH_LABELS = {
        "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
        "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
        "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec",
    }
    months = sorted(set(r.month for r in records if re.match(r"\d{4}-\d{2}$", r.month)))
    result = []
    for m in months:
        year, num = m.split("-")
        label = f"{MONTH_LABELS.get(num, num)} {year}"
        result.append({"month": m, "label": label})
    return result
