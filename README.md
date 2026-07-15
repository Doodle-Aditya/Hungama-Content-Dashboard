# Content Operations Dashboard — User Guide

🔗 **Live App:** [master-label-page.streamlit.app](https://master-label-page.streamlit.app/)

This tool helps Legal, Finance, and MIS teams keep track of two things:

1. **Which label agreements are active, expiring soon, or already expired**
2. **Which labels' reports have been shared, and their approval status**

No installation or Excel formulas needed on your end — you just upload the
latest files and the dashboard does the rest.

---

## 1. What You'll Need

Two Excel workbooks, both `.xlsx`:

| Workbook | Used for |
|---|---|
| **Master Label Dashboard** | Agreement dates, status, approval info |
| **Revenue Summary** | Report sharing / period tracking |

You don't need to prepare or clean these — just upload the latest version
you have. The dashboard reads specific sheets and columns from each (see
below); everything else in the file is ignored and won't cause errors.

### Master Label Dashboard — what the dashboard looks for
- A sheet named **`Master`**
- Columns named exactly: **`Label Name`**, **`Start Date`**, **`End Date`**
- Optional column **`Approval upto`** (a date) — if present, it's shown as
  a friendly "Month Year" label (e.g. a cell showing `31-03-2025` becomes
  **"March 2025"**)

### Revenue Summary — what the dashboard looks for
- A sheet named **`Reports Update`**
- Columns named exactly: **`TV Studios`**, **`Period`**, **`Report Date`**,
  **`Shared with CP`**

If a required sheet or column is missing, the app will tell you exactly
what's missing instead of crashing — just fix the file and re-upload.

---

## 2. How to Use It

1. Open the [live app](https://master-label-page.streamlit.app/).
2. In the sidebar, you'll see upload boxes. Upload your **Master Label
   Dashboard** file and (on the Report Tracker page) your **Revenue
   Summary** file.
3. The dashboard updates immediately — no further steps needed.
4. Got a newer file later? Just upload it again in the same sidebar box —
   it replaces the old one right away.

**Note:** uploads only last for your current session. If you close the
app or leave it open too long without using it, you'll need to upload the
files again next time.

---

## 3. Page 1 — Agreement Monitor

Shows every label's agreement status, computed automatically from
`Start Date` and `End Date`:

| Status | Meaning |
|---|---|
| 🟢 **Active** | More than 30 days remain |
| 🟡 **Expiring Soon** | 30 days or fewer remain |
| 🟠 **Expires Today** | Ends today |
| 🔴 **Expired** | End date has already passed |
| ⚪ **Unknown** | Dates missing or unreadable in the source file |

**What's on the page:**
- Summary cards at the top (total labels, active, expired, etc.)
- A pie chart of status distribution and a bar chart of expiries by month
- A searchable table of every label, with Approval Month shown last
- An **Export filtered data (Excel)** button that downloads exactly what's
  currently showing in the table below it

**Filters (sidebar):**
- **Search Label** — type any part of a label name
- **Status Filter** — show only one status at a time (or all)
- **Approval Month** — show only labels with a specific approval month

---

## 4. Page 2 — Report Tracker

Shows **one row per label** — if a label appears many times in the
Revenue Summary file (e.g. once per reporting period), only its most
recent entry is shown, so the list doesn't get cluttered with duplicates.

Each row also shows that label's Agreement Status, pulled in automatically
from the Master Label Dashboard file by matching label names (so upload
both files for full information — if the Master Label Dashboard hasn't
been uploaded yet, Agreement Status just shows as "Unknown").

An **Export filtered data (Excel)** button above the table downloads
exactly what's currently showing, after filters are applied.

**Filters (sidebar):**
- **Agreement Status** — Active / Expiring Soon / Expires Today / Expired / Unknown
- **Period** — a specific reporting period from the Revenue Summary file
- **Approval Month** — same as on the Agreement Monitor page

---

## 5. Troubleshooting

- **"No data found" / missing column warning** — the uploaded file is
  either the wrong workbook, or a sheet/column name doesn't match what's
  listed in Section 1. Sheet and column names must match exactly
  (including capitalization and spacing).
- **A label shows "Unknown" status** — either its dates are missing/
  invalid in the source file, or (on the Report Tracker page) its name
  doesn't match a label in the Master Label Dashboard file closely enough
  to be linked automatically.
- **Approval Month shows "—"** — that label's `Approval upto` cell was
  blank or not a real date in the source file.
- **My upload disappeared** — sessions don't persist between visits;
  re-upload both files whenever you return to the app.

---

## Credits

Made by **Aditya Nishad** for **Hungama Digital Infotainment Pvt Ltd**.
[Github](github.com/doodle-aditya)
[E-mail](mailto:adityanishad98196@gmail.com)