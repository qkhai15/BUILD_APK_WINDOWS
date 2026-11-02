"""Real report serializers; no data fixture or cached workbook formulas."""
from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo
import xlsxwriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from .rules import VIOLATION_NAMES

SCHOOL='TRƯỜNG THPT TRẦN HƯNG ĐẠO – THANH XUÂN'

def report_object(year, start, end, rows):
    total_by_type={n:sum(r['by_type'][n] for r in rows) for n in VIOLATION_NAMES}
    return {'school':SCHOOL,'school_year':year.name,'start':str(start),'end':str(end),
            'issued_at':datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).strftime('%d/%m/%Y %H:%M'),
            'classes':rows,'by_type':total_by_type,'total':sum(total_by_type.values())}

def to_xlsx(report):
    io=BytesIO(); w=xlsxwriter.Workbook(io,{'in_memory':True})
    s=w.add_worksheet('Báo cáo tuần')
    title=w.add_format({'bold':True,'font_size':15,'font_color':'#0B2447','align':'center'})
    info=w.add_format({'font_size':10,'font_color':'#375171'})
    header=w.add_format({'bold':True,'bg_color':'#14477D','font_color':'white','text_wrap':True,'align':'center','valign':'vcenter','border':1,'border_color':'#CCD5DF'})
    body=w.add_format({'border':1,'border_color':'#DCE4ED'})
    number=w.add_format({'border':1,'border_color':'#DCE4ED','align':'center','num_format':'0'})
    s.set_landscape();s.fit_to_pages(1,0);s.set_paper(9);s.freeze_panes(6,1)
    s.merge_range(0,0,0,13,report['school'],title)
    s.merge_range(1,0,1,13,'BÁO CÁO NỀN NẾP HỌC SINH – '+report['school_year'],title)
    s.merge_range(2,0,2,13,f"Từ {report['start']} đến {report['end']} (bao gồm hai đầu mốc)",info)
    s.merge_range(3,0,3,13,'Lập báo cáo: '+report['issued_at'],info)
    s.set_row(5,46);s.set_column(0,0,14);s.set_column(1,11,17);s.set_column(12,12,13);s.set_column(13,13,20)
    headings=['Lớp',*VIOLATION_NAMES,'Tổng','Cảnh báo lớp']
    for c,h in enumerate(headings):s.write(5,c,h,header)
    for i,row in enumerate(report['classes'],6):
        s.write(i,0,row['class_name'],body)
        for c,n in enumerate(VIOLATION_NAMES,1):s.write_number(i,c,row['by_type'][n],number)
        s.write_number(i,12,row['total'],number)
        s.write(i,13,row['warning'],body)
    i=6+len(report['classes']);s.write(i,0,'TOÀN TRƯỜNG / PHẠM VI',header)
    for c,n in enumerate(VIOLATION_NAMES,1):s.write_number(i,c,report['by_type'][n],number)
    s.write_number(i,12,report['total'],number)
    s.autofilter(5,0,max(5,i-1),13)
    s.print_area(0,0,i,13)
    w.close();return io.getvalue()

def to_pdf(report):
    pdfmetrics.registerFont(TTFont('THDDejaVu','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf' if __import__('os').path.exists('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf') else '/usr/local/share/fonts/dejavu/DejaVuSans.ttf'))
    io=BytesIO();doc=SimpleDocTemplate(io,pagesize=landscape(A4),leftMargin=17,rightMargin=17,topMargin=20,bottomMargin=20)
    st=ParagraphStyle('thd',fontName='THDDejaVu',fontSize=9,leading=13,alignment=TA_CENTER)
    st_small=ParagraphStyle('thdsmall',parent=st,fontSize=6,leading=8)
    story=[Paragraph(report['school'],st),Spacer(1,8),Paragraph('BÁO CÁO NỀN NẾP – '+report['school_year'],st),
           Paragraph(f"Từ {report['start']} đến {report['end']} – Lập lúc {report['issued_at']}",st),Spacer(1,12)]
    # Landscape A4 requires compact abbreviated headers; full category names stay in XLSX and legend below.
    labels=['Lớp','Muộn','Nghỉ KP','Trang phục','Thẻ HS','Tóc','Khuyên','Giày dép','Không mũ','Hút thuốc','Đánh nhau','Khác','Tổng','Cảnh báo lớp']
    entries=[[Paragraph(x,st_small) for x in labels]]
    for r in report['classes']:
        values=[r['class_name'],*[str(r['by_type'][n]) for n in VIOLATION_NAMES],str(r['total']),r['warning']]
        entries.append([Paragraph(x,st_small) for x in values])
    entries.append([Paragraph(x,st_small) for x in ['TỔNG',*[str(report['by_type'][n]) for n in VIOLATION_NAMES],str(report['total']),'']])
    table=Table(entries,colWidths=[57]+[43]*11+[42,90],repeatRows=1,hAlign='CENTER')
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#14477D')),
                               ('TEXTCOLOR',(0,0),(-1,0),colors.white),
                               ('GRID',(0,0),(-1,-1),.25,colors.HexColor('#C5CFDD')),
                               ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                               ('BACKGROUND',(0,-1),(-1,-1),colors.HexColor('#E7EFF8')),
                               ('ROWBACKGROUNDS',(0,1),(-1,-2),[colors.white,colors.HexColor('#F5F8FC')])]))
    story.append(table)
    story.append(Spacer(1,6))
    story.append(Paragraph('Ghi chú: Nghỉ KP = Nghỉ học không phép; Không mũ = Không đội mũ bảo hiểm. Các tên loại đầy đủ có trong bản Excel.',st_small))
    doc.build(story);return io.getvalue()
