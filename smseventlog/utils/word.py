from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.shared import OxmlElement, qn
from docx.shared import Cm, Inches, Pt

from .. import reports as rp
from . import fileops as fl
from .__init__ import *


class WordReport():
    def __init__(self, **kw) -> None:
        doc = Document()
        font_name = 'Calibri'
        font_size = Pt(12)

        font_props = dict(
            size=font_size,
            name=font_name)
        
        tables = {}

        f.set_self(vars())

        # set default paragraph font styles
        self.set_style_props('Normal', font_props)
        self.set_style_props('No Spacing', font_props)
        self.set_style_props('Normal Table', font_props)

        self.doc.styles['Normal'].paragraph_format.line_spacing = 1
        self.doc.styles['Heading 1'].paragraph_format.space_before = Pt(6)
        
        self.set_margins()
    
    def set_header_footer(self):
        
        p = f.resources / 'reports/images'
        p_head = p / 'SMS Logo.png'
        p_foot = p / 'SMS Footer.png'

        section = self.doc.sections[0]
        header = section.header.paragraphs[0]
        footer = section.footer.paragraphs[0]

        header.paragraph_format.space_after = Pt(12)

        header.add_run().add_picture(str(p_head), height=Inches(0.4))
        footer.add_run().add_picture(str(p_foot))
    
    def set_style_props(self, name, props):
        style = self.doc.styles[name]
        font = style.font

        for k, v in props.items():
            setattr(font, k, v)
    
    def set_margins(self):
        """Set full document margins"""
        doc = self.doc
        sections = doc.sections

        for section in sections:
            section.top_margin = Cm(1)
            section.bottom_margin = Cm(1.5)
            section.left_margin = Cm(1.5)
            section.right_margin = Cm(1.5)

    def add_df(self, df, name: str=None, header: bool=True):
        """Add table to word doc from df

        Parameters
        ----------
        df : pd.DataFrame
            dataframe to add
        name : str, optional
            name to save table as, by default 'table_1'
        """

        if name is None:
            name = f'table_{len(self.tables.keys()) + 1}'
        
        hdr = 1 if header else 0
        
        tbl = self.doc.add_table(
            rows=df.shape[0] + hdr,
            cols=df.shape[1])
        
        # save table
        self.tables[name] = tbl

        # add column labels
        if header:
            for i, col in enumerate(df.columns):
                cell = tbl.rows[0].cells[i]
                cell.text = col
        
        # add data
        for i, row in enumerate(df.itertuples(index=False)):
            for j, val in enumerate(row):
                cell = tbl.rows[i + hdr].cells[j]
                
                # set number formats, don't add None
                if not val is None:
                    if isinstance(val, int):
                        val = f'{val:,.0f}'

                    cell.text = str(val)

        self.set_table_style(tbl=tbl)

        return tbl
    
    def set_table_style(self, tbl):
        """Set font size/name for full table"""
        for row in tbl.rows:
            for cell in row.cells:
                p = cell.paragraphs[0]
                p.style = self.doc.styles['No Spacing']
    
    def add_tbl_border(self, tbl):
        """Add table bottom border with OxmlElement"""
        borders = OxmlElement('w:tblBorders')
        bottom_border = OxmlElement('w:bottom')
        bottom_border.set(qn('w:val'), 'single')
        bottom_border.set(qn('w:sz'), '4')
        borders.append(bottom_border)

        tbl._tbl.tblPr.append(borders)
    
    def set_cell_font(self, cell, props: dict):
        """Set cell font/properties"""
        para = cell.paragraphs[0]
        para.paragraph_format.space_after = Pt(0)

        for run in para.runs:
            font = run.font
            for name, val in props.items():
                setattr(font, name, val)
    
    def bold_column(self, tbl, cols: list):
        """Set table columns to bold"""
        for row in tbl.rows:
            for i in cols:
                cell = row.cells[i]
                self.set_cell_font(cell=cell, props=dict(bold=True))
    
    def bold_header(self, text):
        doc = self.doc

        p = doc.add_paragraph()
        run = p.add_run(f'{text.title()}:')
        run.bold = True
        run.add_break()
    
    def add_pictures(self, pics: list):
        doc = self.doc
        doc.add_page_break()

        for i, pic in enumerate(pics):
            
            doc.add_picture(str(pic), height=Inches(4))

            # center picture
            p = doc.paragraphs[-1]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

            # Add figure caption
            cap = doc.add_paragraph(f'Figure ', style='Caption')
            self.add_fig_caption(cap)
            cap.add_run(' - ')
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    def add_fig_caption(self, paragraph):
        """Add figure caption to image with auto updating numbers
        - User must select all (cmd/ctrl + A), then F9 to update fig captions"""
        run = paragraph.add_run()
        r = run._r
        fldChar = OxmlElement('w:fldChar')
        fldChar.set(qn('w:fldCharType'), 'begin')
        r.append(fldChar)
        instrText = OxmlElement('w:instrText')
        instrText.text = ' SEQ Figure \* ARABIC'
        r.append(instrText)
        fldChar = OxmlElement('w:fldChar')
        fldChar.set(qn('w:fldCharType'), 'end')
        r.append(fldChar)

    def save(self, p: Path=None):

        if p is None:
            p = self.p

        self.doc.save(p)
    
    def show(self):
        fl.open_folder(self.p)

    def create_word(self, p_base=None, check_overwrite=False, **kw):
        if p_base is None:
            p_base = Path.home() / 'Desktop'
        
        p = p_base / f'{self.title}.docx'

        if check_overwrite and p.exists():
            from ..gui.dialogs import msgbox
            msg = f'File "{p.name}" already exists. Overwrite?'
            if not msgbox(msg=msg, yesno=True):
                p = p_base / f'{self.title} (1).docx'

        self.doc.save(str(p))
        self.p_rep = p
        return self



class FailureReportWord(WordReport, rp.FailureReport):
    """Failure report based on both rp.FailureReport (for data/initialization) and Word report"""
    def __init__(self, **kw):
        super().__init__(**kw)
        rp.FailureReport.__init__(self, **kw)

        p = f.desktop / 'component_failure.docx'

        f.set_self(vars())

    def create_word(self, **kw):
        doc = self.doc

        self.set_header_footer()

        p = doc.add_heading('Component Failure Summary', level=1)
        p.runs[0].font.size = Pt(20)
        p.paragraph_format.space_after = Pt(12)

        tbl = self.add_df(df=self.df_head, name='header', header=False)
        self.bold_column(tbl=tbl, cols=(0, 2))
        self.add_tbl_border(tbl)

        self.add_body()

        self.add_pictures(pics=sorted(self.pictures))

        return super().create_word(
            p_base=self.ef._p_event,
            check_overwrite=True,
            **kw)
    
    def add_body(self):
        doc = self.doc
        doc.add_paragraph()
        
        for header, text in self.body.items():
            self.bold_header(header)
            p = doc.paragraphs[-1]
            p.add_run(text)
