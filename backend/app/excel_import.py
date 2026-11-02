"""Audited, all-or-nothing import of the supplied 2026 workbook.

Uses zip/XML read-only to preserve student ID strings and avoid evaluating
formula cells. Never exports the student roster into the project or repo.
"""
import argparse, hashlib, json, re, zipfile
from datetime import datetime
from xml.etree import ElementTree as ET
from collections import Counter
from sqlalchemy.exc import SQLAlchemyError
from .db import SessionLocal
from .models import SchoolYear, SchoolClass, Student, ViolationType, ImportJob, AuditLog
from .seed import seed_defaults

M='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
def q(x):return '{'+M+'}'+x

class WorkbookReader:
    def __init__(self,path):
        self.z=zipfile.ZipFile(path)
        s=self.z.read('xl/sharedStrings.xml') if 'xl/sharedStrings.xml' in self.z.namelist() else b'<sst/>'
        self.strings=[''.join(v.text or '' for v in t.iter(q('t'))) for t in ET.fromstring(s).findall(q('si'))]
        wb=ET.fromstring(self.z.read('xl/workbook.xml'))
        relroot=ET.fromstring(self.z.read('xl/_rels/workbook.xml.rels'))
        rels={r.get('Id'):r.get('Target') for r in relroot}
        self.paths={}
        for sh in wb.findall('.//'+q('sheet')):
            path=rels[sh.get('{'+R+'}id')].lstrip('/')
            self.paths[sh.get('name')]=path if path.startswith('xl/') else 'xl/'+path
    def cells(self,name):
        root=ET.fromstring(self.z.read(self.paths[name]));result={}
        for cell in root.findall('.//'+q('sheetData')+'/'+q('row')+'/'+q('c')):
            # Derived cells have formulas, should never be included as raw input.
            if cell.find(q('f')) is not None:continue
            val=cell.find(q('v'));inline=cell.find(q('is'))
            if val is not None: x=val.text or ''
            elif inline is not None:x=''.join(t.text or '' for t in inline.iter(q('t')))
            else:continue
            if cell.get('t')=='s':x=self.strings[int(x)]
            result[cell.get('r')]=str(x)
        return result

def read_roster(path):
    reader=WorkbookReader(path)
    required={'DULIEU_HOCSINH','CAU_HINH','NHAT_KY_VI_PHAM'}
    if not required.issubset(reader.paths):raise ValueError('Thiếu sheet bắt buộc')
    data=reader.cells('DULIEU_HOCSINH');config=reader.cells('CAU_HINH')
    headers=[data.get(f'{k}5') for k in 'ABCDEF']
    if headers!=['Mã HS','STT','Họ và tên','Lớp','Ngày sinh','Giới tính']:
        raise ValueError('Cấu trúc cột học sinh khác workbook gốc')
    allowed=set(x for r in range(6,500) if (x:=config.get(f'H{r}')))
    if not allowed:raise ValueError('Danh sách lớp trong CAU_HINH trống')
    roster=[];err=[];row_numbers=sorted({int(m.group(2)) for key in data if (m:=re.fullmatch(r'([A-F])(\d+)',key)) and int(m.group(2))>=6})
    for row in row_numbers:
        vals=[data.get(f'{c}{row}','').strip() for c in 'ABCDEF']
        if not any(vals):continue
        if not all(vals):err.append(f'Dòng {row}: thiếu trường');continue
        code,ord_,name,class_name,dob,gender=vals
        if class_name not in allowed:err.append(f'Dòng {row}: lớp không nằm trong CAU_HINH');continue
        try:
            n=int(ord_); birth=datetime.strptime(dob,'%d/%m/%Y').date()
            if n<=0 or gender not in ('Nam','Nữ') or not re.fullmatch(r'(10|11|12)[A-Z0-9]+',class_name):raise ValueError('bad field')
        except ValueError:err.append(f'Dòng {row}: STT/ngày sinh/giới tính/lớp không hợp lệ');continue
        roster.append({'code':code,'ordinal':n,'full_name':name,'class_name':class_name,'birth_date':birth,'gender':gender})
    counts=Counter(x['code'] for x in roster)
    duplicates=[k for k,v in counts.items() if v>1]
    if duplicates:err.append(f'Tồn tại {len(duplicates)} mã học sinh trùng')
    used={x['class_name'] for x in roster}
    if used !=allowed:err.append(f'Số lớp có học sinh {len(used)} khác số lớp trong CAU_HINH {len(allowed)}')
    # Existing journal is a template of 5000 formula rows; imported violations must NOT be fabricated.
    journal=reader.cells('NHAT_KY_VI_PHAM')
    journal_inputs=[key for key,v in journal.items() if re.fullmatch(r'[BIK]\d+',key) and int(re.search(r'\d+',key).group())>=6 and v.strip()]
    if journal_inputs:err.append(f'Nhật ký có {len(journal_inputs)} ô nhập liệu; cần quy trình duyệt lịch sử riêng vì NOW() không cố định')
    if err:raise ValueError('; '.join(err[:20]))
    return roster,allowed,{'student_count':len(roster),'class_count':len(allowed),'grade_counts':dict(Counter(x['class_name'][:2] for x in roster)),
                           'duplicates':0,'missing':0,'journal_populated':False}

