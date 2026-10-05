"""
Builds examples/Sample Services Agreement.docx, the template the tests use
and the one handed to the department as a worked example.

    python tests/sample.py
"""
import pathlib

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "examples" / "Sample Services Agreement.docx"


def numbered(doc, text):
    return doc.add_paragraph(text, style="List Number")


def build(path=OUT):
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    header = doc.sections[0].header.paragraphs[0]
    header.text = "Services Agreement – {{Client Name}}"
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("PROFESSIONAL SERVICES AGREEMENT")
    run.bold = True
    run.font.size = Pt(14)

    # Word often splits a field across runs, as here: the name is bold, the
    # braces are not, and the closing braces sit in a run of their own.
    p = doc.add_paragraph("This Professional Services Agreement (the “Agreement”) is entered into "
                          "as of the ")
    p.add_run("{{Effective Date | date-formal}}")
    p.add_run(" (the “Effective Date”) by and between TMAI (“Provider”) and ")
    p.add_run("{{")
    bold = p.add_run("Client Name")
    bold.bold = True
    p.add_run("}")
    p.add_run("}, a ")
    p.add_run("{{Client Entity Type | choice: corporation, limited liability company, partnership}}")
    p.add_run(" with its principal office at {{Client Address}} (“Client”).")

    numbered(doc, "Services. Provider shall perform the following services: {{Scope of Services | long}}")
    numbered(doc, "Term. This Agreement begins on {{Effective Date | date}} and continues for "
                  "{{Term Months | number-words}} months unless ended earlier under this Agreement.")
    numbered(doc, "Fees. Client shall pay Provider {{Total Fee | money-words}}, invoiced "
                  "{{Billing Frequency | choice: monthly, quarterly, upon completion}}. "
                  "Invoices are due within 30 days{{#if Late Fee}}, and a late fee of "
                  "{{Late Fee | money}} applies to each invoice paid after that{{/if}}.")

    doc.add_paragraph("{{#if Include Non-Compete}}")
    numbered(doc, "Non-Solicitation. During the term and for twelve (12) months after, Client shall not "
                  "solicit for employment any Provider staff assigned to the Services.")
    doc.add_paragraph("{{/if}}")

    doc.add_paragraph("{{#if Governing State = Texas}}")
    numbered(doc, "Governing Law. This Agreement is governed by the laws of the State of Texas, and "
                  "venue lies in Tarrant County.")
    doc.add_paragraph("{{else}}")
    numbered(doc, "Governing Law. This Agreement is governed by the laws of the State of "
                  "{{Governing State | choice: Texas, Oklahoma, Louisiana}}.")
    doc.add_paragraph("{{/if}}")

    numbered(doc, "Notices. Notices to Client go to {{Client Contact}} at {{Client Address}}.")

    doc.add_paragraph("{{#if Guarantor Name}}")
    numbered(doc, "Guarantee. {{Guarantor Name}} guarantees Client’s payment obligations "
                  "under this Agreement.")
    doc.add_paragraph("{{/if}}")

    doc.add_paragraph("Fee schedule:")
    table = doc.add_table(rows=3, cols=2)
    table.style = "Table Grid"
    table.cell(0, 0).text = "Item"
    table.cell(0, 1).text = "Amount"
    table.cell(1, 0).text = "Total fee"
    table.cell(1, 1).text = "{{Total Fee | money}}"
    table.cell(2, 0).text = "Late fee"
    table.cell(2, 1).text = "{{#if Late Fee}}{{Late Fee | money}}{{else}}None{{/if}}"

    doc.add_paragraph()
    doc.add_paragraph("IN WITNESS WHEREOF, the parties have signed this Agreement as of the Effective Date.")
    sig = doc.add_table(rows=4, cols=2)
    sig.cell(0, 0).text = "TMAI"
    sig.cell(0, 1).text = "{{Client Name | upper}}"
    sig.cell(1, 0).text = "By: ______________________"
    sig.cell(1, 1).text = "By: ______________________"
    sig.cell(2, 0).text = "Name: {{TMAI Signatory}}"
    sig.cell(2, 1).text = "Name: {{Client Signatory}}"
    sig.cell(3, 0).text = "Date: ________________"
    sig.cell(3, 1).text = "Date: ________________"

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    return path


if __name__ == "__main__":
    print(build())
