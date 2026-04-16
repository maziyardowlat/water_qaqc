"""
Generate the Water Temperature QAQC App How-To Guide PDF.
Run with: python generate_howto_pdf.py
Output: water_temp_app/Water_Temp_QAQC_HowTo.pdf
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import ListFlowable, ListItem
import os

OUTPUT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "water_temp_app",
    "Water_Temp_QAQC_HowTo.pdf"
)

REPO_URL = "https://github.com/maziyardowlat/water_qaqc"
LAB_SHORT = "UNBC - NHG"
LAB_LONG  = ("Northern Hydrometeorology Group (NHG), "
             "University of Northern British Columbia (UNBC), "
             "Prince George, British Columbia, Canada")

# ── Colour palette ────────────────────────────────────────────────────────────
UNBC_GREEN   = colors.HexColor("#006633")
UNBC_GOLD    = colors.HexColor("#FFC629")
LIGHT_GREEN  = colors.HexColor("#E8F5E9")
LIGHT_GOLD   = colors.HexColor("#FFF8E1")
LIGHT_GREY   = colors.HexColor("#F5F5F5")
MID_GREY     = colors.HexColor("#BDBDBD")
DARK_GREY    = colors.HexColor("#424242")
WHITE        = colors.white
FLAG_PASS    = colors.HexColor("#C8E6C9")  # green
FLAG_FAIL    = colors.HexColor("#FFCDD2")  # red

# ── Styles ────────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

def S(name, **kwargs):
    """Create a named ParagraphStyle."""
    return ParagraphStyle(name, **kwargs)

Title       = S("DocTitle",    fontSize=26, textColor=WHITE,        alignment=TA_CENTER,
                leading=32,    spaceAfter=6,  fontName="Helvetica-Bold")
SubTitle    = S("DocSubTitle", fontSize=13, textColor=UNBC_GOLD,    alignment=TA_CENTER,
                leading=18,    spaceAfter=4,  fontName="Helvetica")
H1          = S("H1",          fontSize=16, textColor=WHITE,        leading=20,
                spaceBefore=18, spaceAfter=6, fontName="Helvetica-Bold")
H2          = S("H2",          fontSize=13, textColor=UNBC_GREEN,   leading=17,
                spaceBefore=14, spaceAfter=5, fontName="Helvetica-Bold",
                borderPad=4)
H3          = S("H3",          fontSize=11, textColor=DARK_GREY,    leading=14,
                spaceBefore=10, spaceAfter=4, fontName="Helvetica-Bold")
Body        = S("Body",        fontSize=10, textColor=DARK_GREY,    leading=14,
                spaceBefore=2,  spaceAfter=4, fontName="Helvetica",
                alignment=TA_JUSTIFY)
BodyBold    = S("BodyBold",    fontSize=10, textColor=DARK_GREY,    leading=14,
                spaceBefore=2,  spaceAfter=4, fontName="Helvetica-Bold")
Note        = S("Note",        fontSize=9,  textColor=colors.HexColor("#37474F"),
                leading=13,    spaceBefore=4, spaceAfter=4,
                fontName="Helvetica-Oblique", leftIndent=12)
Code        = S("Code",        fontSize=8.5, textColor=colors.HexColor("#1A237E"),
                leading=12,    spaceBefore=2, spaceAfter=2,
                fontName="Courier", leftIndent=18, backColor=LIGHT_GREY)
TblHeader   = S("TblHdr",      fontSize=9,  textColor=WHITE,        leading=12,
                alignment=TA_CENTER, fontName="Helvetica-Bold")
TblCell     = S("TblCell",     fontSize=9,  textColor=DARK_GREY,    leading=12,
                alignment=TA_LEFT,   fontName="Helvetica")
TblCellC    = S("TblCellC",    fontSize=9,  textColor=DARK_GREY,    leading=12,
                alignment=TA_CENTER, fontName="Helvetica")

def bullet_list(items, style=Body, bullet_char="\u2022"):
    return ListFlowable(
        [ListItem(Paragraph(i, style), leftIndent=18, bulletIndent=6) for i in items],
        bulletType="bullet",
        bulletFontName="Helvetica",
        bulletFontSize=10,
        bulletColor=UNBC_GREEN,
        leftIndent=18,
        spaceAfter=2,
    )

def numbered_list(items, style=Body):
    return ListFlowable(
        [ListItem(Paragraph(i, style), leftIndent=24, bulletIndent=6) for i in items],
        bulletType="1",
        bulletFontName="Helvetica",
        bulletFontSize=10,
        bulletColor=UNBC_GREEN,
        leftIndent=18,
        spaceAfter=2,
    )

def section_header(text, level=1):
    if level == 1:
        bg = UNBC_GREEN
        st = H1
    else:
        bg = colors.HexColor("#004D26")
        st = H1
    tbl = Table([[Paragraph(text, st)]], colWidths=[6.5 * inch])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ("ROUNDEDCORNERS", [4]),
    ]))
    return tbl

def info_box(text, bg=LIGHT_GREEN, border=UNBC_GREEN):
    tbl = Table([[Paragraph(text, Note)]], colWidths=[6.5 * inch])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), bg),
        ("LINEAFTER",     (0, 0), (0, -1), 3, border),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    return tbl

def warning_box(text):
    return info_box(
        "<b>Important: </b>" + text,
        bg=LIGHT_GOLD,
        border=UNBC_GOLD
    )

def step_table(steps):
    rows = []
    for i, (title, detail) in enumerate(steps):
        rows.append([
            Paragraph(f"<b>{i+1}</b>", TblCellC),
            Paragraph(f"<b>{title}</b>", TblCell),
            Paragraph(detail, TblCell),
        ])
    tbl = Table(rows, colWidths=[0.35 * inch, 1.6 * inch, 4.55 * inch])
    style = [
        ("BACKGROUND",    (0, 0), (-1, -1), WHITE),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT_GREY]),
        ("LINEBELOW",     (0, 0), (-1, -1), 0.5, MID_GREY),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("FONTNAME",      (0, 0), (0, -1),  "Helvetica-Bold"),
        ("TEXTCOLOR",     (0, 0), (0, -1),  UNBC_GREEN),
        ("FONTSIZE",      (0, 0), (0, -1),  12),
        ("ALIGN",         (0, 0), (0, -1),  "CENTER"),
        ("BOX",           (0, 0), (-1, -1), 0.5, MID_GREY),
    ]
    tbl.setStyle(TableStyle(style))
    return tbl

def flag_table():
    header = [
        Paragraph("Flag", TblHeader),
        Paragraph("Name", TblHeader),
        Paragraph("Meaning", TblHeader),
    ]
    rows = [
        ("P", "Pass",       "Reading passed all QAQC checks."),
        ("S", "Spike",      "Sudden jump between consecutive readings."),
        ("E", "Error",      "Value outside the acceptable min/max range."),
        ("B", "Below Ice",  "Temperature below 0 \u00b0C — possible logger buried in ice."),
        ("T", "High Temp",  "Temperature above the high threshold (default 35\u00b0C)."),
        ("A", "Diurnal",    "Daily temperature swing too large — possible air exposure."),
        ("M", "Missing",    "Gap in record; row was padded with NaN."),
        ("V", "Visit",      "Data recorded during a field visit window."),
        ("AVG", "Average",  "Annual only: record is an average of two loggers."),
        ("C", "Caution",    "Annual only: averaged from two failed records."),
    ]
    flag_bg = {
        "P": FLAG_PASS, "S": FLAG_FAIL, "E": FLAG_FAIL,
        "B": colors.HexColor("#E3F2FD"), "T": FLAG_FAIL,
        "A": colors.HexColor("#FFF3E0"), "M": LIGHT_GREY,
        "V": colors.HexColor("#EDE7F6"), "AVG": FLAG_PASS,
        "C": colors.HexColor("#FFF3E0"),
    }
    data = [header]
    style = [
        ("BACKGROUND",    (0, 0), (-1, 0), UNBC_GREEN),
        ("LINEBELOW",     (0, 0), (-1, 0), 1, WHITE),
        ("BOX",           (0, 0), (-1, -1), 0.5, MID_GREY),
        ("LINEBELOW",     (0, 0), (-1, -1), 0.3, MID_GREY),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]
    for i, (flag, name, meaning) in enumerate(rows):
        r = i + 1
        bg = flag_bg.get(flag, WHITE)
        data.append([
            Paragraph(f"<b>{flag}</b>", TblCellC),
            Paragraph(name, TblCell),
            Paragraph(meaning, TblCell),
        ])
        style.append(("BACKGROUND", (0, r), (0, r), bg))

    tbl = Table(data, colWidths=[0.6 * inch, 1.1 * inch, 4.8 * inch])
    tbl.setStyle(TableStyle(style))
    return tbl

# ── Page template ─────────────────────────────────────────────────────────────
def on_first_page(canvas, doc):
    canvas.saveState()
    w, h = letter
    canvas.setFillColor(UNBC_GREEN)
    canvas.rect(0, h - 2.4 * inch, w, 2.4 * inch, fill=1, stroke=0)
    canvas.setFillColor(UNBC_GOLD)
    canvas.rect(0, h - 2.42 * inch, w, 0.06 * inch, fill=1, stroke=0)
    canvas.setFillColor(MID_GREY)
    canvas.rect(0, 0, w, 0.45 * inch, fill=1, stroke=0)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(DARK_GREY)
    canvas.drawString(0.75 * inch, 0.16 * inch,
        f"Water Temperature QAQC App  \u2014  How-To Guide  \u2014  {LAB_SHORT}")
    canvas.restoreState()

def on_later_pages(canvas, doc):
    canvas.saveState()
    w, h = letter
    canvas.setFillColor(UNBC_GREEN)
    canvas.rect(0, h - 0.45 * inch, w, 0.45 * inch, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(WHITE)
    canvas.drawString(0.75 * inch, h - 0.29 * inch, "Water Temperature QAQC App — How-To Guide")
    canvas.setFillColor(LIGHT_GREY)
    canvas.rect(0, 0, w, 0.45 * inch, fill=1, stroke=0)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(DARK_GREY)
    canvas.drawRightString(w - 0.75 * inch, 0.16 * inch, f"Page {doc.page}")
    canvas.drawString(0.75 * inch, 0.16 * inch, LAB_SHORT)
    canvas.restoreState()

# ── Build document ────────────────────────────────────────────────────────────
def build_pdf():
    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.65 * inch,
    )

    story = []

    # ── TITLE PAGE ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.45 * inch))
    story.append(Paragraph("Water Temperature QAQC App", Title))
    story.append(Spacer(1, 0.05 * inch))
    story.append(Paragraph("How-To Guide", SubTitle))
    story.append(Spacer(1, 0.05 * inch))
    story.append(Paragraph(LAB_SHORT, SubTitle))
    story.append(Spacer(1, 0.5 * inch))

    story.append(Paragraph(
        f"<i>{LAB_LONG}</i>", Note))
    story.append(Spacer(1, 0.15 * inch))

    overview_data = [
        [Paragraph("<b>What this guide covers</b>", H3)],
        [bullet_list([
            "Installing Python, downloading the app, and setting up a virtual environment "
            "(Windows &amp; Mac)",
            "The <b>UNBC OneDrive workflow</b> for managed station data",
            "The <b>standalone workflow</b> — dragging your own raw and tidy files in",
            "Step-by-step instructions for all <b>five modules</b>",
            "Using <b>FastField PDF forms</b> to auto-detect field visit times",
            "A complete <b>data flags reference</b>",
            "Common <b>troubleshooting</b> (PowerShell, Python, OneDrive, etc.)",
        ])],
    ]
    ov_tbl = Table(overview_data, colWidths=[6.5 * inch])
    ov_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), LIGHT_GREEN),
        ("LINEAFTER",     (0, 0), (0, -1), 4, UNBC_GREEN),
        ("BOX",           (0, 0), (-1, -1), 0.5, UNBC_GREEN),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
    ]))
    story.append(ov_tbl)
    story.append(Spacer(1, 0.25 * inch))

    story.append(Paragraph("The Five-Step Workflow", H2))
    wf_header = [
        Paragraph("Step", TblHeader),
        Paragraph("Module", TblHeader),
        Paragraph("What it does", TblHeader),
    ]
    wf_rows = [
        ("1", "Format Data",   "Converts raw logger CSV into a standardised format with metadata."),
        ("2", "Flag & Compile","Applies automated quality checks and assigns a flag to each reading."),
        ("3", "Review",        "Interactive plot to inspect flags and make manual corrections."),
        ("4", "Report",        "Generates a summary statistics report for a single file."),
        ("5", "Annual",        "Combines multiple files into a compiled annual dataset and report."),
    ]
    wf_data = [wf_header]
    for step, mod, desc in wf_rows:
        wf_data.append([
            Paragraph(f"<b>{step}</b>", TblCellC),
            Paragraph(f"<b>{mod}</b>",  TblCell),
            Paragraph(desc, TblCell),
        ])
    wf_tbl = Table(wf_data, colWidths=[0.4 * inch, 1.4 * inch, 4.7 * inch])
    wf_tbl.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  UNBC_GREEN),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
        ("BOX",            (0, 0), (-1, -1), 0.5, MID_GREY),
        ("LINEBELOW",      (0, 0), (-1, -1), 0.3, MID_GREY),
        ("TOPPADDING",     (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 6),
        ("LEFTPADDING",    (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 6),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",          (0, 0), (0, -1),  "CENTER"),
        ("FONTSIZE",       (0, 1), (0, -1),  12),
        ("TEXTCOLOR",      (0, 1), (0, -1),  UNBC_GREEN),
    ]))
    story.append(wf_tbl)
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # PART 1 — INSTALL & RUN (COMMON)
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(section_header("Part 1 — Installing and Running the App"))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(
        "This section applies to <b>everyone</b> — whether you are on a UNBC-managed "
        "Windows computer or your own Mac/PC. Do this once the first time you set up. "
        "After the initial install, launching the app is just two commands.",
        Body))
    story.append(Spacer(1, 0.1 * inch))

    # ── Step 1: Python ────────────────────────────────────────────────────────
    story.append(Paragraph("Step 1 — Make sure Python is installed", H2))
    story.append(Paragraph(
        "The app runs on Python (version 3.11 or newer). To check if Python is already "
        "installed, open a terminal and type:", Body))
    story.append(Paragraph("python --version", Code))
    story.append(Paragraph(
        "On Windows, the terminal is <b>PowerShell</b> (search for it in the Start menu). "
        "On Mac, it is <b>Terminal</b> (Applications \u2192 Utilities). "
        "If you see a version number like <i>Python 3.11.4</i>, you are set — skip to Step 2.",
        Body))
    story.append(Spacer(1, 0.08 * inch))

    story.append(Paragraph("If Python is missing — UNBC Windows computers", H3))
    story.append(Paragraph(
        "UNBC-managed Windows devices <b>should come with Python pre-installed</b>. "
        "If yours does not, try these in order:", Body))
    story.append(numbered_list([
        'Open the <b>UNBC Software Center</b> (or <b>Approval Portal</b>) from the Start menu '
        'and search for <b>Python 3</b>. Request and install from there.',
        'If Software Center does not list Python, contact <b>UNBC IT Services</b> and '
        'request Python 3.11 (or newer) be installed on your machine.',
        'As a last resort on a personal or loaner machine, download it yourself from '
        '<b>python.org/downloads</b>.',
    ]))
    story.append(Spacer(1, 0.06 * inch))
    story.append(warning_box(
        'If you install from python.org yourself, on the first installer screen '
        '<b>tick "Add Python to PATH"</b> before clicking Install Now. '
        'If you miss this, the <font name="Courier" size="8.5">python</font> and '
        '<font name="Courier" size="8.5">pip</font> commands will not work in PowerShell.'
    ))
    story.append(Spacer(1, 0.08 * inch))

    story.append(Paragraph("If Python is missing — Mac", H3))
    story.append(Paragraph(
        "macOS comes with an old Python that is not recommended. Install a current version "
        "from <b>python.org/downloads</b> (download the macOS installer and run it), "
        "or use Homebrew:", Body))
    story.append(Paragraph("brew install python@3.11", Code))
    story.append(Spacer(1, 0.12 * inch))

    # ── Step 2: Download ZIP ──────────────────────────────────────────────────
    story.append(Paragraph("Step 2 — Download the app from GitHub", H2))
    story.append(numbered_list([
        f'In your browser, go to <b>{REPO_URL}</b>.',
        'Click the green <b>&lt;&gt; Code</b> button near the top right of the file list.',
        'In the dropdown, click <b>Download ZIP</b>.',
        'Save the ZIP file to a location you can find easily — your <b>Desktop</b> or '
        '<b>Documents</b> folder work well.',
        '<b>Extract</b> the ZIP:<br/>'
        '&nbsp;&nbsp;\u2022 <b>Windows:</b> right-click the ZIP \u2192 <b>Extract All...</b> '
        '\u2192 pick a destination \u2192 Extract.<br/>'
        '&nbsp;&nbsp;\u2022 <b>Mac:</b> double-click the ZIP and it extracts automatically.',
        'Open the extracted folder. You should see files including <b>requirements.txt</b> '
        'and <b>app.py</b>.',
    ]))
    story.append(Spacer(1, 0.06 * inch))
    story.append(info_box(
        'Keep the extracted folder where it is after setup — moving it later breaks the '
        'virtual environment paths, and you will have to redo Step 3. '
        'Pick a permanent home first (e.g., <b>Documents\\water_qaqc\\</b>).'
    ))
    story.append(Spacer(1, 0.12 * inch))

    # ── Step 3: Virtual Environment ───────────────────────────────────────────
    story.append(Paragraph("Step 3 — Create a virtual environment and install requirements", H2))
    story.append(Paragraph(
        "A virtual environment (\"venv\") is an isolated Python workspace that keeps this "
        "app's packages separate from everything else on your computer. You only need to "
        "create it <b>once</b>. After that, you just activate and launch.", Body))
    story.append(Spacer(1, 0.08 * inch))

    # Windows sub-section
    story.append(Paragraph("Windows (PowerShell)", H3))
    story.append(numbered_list([
        'Open <b>File Explorer</b> and navigate into the extracted app folder — the one '
        'containing <b>requirements.txt</b>.',
        'Hold <b>Shift</b> and <b>right-click</b> on an empty area inside that folder, '
        'then choose <b>"Open in Terminal"</b> or <b>"Open PowerShell window here"</b>. '
        '(Alternatively: click the address bar, type <b>powershell</b>, press Enter.)',
        'Create the virtual environment by running:',
    ]))
    story.append(Paragraph("python -m venv venv", Code))
    story.append(numbered_list([
        'Activate the virtual environment:',
    ]))
    story.append(Paragraph(".\\venv\\Scripts\\activate.ps1", Code))
    story.append(Paragraph(
        "Your PowerShell prompt should now start with <b>(venv)</b>. That means the venv is "
        "active and any Python commands will use it.", Body))
    story.append(Spacer(1, 0.04 * inch))
    story.append(warning_box(
        'If you see a red error like <i>"running scripts is disabled on this system"</i>, '
        'PowerShell\'s execution policy is blocking the script. Run this once '
        '(in the <b>same</b> PowerShell window) and then try the activate command again:<br/>'
        '<font name="Courier" size="8.5">Set-ExecutionPolicy -Scope CurrentUser RemoteSigned</font><br/>'
        'If that is also blocked by your IT policy, use this fallback instead — it activates '
        'the venv for just this one session without changing any settings:<br/>'
        '<font name="Courier" size="8.5">.\\venv\\Scripts\\Activate.bat</font><br/>'
        'Or, from Command Prompt (cmd.exe) instead of PowerShell:<br/>'
        '<font name="Courier" size="8.5">venv\\Scripts\\activate</font>'
    ))
    story.append(Spacer(1, 0.05 * inch))
    story.append(numbered_list([
        'With the venv active, install the required packages:',
    ]))
    story.append(Paragraph("pip install -r requirements.txt", Code))
    story.append(Paragraph(
        "This downloads Streamlit, pandas, plotly, and everything else the app needs. "
        "It takes a few minutes the first time. You only run this once.", Body))
    story.append(Spacer(1, 0.12 * inch))

    # Mac sub-section
    story.append(Paragraph("Mac (Terminal)", H3))
    story.append(numbered_list([
        'Open <b>Terminal</b> (Applications \u2192 Utilities \u2192 Terminal, or Cmd+Space '
        'and type "terminal").',
        'Navigate into the extracted app folder. The easiest way: type '
        '<b>cd</b> followed by a space, then drag the folder from Finder onto the Terminal '
        'window and press Enter. Example:',
    ]))
    story.append(Paragraph("cd ~/Documents/water_qaqc", Code))
    story.append(numbered_list([
        'Create the virtual environment:',
    ]))
    story.append(Paragraph("python3 -m venv venv", Code))
    story.append(numbered_list([
        'Activate it:',
    ]))
    story.append(Paragraph("source venv/bin/activate", Code))
    story.append(Paragraph(
        "Your prompt should now start with <b>(venv)</b>.", Body))
    story.append(numbered_list([
        'Install the requirements:',
    ]))
    story.append(Paragraph("pip install -r requirements.txt", Code))
    story.append(Spacer(1, 0.12 * inch))

    # ── Step 4: Run ───────────────────────────────────────────────────────────
    story.append(Paragraph("Step 4 — Launch the app", H2))
    story.append(Paragraph(
        "With the virtual environment active (you should see <b>(venv)</b> at the start of "
        "your terminal prompt), start the app:", Body))
    story.append(Paragraph("streamlit run app.py", Code))
    story.append(Paragraph(
        "The app opens automatically in your default browser at "
        "<b>http://localhost:8501</b>. If it does not open on its own, copy that URL into "
        "any browser.", Body))
    story.append(Spacer(1, 0.06 * inch))
    story.append(warning_box(
        'Keep the terminal window open while using the app. Closing it stops the app. '
        'You can minimise the window freely — just do not close it.'
    ))
    story.append(Spacer(1, 0.08 * inch))

    story.append(Paragraph("Coming back next time", H3))
    story.append(Paragraph(
        "After the first-time setup, your routine is just:", Body))
    story.append(numbered_list([
        'Open PowerShell (Windows) or Terminal (Mac) <b>in the app folder</b>.',
        'Activate the venv: '
        '<font name="Courier" size="8.5">.\\venv\\Scripts\\activate.ps1</font> '
        '(Windows) or '
        '<font name="Courier" size="8.5">source venv/bin/activate</font> (Mac).',
        'Run: <font name="Courier" size="8.5">streamlit run app.py</font>.',
    ]))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # PART 2 — ONEDRIVE WORKFLOW
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(section_header("Part 2 — UNBC OneDrive Workflow"))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(
        "Use this workflow when working on a UNBC-managed computer that has OneDrive "
        "synced with the <b>NHG Field \u2013 Data Management</b> folder. In this mode, "
        "the app automatically finds your station folder and writes outputs back into it "
        "— no browsing or drag-and-drop needed.",
        Body))
    story.append(Spacer(1, 0.12 * inch))

    story.append(Paragraph("Configuring the OneDrive integration", H2))
    story.append(Paragraph(
        "Once the app is open in your browser (see Part 1, Step 4), look at the "
        "<b>left sidebar</b>:", Body))
    story.append(numbered_list([
        'Check the box labelled <b>"Use with UNBC OneDrive"</b>.',
        'Enter your <b>UNBC username</b> — the part before the @ in your UNBC email '
        '(e.g., <b>dowlataba</b>).',
        'Enter the <b>Station Code</b> you are processing '
        '(e.g., <b>02FW006</b> or <b>qrrc_water</b>).',
        'The app resolves your station folder automatically and sets the project directory.',
    ]))
    story.append(Spacer(1, 0.06 * inch))
    story.append(info_box(
        'The app looks for your station folder at:<br/>'
        '<font name="Courier" size="8.5">C:\\Users\\[username]\\OneDrive - UNBC\\'
        'NHG Field - Data Management\\02_Stations\\[station_code]*\\</font>'
    ))
    story.append(Spacer(1, 0.12 * inch))

    story.append(Paragraph("Where files are saved", H2))
    story.append(Paragraph(
        "With OneDrive mode active, all outputs are written directly into the station "
        "folder and sync automatically:", Body))
    folder_data = [
        [Paragraph("Subfolder", TblHeader), Paragraph("Contents", TblHeader)],
        [Paragraph("01_Data\\01_Raw_Formatted\\", Code), Paragraph("Formatted CSV files (after Format Data step)", TblCell)],
        [Paragraph("01_Data\\02_Tidy\\",           Code), Paragraph("Quality-checked (flagged) CSV files",          TblCell)],
        [Paragraph("01_Data\\03_Compiled\\",       Code), Paragraph("Annual compiled datasets",                     TblCell)],
        [Paragraph("03_Reports\\",                 Code), Paragraph("Individual HTML reports",                      TblCell)],
        [Paragraph("03_Reports\\03_Annual\\",      Code), Paragraph("Annual HTML reports",                          TblCell)],
    ]
    folder_tbl = Table(folder_data, colWidths=[2.8 * inch, 3.7 * inch])
    folder_tbl.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  UNBC_GREEN),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
        ("BOX",            (0, 0), (-1, -1), 0.5, MID_GREY),
        ("LINEBELOW",      (0, 0), (-1, -1), 0.3, MID_GREY),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 6),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(folder_tbl)
    story.append(Spacer(1, 0.12 * inch))
    story.append(info_box(
        'Because everything writes through OneDrive, other NHG members with access to the '
        'same station folder will see your formatted, tidy, and compiled files as soon as '
        'OneDrive finishes syncing.'
    ))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # PART 3 — STANDALONE WORKFLOW
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(section_header("Part 3 — Standalone Workflow (Outside UNBC OneDrive)"))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(
        "Use this workflow on a personal laptop, on a computer without OneDrive, or "
        "whenever you are working with data <b>outside</b> the standard UNBC station "
        "folder structure. Instead of the app auto-finding your files, you drag them in "
        "yourself and the app saves outputs to a project folder you choose.", Body))
    story.append(Spacer(1, 0.12 * inch))

    story.append(KeepTogether([
        Paragraph("Step 1 — Create a project folder", H2),
        Paragraph(
            "Create a new empty folder anywhere on your computer for this project. "
            "For example:", Body),
        Paragraph("Documents/TemperatureData_2024/", Code),
        Paragraph(
            "You do not need to create any subfolders — the app creates "
            "<b>01_Data</b> and <b>03_Reports</b> automatically the first time you save a file.",
            Body),
        Spacer(1, 0.05 * inch),
    ]))

    story.append(KeepTogether([
        Paragraph("Step 2 — Point the app at your project folder", H2),
        numbered_list([
            'In the left sidebar, make sure <b>"Use with UNBC OneDrive"</b> is '
            '<b>unchecked</b>.',
            'Paste the full path to your project folder into the <b>Project Directory</b> '
            'field. On Windows you can copy the path from File Explorer\'s address bar; on '
            'Mac, right-click the folder with Option held and choose "Copy as Pathname".',
            'The directory is remembered for the duration of your session.',
        ]),
        Spacer(1, 0.05 * inch),
    ]))

    story.append(KeepTogether([
        Paragraph("Step 3 — Drag in your raw files", H2),
        Paragraph(
            "In the <b>Format Data</b> module, instead of selecting from a dropdown you "
            "use the file uploader:", Body),
        numbered_list([
            'Click <b>"Browse files"</b> in the upload area <b>or</b> drag and drop your '
            'raw logger file (CSV, TXT, or XLSX) straight from File Explorer / Finder onto '
            'the upload zone.',
            'A preview of the data appears immediately.',
            'Continue with the Format Data steps (see Part 4, Module 1).',
        ]),
        info_box(
            'Accepted formats: <b>.csv</b>, <b>.txt</b>, <b>.xlsx</b>. Most logger software '
            '(HOBOware, Onset, Solinst, etc.) exports CSV by default.'
        ),
        Spacer(1, 0.05 * inch),
    ]))

    story.append(KeepTogether([
        Paragraph("Step 4 — Drag in your tidy files (if continuing from elsewhere)", H2),
        Paragraph(
            "If you already have tidy files from a previous deployment — for example, "
            "files shared by a collaborator or pulled from an older project — drop them "
            "into the Flag &amp; Compile or Annual modules the same way:", Body),
        bullet_list([
            'In <b>Flag &amp; Compile</b>, the "Previous Tidy File" uploader accepts a '
            'previously-flagged CSV for Sequential or Logger Swap continuity.',
            'In <b>Annual</b>, the multi-file uploader accepts multiple tidy CSVs at once — '
            'drag them all in together.',
            'In <b>Review</b> and <b>Report</b>, drag a single tidy CSV in to inspect or '
            'generate a report.',
        ]),
        Spacer(1, 0.05 * inch),
    ]))

    story.append(KeepTogether([
        Paragraph("Step 5 — Where files are saved", H2),
        Paragraph("Files are saved inside the project folder you chose in Step 1:", Body),
        Paragraph(
            "TemperatureData_2024/\n"
            "  01_Data/01_Raw_Formatted/   \u2190 Formatted CSV files\n"
            "  01_Data/02_Tidy/            \u2190 Flagged CSV files\n"
            "  01_Data/03_Compiled/        \u2190 Annual compiled datasets\n"
            "  03_Reports/                 \u2190 Individual HTML reports\n"
            "  03_Reports/03_Annual/       \u2190 Annual HTML reports",
            Code),
        Spacer(1, 0.05 * inch),
    ]))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # PART 4 — MODULE WALKTHROUGHS
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(section_header("Part 4 — Module-by-Module Walkthrough"))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(
        "Work through the modules in order for each dataset: "
        "Format Data \u2192 Flag &amp; Compile \u2192 Review \u2192 Report \u2192 Annual.",
        Body))
    story.append(Spacer(1, 0.1 * inch))

    # MODULE 1
    story.append(Paragraph("Module 1 — Format Data", H2))
    story.append(Paragraph(
        "Converts your raw logger file into the standardised format the app uses for all "
        "downstream processing.", Body))
    story.append(Spacer(1, 0.06 * inch))
    story.append(step_table([
        ("Upload file",
         "Drag in your raw CSV/TXT/XLSX, or pick from the dropdown if using OneDrive mode."),
        ("Set Rows to Skip",
         "Some logger files have extra header lines above the column names. "
         "Increase this number until the column headers appear correctly in the preview. "
         "Common values: 0, 1, or 2."),
        ("Select timestamp column",
         "Choose the column that contains date and time from the dropdown."),
        ("Select temperature column",
         "Choose the water temperature column and rename it to <b>wtmp</b> in the "
         "column-rename field."),
        ("Remove unused columns",
         "Uncheck any columns you do not need (e.g., voltage, light sensors)."),
        ("Timezone conversion",
         "If your data is in local time, check <b>\"Convert Timestamp to UTC?\"</b> "
         "and enter the UTC offset. Common values: "
         "<b>\u20137</b> for Pacific Daylight Time (PDT), "
         "<b>\u20138</b> for Pacific Standard Time (PST), "
         "<b>0</b> if already UTC. "
         "Click <b>Preview Conversion</b> to verify."),
        ("Enter metadata",
         "<b>Station Code</b> — e.g., 02FW006 or qrrc_water<br/>"
         "<b>Logger Serial Number</b> — printed on the logger or in the export filename<br/>"
         "<b>UTC Offset</b> — same value as above<br/>"
         "<b>Data ID</b> — use 999 for new datasets, or a sequential number"),
        ("Enter filename",
         "Short, descriptive, no spaces (e.g., 02FW006_fall2024_formatted). "
         "The app adds .csv automatically."),
        ("Save",
         "Click <b>Save Formatted Data</b>. Written to 01_Data/01_Raw_Formatted/."),
    ]))
    story.append(Spacer(1, 0.1 * inch))

    # MODULE 2
    story.append(Paragraph("Module 2 — Flag &amp; Compile", H2))
    story.append(Paragraph(
        "Applies automated quality checks to each reading and assigns a flag. Pads missing "
        "timestamps with NaN rows and marks field-visit windows.", Body))
    story.append(Spacer(1, 0.06 * inch))
    story.append(step_table([
        ("Select file",
         "Choose your formatted file from the dropdown (OneDrive) or drag it in "
         "(standalone)."),
        ("Review QAQC thresholds",
         "Adjust only if needed for your site. Defaults work well for most BC streams:<br/>"
         "<b>Spike</b> — max change between readings (default: 3\u00b0C)<br/>"
         "<b>Min / Max range</b> — acceptable bounds (default: \u22122\u00b0C to 35\u00b0C)<br/>"
         "<b>Diurnal</b> — max daily swing (default: 10\u00b0C)<br/>"
         "<b>High temp</b> — default: 35\u00b0C"),
        ("Set Data Continuity Mode",
         "<b>First Data Set</b> — standalone file, no history.<br/>"
         "<b>Sequential</b> — adding to existing record from the same logger. Select the "
         "previous tidy file to remove overlapping timestamps.<br/>"
         "<b>Logger Swap</b> — logger was replaced. Select the previous file; the app "
         "matches by station (not serial number)."),
        ("Enter field visit times",
         "See Module 2a below for full details. Visit times flag readings during logger "
         "disturbance as <b>V</b>."),
        ("Run QAQC",
         "Click <b>Run QAQC</b>. A colour-coded scatter plot and flag summary appear."),
        ("Review results",
         "Check the flag distribution. A high proportion of S or A flags may indicate a "
         "threshold that needs adjusting for your site."),
        ("Save",
         "Click <b>Save Flagged Data</b>. Written to 01_Data/02_Tidy/ with a filename "
         "like 02FW006_tidy_21682208_20260416.csv."),
    ]))
    story.append(Spacer(1, 0.1 * inch))

    # Module 2a — FastField
    story.append(Paragraph("Module 2a — Entering Field Visit Times", H3))
    story.append(Paragraph(
        "The app needs to know when a field technician was at the station so it can flag "
        "any readings taken during the visit as <b>V</b> (Visit). There are two ways to "
        "provide this:", Body))
    story.append(Spacer(1, 0.06 * inch))

    ff_data = [
        [Paragraph("<b>Option A: FastField PDF</b>", TblCell),
         Paragraph("<b>Option B: Manual Entry</b>", TblCell)],
        [
            bullet_list([
                "Export the completed field visit form from the FastField app as a PDF.",
                "In Flag &amp; Compile, upload the PDF using the uploader under "
                "<b>\"Field Visit\"</b>.",
                "The app reads the PDF and auto-extracts the visit date, Time-in, Time-out.",
                "If the logger records in local time, tick "
                "<b>\"Convert visit times to UTC\"</b>.",
            ]),
            bullet_list([
                "If no FastField PDF, tick <b>\"No FastField Form\"</b>.",
                "Enter visit <b>date</b>, <b>Time-in</b>, and <b>Time-out</b> manually.",
                "Apply the same UTC conversion checkbox if needed.",
                "Previous visit fields auto-fill from the prior tidy file if available.",
            ]),
        ],
    ]
    ff_tbl = Table(ff_data, colWidths=[3.25 * inch, 3.25 * inch])
    ff_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), UNBC_GREEN),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("BACKGROUND",    (0, 1), (0, 1),  LIGHT_GREEN),
        ("BACKGROUND",    (1, 1), (1, 1),  LIGHT_GOLD),
        ("BOX",           (0, 0), (-1, -1), 0.5, MID_GREY),
        ("LINEAFTER",     (0, 0), (0, -1), 0.5, MID_GREY),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(ff_tbl)
    story.append(Spacer(1, 0.15 * inch))

    # MODULE 3
    story.append(KeepTogether([
        Paragraph("Module 3 — Review", H2),
        Paragraph(
            "Lets you visually inspect the flagged data and manually correct any flags the "
            "automated system got wrong. This is an important quality-control step before "
            "generating reports.", Body),
        Spacer(1, 0.06 * inch),
        step_table([
            ("Load file",
             "Select a tidy file from the dropdown, or drag one in. "
             "The scatter plot loads with readings colour-coded by flag."),
            ("Inspect the plot",
             "Zoom into areas of concern. Hover a point to see exact time and temperature."),
            ("Filter by flag",
             "Use the flag checkboxes to show/hide specific flag types. "
             "Tip: isolate <b>S</b> (Spike) and <b>A</b> (Diurnal) first."),
            ("Edit flags",
             "Find the row in the data table below the plot. Click the <b>wtmp_flag</b> "
             "cell and type the correct flag code. You can also edit the <b>wtmp</b> value "
             "to correct a temperature."),
            ("Add notes",
             "Type a comment in the <b>QAQC Notes</b> box explaining what you changed and "
             "why. Notes are saved with the file."),
            ("Save",
             "Click <b>Save Reviewed Data</b>. The tidy file is updated in-place."),
        ]),
    ]))
    story.append(Spacer(1, 0.1 * inch))

    # MODULE 4
    story.append(KeepTogether([
        Paragraph("Module 4 — Report", H2),
        Paragraph(
            "Generates a summary HTML report for a single tidy file, including statistics "
            "and a time series plot.", Body),
        Spacer(1, 0.06 * inch),
        step_table([
            ("Select file",    "Choose a reviewed tidy file."),
            ("Generate",       "Click <b>Generate Report</b>. A summary appears with pass "
                               "rate, flag distribution, and temperature statistics "
                               "(all data vs. passed data only)."),
            ("Save report",    "Click <b>Save Report</b>. HTML file is written to "
                               "03_Reports/. Open in any browser to view or print."),
        ]),
    ]))
    story.append(Spacer(1, 0.1 * inch))

    # MODULE 5
    story.append(KeepTogether([
        Paragraph("Module 5 — Annual", H2),
        Paragraph(
            "Combines multiple tidy files from the same station — for example, from several "
            "logger deployments across a field season — into a single compiled dataset and "
            "annual report.", Body),
        Spacer(1, 0.06 * inch),
        step_table([
            ("Select files",
             "Hold <b>Ctrl</b> (Windows) or <b>Cmd</b> (Mac) and click all the tidy files "
             "you want to include. Select all files for the same station."),
            ("Duplicate resolution",
             "The app automatically handles overlapping timestamps:<br/>"
             "\u2022 Same logger overlap \u2192 keeps the first record<br/>"
             "\u2022 Two loggers, both passed \u2192 averages the temperatures<br/>"
             "\u2022 One passed, one failed \u2192 keeps the passed record<br/>"
             "\u2022 Both failed \u2192 averages and marks as <b>C</b> (Caution)"),
            ("Review",
             "Check the compiled data table and the daily mean temperature plot."),
            ("Save compiled data",
             "Click <b>Save Compiled Data</b>. Written to 01_Data/03_Compiled/."),
            ("Generate annual report",
             "Click <b>Generate Annual Report</b>. Written to 03_Reports/03_Annual/."),
        ]),
    ]))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # PART 5 — FLAGS REFERENCE
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(section_header("Part 5 — Data Flags Reference"))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(
        "Every temperature reading in a tidy file has a <b>wtmp_flag</b> value. Multiple "
        "flags can be combined alphabetically (e.g., <b>A, S</b>). Only readings flagged "
        "<b>P</b> (Pass) are used in final statistics by default.", Body))
    story.append(Spacer(1, 0.1 * inch))
    story.append(flag_table())
    story.append(Spacer(1, 0.15 * inch))
    story.append(info_box(
        'Combined flags: a reading can have more than one issue. The app lists them '
        'alphabetically, separated by a comma and space (e.g., "A, S" means both a diurnal '
        'anomaly and a spike were detected).'
    ))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # PART 6 — FASTFIELD
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(section_header("Part 6 — Getting FastField Forms"))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(
        "FastField is the mobile app used by field technicians to record station visit "
        "information. The visit form captures arrival time (Time-in) and departure time "
        "(Time-out), which the app uses to flag logger disturbance data as <b>V</b>.", Body))
    story.append(Spacer(1, 0.1 * inch))

    story.append(Paragraph("Exporting a FastField Form as PDF", H2))
    story.append(numbered_list([
        'Open the <b>FastField</b> app on your phone or tablet.',
        'Navigate to <b>Submissions</b> and find the completed form for the station visit.',
        'Tap the form to open it.',
        'Tap the <b>Share / Export</b> button (usually three dots or a share icon).',
        'Select <b>Export as PDF</b>.',
        'Save the PDF to your phone, then transfer it to your computer via OneDrive, '
        'email, or USB.',
    ]))
    story.append(Spacer(1, 0.1 * inch))

    story.append(Paragraph("What the App Extracts from the PDF", H2))
    story.append(Paragraph(
        "The app uses text pattern matching to find these fields in the FastField PDF:", Body))
    ff_extract_data = [
        [Paragraph("Field", TblHeader), Paragraph("Expected format in PDF", TblHeader), Paragraph("Example", TblHeader)],
        [Paragraph("Date", TblCell), Paragraph("YYYY-MM-DD or MM/DD/YY", TblCell), Paragraph("2024-09-15", TblCell)],
        [Paragraph("Time-in", TblCell), Paragraph("Time-in HH:MM", TblCell), Paragraph("Time-in 09:30", TblCell)],
        [Paragraph("Time-out", TblCell), Paragraph("Time-out HH:MM", TblCell), Paragraph("Time-out 11:15", TblCell)],
    ]
    ff_ext_tbl = Table(ff_extract_data, colWidths=[1.2 * inch, 2.5 * inch, 2.8 * inch])
    ff_ext_tbl.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  UNBC_GREEN),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
        ("BOX",            (0, 0), (-1, -1), 0.5, MID_GREY),
        ("LINEBELOW",      (0, 0), (-1, -1), 0.3, MID_GREY),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 6),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(ff_ext_tbl)
    story.append(Spacer(1, 0.1 * inch))
    story.append(warning_box(
        'If the FastField PDF fails to extract the times (e.g., the form layout changed or '
        'the PDF is a scanned image), use <b>Option B — Manual Entry</b> in the Flag &amp; '
        'Compile module and type the times yourself.'
    ))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # PART 7 — TROUBLESHOOTING
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(section_header("Part 7 — Troubleshooting"))
    story.append(Spacer(1, 0.15 * inch))

    problems = [
        ("Python is not recognised / \"python is not a command\"",
         'Either Python is not installed, or it is installed but not on your PATH. '
         'On UNBC Windows devices, check the <b>Software Center</b> / <b>Approval Portal</b> '
         'for Python 3, or contact <b>UNBC IT</b>. On a personal machine, re-run the '
         'python.org installer and tick <b>"Add Python to PATH"</b>. '
         'After installing, <b>close and reopen</b> PowerShell so it picks up the new PATH.'),
        ("PowerShell: \"running scripts is disabled on this system\"",
         'Windows blocks unsigned PowerShell scripts by default, which stops '
         '<font name="Courier" size="8.5">activate.ps1</font> from running. Fix: '
         '<font name="Courier" size="8.5">Set-ExecutionPolicy -Scope CurrentUser RemoteSigned</font>, '
         'then re-run the activate command. If IT has locked that policy down, use one of '
         'these fallbacks: '
         '<font name="Courier" size="8.5">.\\venv\\Scripts\\Activate.bat</font> from '
         'PowerShell, or open <b>Command Prompt (cmd.exe)</b> instead of PowerShell and run '
         '<font name="Courier" size="8.5">venv\\Scripts\\activate</font>.'),
        ("\"Module not found\" or \"No module named streamlit\"",
         'The packages are not installed in the currently active environment. Make sure '
         'your prompt starts with <b>(venv)</b>. If it does not, re-run the activate '
         'command for your OS. Then run '
         '<font name="Courier" size="8.5">pip install -r requirements.txt</font> again.'),
        ("\"streamlit is not recognised\" even after pip install",
         'You likely installed the packages globally rather than inside the venv. Activate '
         'the venv first, then reinstall: '
         '<font name="Courier" size="8.5">pip install -r requirements.txt</font>. '
         'As a fallback, launch the app with '
         '<font name="Courier" size="8.5">python -m streamlit run app.py</font>.'),
        ("OneDrive station folder not found",
         'Check your UNBC username is correct (case-sensitive, no spaces). Make sure '
         'OneDrive is fully synced and the <b>NHG Field \u2013 Data Management</b> folder '
         'is set to be available offline. As a workaround, switch to the standalone mode '
         '(uncheck the OneDrive box) and paste the full path manually.'),
        ("Timestamp parsing errors in Format Data",
         'If you see red error text about dates, try increasing <b>Rows to Skip</b> by 1 '
         'until the preview looks correct. Make sure you selected the column that actually '
         'contains date-time values, not just a date or a serial number.'),
        ("FastField extraction finds no times",
         'Usually means the PDF is a <b>scanned image</b> rather than text-based — the app '
         'cannot read text from images. Use <b>Option B — Manual Entry</b> as a fallback. '
         'If the PDF is text-based but extraction still fails, the form layout may have '
         'changed — enter times manually and flag this for the app maintainer.'),
        ("Files not appearing in dropdowns",
         'Make sure you clicked <b>Save</b> in the previous step. Check the Project '
         'Directory in the sidebar is set to the correct folder. Try refreshing the browser '
         'page (do <b>not</b> close the terminal window).'),
        ("App is very slow or freezes",
         'Large files (more than ~100,000 rows) can slow the app. Process one logger '
         'deployment at a time rather than uploading a very long time series in a single file.'),
        ("Outputs saved in the wrong folder",
         'The app always saves files inside the <b>Project Directory</b> shown in the sidebar. '
         'If files appear in an unexpected location, check the sidebar path and update it.'),
    ]
    for title, detail in problems:
        story.append(KeepTogether([
            Paragraph(title, H3),
            info_box(detail),
            Spacer(1, 0.08 * inch),
        ]))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════════
    # QUICK REFERENCE
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(section_header("Quick Reference — Common UTC Offsets"))
    story.append(Spacer(1, 0.15 * inch))

    tz_data = [
        [Paragraph("Timezone", TblHeader),
         Paragraph("Abbrev.", TblHeader),
         Paragraph("UTC Offset to enter", TblHeader),
         Paragraph("When it applies", TblHeader)],
        ["Pacific Daylight Time", "PDT", "\u20137", "Mid-March to early November"],
        ["Pacific Standard Time", "PST", "\u20138", "Early November to mid-March"],
        ["Mountain Daylight Time", "MDT", "\u20136", "Mid-March to early November"],
        ["Mountain Standard Time", "MST", "\u20137", "Early November to mid-March"],
        ["UTC / Already converted", "UTC", "0", "If your logger records in UTC"],
    ]
    tz_tbl_data = [tz_data[0]]
    for row in tz_data[1:]:
        tz_tbl_data.append([Paragraph(str(c), TblCell) for c in row])

    tz_tbl = Table(tz_tbl_data, colWidths=[1.9 * inch, 0.75 * inch, 1.6 * inch, 2.25 * inch])
    tz_tbl.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  UNBC_GREEN),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
        ("BOX",            (0, 0), (-1, -1), 0.5, MID_GREY),
        ("LINEBELOW",      (0, 0), (-1, -1), 0.3, MID_GREY),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 6),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(tz_tbl)
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Quick Reference — Command Cheat Sheet", H2))
    cheat_data = [
        [Paragraph("Task", TblHeader),
         Paragraph("Windows (PowerShell)", TblHeader),
         Paragraph("Mac (Terminal)", TblHeader)],
        [Paragraph("Create venv", TblCell),
         Paragraph("python -m venv venv", Code),
         Paragraph("python3 -m venv venv", Code)],
        [Paragraph("Activate venv", TblCell),
         Paragraph(".\\venv\\Scripts\\activate.ps1", Code),
         Paragraph("source venv/bin/activate", Code)],
        [Paragraph("Activate (fallback)", TblCell),
         Paragraph(".\\venv\\Scripts\\Activate.bat", Code),
         Paragraph("—", TblCell)],
        [Paragraph("Install packages", TblCell),
         Paragraph("pip install -r requirements.txt", Code),
         Paragraph("pip install -r requirements.txt", Code)],
        [Paragraph("Run app", TblCell),
         Paragraph("streamlit run app.py", Code),
         Paragraph("streamlit run app.py", Code)],
        [Paragraph("Deactivate venv", TblCell),
         Paragraph("deactivate", Code),
         Paragraph("deactivate", Code)],
    ]
    cheat_tbl = Table(cheat_data, colWidths=[1.6 * inch, 2.45 * inch, 2.45 * inch])
    cheat_tbl.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  UNBC_GREEN),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
        ("BOX",            (0, 0), (-1, -1), 0.5, MID_GREY),
        ("LINEBELOW",      (0, 0), (-1, -1), 0.3, MID_GREY),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 6),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(cheat_tbl)
    story.append(Spacer(1, 0.25 * inch))

    story.append(HRFlowable(width="100%", thickness=1, color=MID_GREY))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(
        f"For questions or to report issues with the app, contact the {LAB_SHORT} "
        f"({LAB_LONG}). Repository: {REPO_URL}",
        Note))

    doc.build(
        story,
        onFirstPage=on_first_page,
        onLaterPages=on_later_pages,
    )
    print(f"PDF saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    build_pdf()
