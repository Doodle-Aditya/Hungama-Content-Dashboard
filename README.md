# Content Operations Dashboard

An internal Streamlit dashboard for monitoring content partner / label
agreements and their report-sharing status. Built for Legal, Finance, and
MIS teams.

Two pages, reading from one Excel workbook:

- **Agreement Monitor** (`app.py`) — validity of each label's agreement
  (Active / Expiring Soon / Expires Today / Expired).
- **Report Tracker** (`pages/1_Report_Tracker.py`) — one row per label
  (most recent entry), filterable by Agreement Status and Period.

---

## 1. Folder Structure

```
ContentOperationsDashboard/
│
├── app.py                     # Agreement Monitor — entry point
├── dashboard.py                # Agreement Monitor — UI rendering
├── report_tracker.py           # Report Tracker — UI rendering
├── utils.py                     # Shared data logic (loading, dates, status, matching)
├── config.py                     # Constants, thresholds, colors, file paths
├── requirements.txt
├── README.md
│
├── data/
│   └── Agreements.xlsx           # Source workbook (Sheet 1 + Sheet 2)
│
└── pages/
    └── 1_Report_Tracker.py       # Report Tracker — entry point (auto-registered by Streamlit)
```

| File | Responsibility |
|---|---|
| `config.py` | Single source of truth for column names, status labels, colors, thresholds, paths. |
| `utils.py` | Pure data logic — loading both sheets, date parsing, status computation, label matching, dedup. No UI code beyond `@st.cache_data`. |
| `dashboard.py` | Agreement Monitor UI — KPIs, charts, filters, table. |
| `report_tracker.py` | Report Tracker UI — KPIs, chart, filters, table. |
| `app.py` / `pages/1_Report_Tracker.py` | Thin entry points. Load data, call rendering functions, handle errors. No business logic. |

---

## 2. Excel Data Format

`data/Agreements.xlsx` has two sheets, read by position (order matters,
not sheet name):

**Sheet 1 — Agreements** (`AGREEMENTS_SHEET_NAME = 0`)

| Column | Type |
|---|---|
| `Label Name` | Text |
| `Start Date` | Date |
| `Expiry Date` | Date |

**Sheet 2 — Reports Update** (`REPORTS_SHEET_NAME = 1`)

Required: `TV Studios`, `Period`, `Report Date`, `Shared with CP`.
Other operational columns (`Approval to MIS`, `Approval from Finance`,
revenue/invoice fields, etc.) may be present and are read if found, but
aren't currently used by either page.

A given label can appear multiple times on Sheet 2 (e.g. once per
period). The Report Tracker page collapses this to **one row per label**,
keeping whichever row appears **last in the sheet** for that label.

---

## 3. Status Rules

**Agreement Status** (computed on Sheet 1, reused everywhere by label
lookup — never recalculated on Sheet 2):

| Status | Rule |
|---|---|
| Expired | `Expiry Date < Today` |
| Expires Today | `Expiry Date == Today` |
| Expiring Soon | `0 < Days Remaining <= 30` |
| Active | `Days Remaining > 30` |
| Unknown | Missing/invalid date, or label not found on Sheet 1 |

Label matching between sheets (`TV Studios` ↔ `Label Name`) is
case-insensitive and whitespace-trimmed.

---

## 4. Installation & Running

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt

streamlit run app.py
```

Opens at `http://localhost:8501`. The Report Tracker page appears
automatically in the sidebar (from `pages/`).

---

## 5. Page Features

**Agreement Monitor**
- KPI cards, status pie chart, monthly expiry bar chart.
- Searchable, color-coded table of all agreements.
- Filters: label search, status.

**Report Tracker**
- One row per label (most recent Sheet 2 entry only).
- KPI cards + pie chart by Agreement Status.
- Table shows: Label (color-coded by Agreement Status), Period, Agreement
  Status. `Report Date`, `Shared with CP`, and Report Status are not
  shown on this page.
- Filters: Agreement Status, Period.

---

## 6. Notes on Data Handling

- Sheet 1 dates parse cleanly via `pd.to_datetime(errors="coerce")`.
- Sheet 2's date-like columns (`Report Date`, `Approval to MIS`, etc.) may
  be stored as raw Excel serial numbers rather than real dates — not an
  issue today since Report Tracker no longer displays or sorts by them,
  but will need handling if those columns are used in a future module.
- Both sheets are cached with `st.cache_data`; restart the app to pick up
  changes to `Agreements.xlsx`.

---

## 7. Future Extensibility (Not Yet Implemented)

- 📊 Revenue Summary (unused Sheet 2 columns: Net Revenue, Payout,
  Invoice fields, etc.)
- ✅ Approval Tracking
- 📧 Automated Email Notifications
- 📤 Automatic Report Dispatch

Pattern for adding a module: constants in `config.py` → logic in
`utils.py` → rendering in a new `<module>.py` → entry point in `pages/`.