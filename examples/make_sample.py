"""Generate the original synthetic certificate used in the quickstart."""

from pathlib import Path

try:
    import pymupdf
except ModuleNotFoundError:  # Older PyMuPDF releases use the legacy module name.
    import fitz as pymupdf


def make_sample(path: Path) -> None:
    with pymupdf.open() as document:
        page = document.new_page(width=612, height=792)
        ink = (0.08, 0.16, 0.22)
        accent = (0.0, 0.33, 0.35)

        page.insert_text((48, 52), "SYNTHETIC SAMPLE - not an ACORD form",
                         fontsize=12, fontname="hebo", color=accent)
        page.insert_text((48, 85), "Liability insurance summary",
                         fontsize=23, fontname="hebo", color=ink)
        page.draw_line((48, 102), (564, 102), color=accent, width=2)

        sections = [
            ("CERTIFICATE DETAILS", [
                "DATE: 06/15/2026",
                "CERTIFICATE NUMBER: SAMPLE-COI-001",
            ]),
            ("PRODUCER", [
                "Synthetic Sample Brokerage",
                "E-MAIL: certificates@example.test",
            ]),
            ("INSURED", ["Synthetic Sample Contractor"]),
            ("INSURERS AFFORDING COVERAGE", ["INSURER A: Synthetic Sample Insurer"]),
            ("COVERAGES", [
                "COMMERCIAL GENERAL LIABILITY",
                "POLICY NUMBER: SAMPLE-GL-001",
                "POLICY EFF: 07/01/2026",
                "POLICY EXP: 07/01/2027",
                "EACH OCCURRENCE: $1,000,000",
                "GENERAL AGGREGATE: $2,000,000",
            ]),
            ("DESCRIPTION OF OPERATIONS", ["Fictional project used to demonstrate local PDF parsing."]),
            ("CERTIFICATE HOLDER", ["Synthetic Sample Project Owner"]),
        ]
        y = 130
        for heading, lines in sections:
            page.insert_text((48, y), heading, fontsize=10, fontname="hebo", color=accent)
            y += 19
            for line in lines:
                page.insert_text((64, y), line, fontsize=11, color=ink)
                y += 17
            y += 15

        document.save(path, deflate=True, no_new_id=True)


if __name__ == "__main__":
    make_sample(Path(__file__).with_name("sample-coi.pdf"))
