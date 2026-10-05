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


MOU = HERE.parent / "examples" / "Publishing MOU TEMPLATE.docx"


def build_mou(path=MOU):
    """A memorandum of agreement for the Publishing agreement field set."""
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Georgia"
    style.font.size = Pt(11)

    def para(*pieces, align=None, style=None):
        p = doc.add_paragraph(style=style)
        for piece in pieces:
            if isinstance(piece, tuple):
                text, how = piece
                run = p.add_run(text)
                run.bold = "b" in how
                run.italic = "i" in how
            else:
                p.add_run(piece)
        if align:
            p.alignment = align
        return p

    def clause(*pieces):
        para(*pieces, style="List Number")
        doc.add_paragraph()

    para(("{{Party Name | list}}", "b"), align=WD_ALIGN_PARAGRAPH.CENTER)
    para(("Memorandum of Agreement", "b"), align=WD_ALIGN_PARAGRAPH.CENTER)
    doc.add_paragraph()
    para("This agreement between {{Party 1 Name}} ({{#if Party 1 Description}}{{Party 1 Description}}, "
         "{{/if}}hereinafter the ",
         ("{{Party 1 Role}}", "b"), ") of {{Party 1 Address}}, and {{Party 2 Name}} (hereinafter the ",
         ("{{Party 2 Role}}", "b"), "), {{Party 2 Address}}",
         "{{#if Party 3 Name}}, and {{Party 3 Name}} (hereinafter the ", ("{{Party 3 Role}}", "b"),
         "), {{Party 3 Address}}{{/if}}, witnesses:")
    doc.add_paragraph()
    para("That, whereas the proprietor has obtained a license for {{Language}} language publishing "
         "rights to ", ("{{Work Title | list}}", "i"), " authored by {{Work Author | list}} (hereinafter the ",
         ("{{Works | plural: work, works}}", "b"), "):")
    doc.add_paragraph()
    clause("The proprietor hereby grants to the publisher {{License Type}} agreement to act as co-publisher "
           "and in-country publishing partner in order to publish (translate, print, and sell) the "
           "{{Language}}-language edition of the {{Works | plural: work, works}} in {{Rights Licensed}} "
           "{{Rights Licensed | plural: format, formats}}"
           "{{#if Print Copy Limit}}, up to {{Print Copy Limit | number-words}} print copies{{/if}}"
           "{{#if Ebook Copy Limit}} and {{Ebook Copy Limit | number-words}} electronic copies{{/if}}, "
           "{{Territory}} (hereinafter the territory), for a period of {{Term Years | number-words}} "
           "{{Term Years | plural: year, years}} (expiring {{Expiration Date | date}}), subject to the "
           "conditions of this agreement.")
    clause("The agreement herein granted expires {{Expiration Date | date}}, or if the publisher goes out "
           "of existence or sells to another publisher.")
    clause("The translated {{Works | plural: work, works}} {{Works | plural: shall be an accurate "
           "translation / shall be accurate translations}}. No abridgment, alteration, or addition will "
           "be made without first obtaining the proprietor’s consent.")
    clause("The publisher shall print on all copies of the translated {{Works | plural: work, works}} "
           "an appropriate copyright notice and the following:")
    doc.add_paragraph("{{#each Works}}")
    para("“This book was first published by {{Work Original Publisher}} with the title ",
         ("{{Work Title}}", "i"), ", copyright {{Work Copyright}}. Translated by permission. "
         "All rights reserved.”")
    doc.add_paragraph("{{/each}}")
    doc.add_paragraph()
    clause("The publisher shall publish the translated {{Works | plural: work, works}} within "
           "{{Publication Deadline Months | number-words}} months of the date of this agreement.")
    clause("The publisher shall furnish one (1) electronic copy of each work to the proprietor without "
           "charge, and {{Copies to Proprietor}} print copies."
           "{{#if Free Copies for Training}} The publisher shall provide {{Free Copies for Training}} "
           "copies free of charge for the proprietor’s training centers.{{/if}}")
    doc.add_paragraph("{{#if Funding Amount}}")
    clause("The proprietor agrees to fund {{Funding Amount | money-whole}} US dollars toward this project "
           "to aid the publisher in making the {{Works | plural: volume, volumes}} affordable and widely "
           "distributed.")
    doc.add_paragraph("{{/if}}")
    doc.add_paragraph("{{#if One-time Fee}}")
    clause("The publisher shall pay the proprietor a one-time fee of {{One-time Fee | money}}.")
    doc.add_paragraph("{{else}}")
    clause("The proprietor waives any licensing fee, advance or royalties due from the publisher.")
    doc.add_paragraph("{{/if}}")
    clause("This agreement shall be valid only if a fully signed copy is in the possession of the "
           "proprietor before {{Signing Deadline | date}}.")
    doc.add_paragraph("{{#each Parties}}")
    para("______________________________   Date ____________")
    para(("{{Party Name}}", "b"))
    para("{{Party Signatory}}, {{Party Signatory Title}}")
    doc.add_paragraph()
    doc.add_paragraph("{{/each}}")

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    return path


if __name__ == "__main__":
    print(build_mou())