def import_roster(path,year_name='2026-2027',update_existing=False,dry_run=False):
    roster,classes,report=read_roster(path)
    if dry_run:return {'mode':'validation_only',**report}
    sha=hashlib.sha256(open(path,'rb').read()).hexdigest()
    created=updated=unchanged=0
    with SessionLocal() as db:
        try:
            year=seed_defaults(db,year_name)
            class_map={c.name:c for c in db.query(SchoolClass).filter_by(school_year_id=year.id)}
            for name in sorted(classes):
                if name not in class_map:
                    c=SchoolClass(school_year_id=year.id,name=name,grade=int(name[:2]));db.add(c);db.flush();class_map[name]=c
            existing={s.code:s for s in db.query(Student).filter(Student.code.in_([x['code'] for x in roster]))}
            for record in roster:
                code=record['code'];cls=class_map[record['class_name']]
                values=dict(ordinal=record['ordinal'],full_name=record['full_name'],class_id=cls.id,
                            birth_date=record['birth_date'],gender=record['gender'],school_year_id=year.id)
                item=existing.get(code)
                if item is None:
                    db.add(Student(code=code,**values));created+=1
                elif all(getattr(item,k)==v for k,v in values.items()):unchanged+=1
                elif update_existing:
                    for k,v in values.items():setattr(item,k,v)
                    updated+=1
                else:raise ValueError(f'Hồ sơ {code} đã thay đổi, dừng toàn bộ import; chỉ cho phép cập nhật khi có --update-existing')
            db.add(ImportJob(file_sha256=sha,school_year_id=year.id,created=created,updated=updated,unchanged=unchanged,status='success',notes='Approved offline import; journal template blank'))
            db.add(AuditLog(action='excel.roster.imported',entity='import_jobs',current={'sha256':sha,'year':year_name,'created':created,'updated':updated,'unchanged':unchanged},actor_id=None))
            db.commit()
        except Exception:
            db.rollback()
            db.add(ImportJob(file_sha256=sha,created=0,updated=0,unchanged=0,status='failed',notes='Transaction rolled back; review server logs without student data'))
            db.commit()
            raise
    return {**report,'created':created,'updated':updated,'unchanged':unchanged,'sha256':sha}

def main():
    parser=argparse.ArgumentParser(description='THĐ – kiểm tra và import Excel trong môi trường được phê duyệt')
    parser.add_argument('file');parser.add_argument('--year',default='2026-2027')
    parser.add_argument('--validate-only',action='store_true')
    parser.add_argument('--update-existing',action='store_true',help='CHỈ sau khi đã duyệt các thay đổi hồ sơ')
    a=parser.parse_args()
    result=import_roster(a.file,a.year,a.update_existing,a.validate_only)
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
