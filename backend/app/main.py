from __future__ import annotations
from datetime import date, datetime, timezone
from collections import defaultdict
from zoneinfo import ZoneInfo
from io import BytesIO
import re
import os
import uuid
import hashlib
from PIL import Image, ImageOps, UnidentifiedImageError
from fastapi import UploadFile, File
from fastapi import FastAPI, Depends, HTTPException, Header, Query, Response, Request
from fastapi.responses import StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy import or_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from .db import get_db
from .models import (User,SchoolYear,SchoolClass,Student,ViolationType,Violation,
                     WarningRule,AuditLog,UserClassAssignment,ImportJob,ViolationPhoto)
from .security import (current_user,require,allowed_classes,assert_class,
                       verify_password,hash_password,token_for,ROLES)
from .analytics import active_year, week_window, count_by_student,student_status,summary_rows,rules,TZ
from .rules import VIOLATION_NAMES,warning,recommendation,validate_rules
from .reports import report_object,to_xlsx,to_pdf

app=FastAPI(title='THĐ Student Discipline',version='0.2.0',docs_url='/docs',redoc_url=None)

def no_year(db):
    year=active_year(db)
    if not year: raise HTTPException(409,'Chưa cấu hình năm học đang hoạt động')
    return year

def scoped(q,db,user,class_col):
    allowed=allowed_classes(db,user)
    return q if allowed is None else q.filter(class_col.in_(allowed))

def audit(db,actor,action,entity,entity_id=None,before=None,after=None,request=None):
    ip=request.client.host if request and request.client else None
    db.add(AuditLog(actor_id=getattr(actor,'id',None),action=action,entity=entity,
                    entity_id=str(entity_id) if entity_id is not None else None,
                    previous=before,current=after,ip_address=ip))

def student_dict(s):
    return {'code':s.code,'ordinal':s.ordinal,'full_name':s.full_name,'class_id':s.class_id,
            'class_name':s.school_class.name,'grade':s.school_class.grade,
            'birth_date':s.birth_date.isoformat(),'gender':s.gender,'school_year_id':s.school_year_id}

def violation_dict(v):
    return {'id':v.id,'student_code':v.student.code,'student_name':v.student.full_name,
            'class_id':v.class_id,'class_name':v.school_class.name,'violation_type_id':v.violation_type_id,
            'violation_type':v.violation_type.name,'happened_on':str(v.happened_on),
            'recorded_at':v.recorded_at.isoformat(),'recorded_by':v.recorded_by,
            'recorder':v.recorder.display_name,'note':v.note,'status':v.status,'void_reason':v.void_reason,
            'photo_count':len(v.photos),'photos':[{'id':p.id,'uploaded_at':p.uploaded_at.isoformat()} for p in v.photos]}

def year_range(db,year_id):
    return db.query(SchoolClass).filter(SchoolClass.school_year_id==year_id)

class Login(BaseModel):
    username:str
    password:str

@app.post('/auth/login')
def login(body:Login,db:Session=Depends(get_db)):
    user=db.query(User).filter(User.username==body.username).one_or_none()
    if not user or not user.is_active or not verify_password(user.password_hash,body.password):
        raise HTTPException(401,'Sai tài khoản hoặc mật khẩu')
    return {'access_token':token_for(user),'token_type':'bearer','role':user.role,'display_name':user.display_name}

@app.get('/auth/me')
def me(user:User=Depends(current_user),db:Session=Depends(get_db)):
    return {'id':user.id,'username':user.username,'display_name':user.display_name,'role':user.role,
            'class_ids':sorted(allowed_classes(db,user) or [])}

@app.get('/school-years')
def school_years(db:Session=Depends(get_db),user:User=Depends(current_user)):
    return [{'id':y.id,'name':y.name,'active':y.active} for y in db.query(SchoolYear).order_by(SchoolYear.name)]

@app.get('/classes')
def classes(grade:int|None=None,db:Session=Depends(get_db),user:User=Depends(current_user)):
    year=no_year(db);q=year_range(db,year.id)
    q=scoped(q,db,user,SchoolClass.id)
    if grade is not None:q=q.filter(SchoolClass.grade==grade)
    return [{'id':c.id,'name':c.name,'grade':c.grade,
             'students':db.query(func.count(Student.id)).filter(Student.class_id==c.id).scalar()} for c in q.order_by(SchoolClass.grade,SchoolClass.name)]

@app.get('/violation-types')
def types(db:Session=Depends(get_db),user:User=Depends(current_user)):
    return [{'id':t.id,'name':t.name,'severe':t.severe} for t in db.query(ViolationType).filter_by(is_active=True).order_by(ViolationType.display_order)]

@app.get('/students')
def students(q:str='',class_id:int|None=None,grade:int|None=None,limit:int=Query(50,ge=1,le=150),offset:int=Query(0,ge=0),
             db:Session=Depends(get_db),user:User=Depends(current_user)):
    year=no_year(db);query=db.query(Student).join(SchoolClass,Student.class_id==SchoolClass.id).filter(Student.school_year_id==year.id)
    query=scoped(query,db,user,Student.class_id)
    if q.strip():query=query.filter(or_(Student.code.ilike(f'%{q.strip()}%'),Student.full_name.ilike(f'%{q.strip()}%'),SchoolClass.name.ilike(f'%{q.strip()}%')))
    if class_id is not None:assert_class(db,user,class_id);query=query.filter(Student.class_id==class_id)
    if grade is not None:query=query.filter(SchoolClass.grade==grade)
    total=query.count()
    data=query.options(joinedload(Student.school_class)).order_by(SchoolClass.name,Student.ordinal).offset(offset).limit(limit).all()
    return {'total':total,'items':[student_dict(s) for s in data]}

@app.get('/students/{student_code}')
def student_profile(student_code:str,db:Session=Depends(get_db),user:User=Depends(current_user)):
    s=db.query(Student).options(joinedload(Student.school_class)).filter_by(code=student_code).first()
    if not s:raise HTTPException(404,'Không tìm thấy học sinh')
    assert_class(db,user,s.class_id)
    history=(db.query(Violation).options(joinedload(Violation.student),joinedload(Violation.violation_type),joinedload(Violation.school_class),joinedload(Violation.recorder))
             .filter(Violation.student_id==s.id,Violation.status=='active').order_by(Violation.happened_on.desc(),Violation.recorded_at.desc()).all())
    return {**student_dict(s),**student_status(db,s),'history':[violation_dict(v) for v in history]}

class NewViolation(BaseModel):
    student_code:str=Field(min_length=2,max_length=64)
    violation_type_id:int
    happened_on:date|None=None
    note:str|None=Field(None,max_length=2000)

class EditViolation(BaseModel):
    violation_type_id:int|None=None
    happened_on:date|None=None
    note:str|None=Field(None,max_length=2000)

@app.post('/violations',status_code=201)
def create_violation(body:NewViolation,request:Request,
           idempotency_key:str=Header(...,alias='Idempotency-Key',min_length=16,max_length=100),
           db:Session=Depends(get_db),user:User=Depends(require('admin','recorder'))):
    existed=db.query(Violation).filter_by(idempotency_key=idempotency_key).first()
    happened=body.happened_on or datetime.now(TZ).date()
    s=db.query(Student).filter_by(code=body.student_code).one_or_none()
    if not s:raise HTTPException(404,'Không tìm thấy học sinh')
    assert_class(db,user,s.class_id)
    t=db.get(ViolationType,body.violation_type_id)
    if not t or not t.is_active:raise HTTPException(400,'Loại vi phạm không hợp lệ')
    note=(body.note or '').strip() or None
    if existed:
        if (existed.student_id!=s.id or existed.violation_type_id!=t.id or existed.happened_on!=happened or existed.note!=note):
            raise HTTPException(409,'Idempotency-Key đã được dùng cho nội dung khác')
        return violation_dict(existed)
    v=Violation(student_id=s.id,class_id=s.class_id,school_year_id=s.school_year_id,
                violation_type_id=t.id,happened_on=happened,note=note,
                recorded_by=user.id,idempotency_key=idempotency_key,recorded_at=datetime.now(timezone.utc))
    db.add(v)
    try:
        db.flush();audit(db,user,'violation.created','violations',v.id,after={'student_code':s.code,'type_id':t.id,'date':str(happened)},request=request)
        db.commit()
    except IntegrityError:
        db.rollback();other=db.query(Violation).filter_by(idempotency_key=idempotency_key).first()
        if other and (other.student_id,other.violation_type_id,other.happened_on,other.note)==(s.id,t.id,happened,note): return violation_dict(other)
        raise HTTPException(409,'Trùng khóa gửi hoặc lỗi ràng buộc')
    db.refresh(v)
    return violation_dict(db.query(Violation).options(joinedload(Violation.student),joinedload(Violation.violation_type),joinedload(Violation.school_class),joinedload(Violation.recorder)).filter_by(id=v.id).one())

# PRIVATE EVIDENCE. Only an authenticated user with class access can read images.
# The configured directory must be a private durable volume, backed up with PostgreSQL.
EVIDENCE_DIR = Path(os.environ.get('THD_EVIDENCE_DIR', str(Path(__file__).resolve().parents[1] / 'private_evidence'))).resolve()
MAX_PHOTO_BYTES = 8 * 1024 * 1024
MAX_PHOTOS_PER_VIOLATION = 3

def photo_parent(db: Session, user: User, violation_id: int) -> Violation:
    v = db.get(Violation, violation_id)
    if v is None: raise HTTPException(404, 'Không tìm thấy vi phạm')
    assert_class(db, user, v.class_id)
    return v

@app.post('/violations/{violation_id}/photos', status_code=201)
async def upload_violation_photo(violation_id: int, request: Request,
        file: UploadFile = File(...), db: Session = Depends(get_db),
        user: User = Depends(require('admin', 'recorder'))):
    v = photo_parent(db, user, violation_id)
    if v.status != 'active': raise HTTPException(409, 'Bản ghi đã hủy')
    editable(db, user, v)
    if file.content_type not in ('image/jpeg', 'image/png', 'image/webp'):
        raise HTTPException(415, 'Chỉ nhận ảnh JPG, PNG hoặc WEBP')
    raw = await file.read(MAX_PHOTO_BYTES + 1)
    await file.close()
    if not raw or len(raw) > MAX_PHOTO_BYTES:
        raise HTTPException(413, 'Ảnh phải từ 1 byte đến 8 MB')
    digest = hashlib.sha256(raw).hexdigest()
    previous = db.query(ViolationPhoto).filter_by(violation_id=v.id, sha256=digest).one_or_none()
    if previous:
        return {'id':previous.id, 'violation_id':v.id, 'duplicate':True}
    if len(v.photos) >= MAX_PHOTOS_PER_VIOLATION:
        raise HTTPException(422, 'Mỗi vi phạm tối đa 3 ảnh')
    try:
        # Re-encode without EXIF (GPS/device metadata), cap pixels against decompression bombs.
        with Image.open(BytesIO(raw)) as input_image:
            if input_image.format not in ('JPEG', 'PNG', 'WEBP'):
                raise HTTPException(415, 'Nội dung không phải ảnh hợp lệ')
            if input_image.width * input_image.height > 20_000_000:
                raise HTTPException(413, 'Ảnh quá lớn về độ phân giải')
            clean = ImageOps.exif_transpose(input_image).convert('RGB')
            clean.thumbnail((2200, 2200), Image.Resampling.LANCZOS)
            out = BytesIO()
            clean.save(out, 'JPEG', quality=80, optimize=True)
            data = out.getvalue()
    except (UnidentifiedImageError, ValueError, OSError, Image.DecompressionBombError):
        raise HTTPException(415, 'Ảnh bị lỗi hoặc không được hỗ trợ')
    if len(data) > MAX_PHOTO_BYTES:
        raise HTTPException(413, 'Ảnh sau xử lý vượt giới hạn')
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    key = uuid.uuid4().hex + '.jpg'
    dest = EVIDENCE_DIR / key
    # Private file, random basename; never trust uploaded filenames.
    fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'wb') as handle: handle.write(data)
        item = ViolationPhoto(violation_id=v.id,file_key=key,sha256=digest,
                    content_type='image/jpeg',byte_size=len(data),uploaded_by=user.id,
                    uploaded_at=datetime.now(timezone.utc))
        db.add(item)
        db.flush()
        audit(db,user,'violation.photo.added','violation_photos',item.id,
              after={'violation_id':v.id, 'sha256':digest, 'byte_size':len(data)},request=request)
        db.commit()
        return {'id':item.id,'violation_id':v.id,'duplicate':False}
    except IntegrityError:
        db.rollback()
        dest.unlink(missing_ok=True)
        prior = db.query(ViolationPhoto).filter_by(violation_id=v.id,sha256=digest).one_or_none()
        if prior: return {'id':prior.id,'violation_id':v.id,'duplicate':True}
        raise HTTPException(409,'Không thể ghi ảnh, hãy thử lại')
    except Exception:
        db.rollback()
        dest.unlink(missing_ok=True)
        raise

@app.get('/violations/{violation_id}/photos/{photo_id}')
def read_violation_photo(violation_id:int, photo_id:int, db:Session=Depends(get_db),
                         user:User=Depends(current_user)):
    photo_parent(db,user,violation_id)
    photo=db.query(ViolationPhoto).filter_by(id=photo_id,violation_id=violation_id).one_or_none()
    if not photo: raise HTTPException(404,'Không tìm thấy ảnh')
    path=EVIDENCE_DIR / photo.file_key
    if not path.is_file(): raise HTTPException(503,'Ảnh chưa sẵn sàng; liên hệ quản trị khôi phục bản sao lưu')
    return Response(content=path.read_bytes(),media_type='image/jpeg',headers={
        'Cache-Control':'private, no-store', 'X-Content-Type-Options':'nosniff',
        'Content-Disposition':'inline; filename="evidence.jpg"'})

def editable(db,user,v):
    assert_class(db,user,v.class_id)
    if user.role!='admin' and user.id!=v.recorded_by:raise HTTPException(403,'Chỉ quản trị hoặc người lập được sửa/hủy')

@app.patch('/violations/{violation_id}')
def update_violation(violation_id:int,body:EditViolation,request:Request,
        db:Session=Depends(get_db),user:User=Depends(require('admin','recorder'))):
    v=db.get(Violation,violation_id)
    if not v or v.status!='active':raise HTTPException(404,'Bản ghi không còn hiệu lực')
    editable(db,user,v)
    before={'type_id':v.violation_type_id,'date':str(v.happened_on),'note':v.note}
    if body.violation_type_id is not None:
        t=db.get(ViolationType,body.violation_type_id)
        if not t or not t.is_active:raise HTTPException(400,'Loại vi phạm không hợp lệ')
        v.violation_type_id=t.id
    if body.happened_on is not None:v.happened_on=body.happened_on
    if 'note' in body.model_fields_set:v.note=(body.note or '').strip() or None
    v.updated_at=datetime.now(timezone.utc)
    audit(db,user,'violation.updated','violations',v.id,before=before,
          after={'type_id':v.violation_type_id,'date':str(v.happened_on),'note':v.note},request=request)
    db.commit();db.refresh(v)
    return violation_dict(v)

class VoidBody(BaseModel):
    reason:str=Field(min_length=3,max_length=500)

@app.post('/violations/{violation_id}/void')
def void_violation(violation_id:int,body:VoidBody,request:Request,
       db:Session=Depends(get_db),user:User=Depends(require('admin','recorder'))):
    v=db.get(Violation,violation_id)
    if not v or v.status!='active':raise HTTPException(404,'Bản ghi không còn hiệu lực')
    editable(db,user,v)
    v.status='void';v.void_reason=body.reason;v.updated_at=datetime.now(timezone.utc)
    audit(db,user,'violation.voided','violations',v.id,before={'status':'active'},after={'status':'void','reason':body.reason},request=request)
    db.commit();return {'id':v.id,'status':v.status}

@app.get('/violations')
def list_violations(student_code:str|None=None,class_id:int|None=None,grade:int|None=None,
                    type_id:int|None=None,recorder_id:int|None=None,start:date|None=None,end:date|None=None,
                    include_void:bool=False,limit:int=Query(50,ge=1,le=150),offset:int=Query(0,ge=0),
                    db:Session=Depends(get_db),user:User=Depends(current_user)):
    year=no_year(db);q=db.query(Violation).join(Student,Student.id==Violation.student_id).join(SchoolClass,SchoolClass.id==Violation.class_id).filter(Violation.school_year_id==year.id)
    q=scoped(q,db,user,Violation.class_id)
    if not include_void:q=q.filter(Violation.status=='active')
    if student_code:q=q.filter(Student.code==student_code)
    if class_id is not None:assert_class(db,user,class_id);q=q.filter(Violation.class_id==class_id)
    if grade is not None:q=q.filter(SchoolClass.grade==grade)
    if type_id is not None:q=q.filter(Violation.violation_type_id==type_id)
    if recorder_id is not None:q=q.filter(Violation.recorded_by==recorder_id)
    if start:q=q.filter(Violation.happened_on>=start)
    if end:q=q.filter(Violation.happened_on<=end)
    count=q.count()
    data=(q.options(joinedload(Violation.student),joinedload(Violation.school_class),joinedload(Violation.violation_type),joinedload(Violation.recorder))
          .order_by(Violation.happened_on.desc(),Violation.recorded_at.desc(),Violation.id.desc()).offset(offset).limit(limit).all())
    return {'total':count,'items':[violation_dict(v) for v in data]}

@app.get('/dashboard')
def dashboard(start:date|None=None,end:date|None=None,db:Session=Depends(get_db),user:User=Depends(current_user)):
    year=no_year(db); today=datetime.now(TZ).date()
    q=db.query(Violation).filter(Violation.status=='active',Violation.school_year_id==year.id)
    q=scoped(q,db,user,Violation.class_id)
    all_count=q.count();today_q=q.filter(Violation.happened_on==today)
    names={name:db.query(ViolationType.id).filter_by(name=name).scalar() for name in ('Đi học muộn','Nghỉ học không phép')}
    window_rows=summary_rows(db,year.id,allowed_classes(db,user),start,end)
    return {'today':str(today),'today_total':today_q.count(),
            'today_late':today_q.filter(Violation.violation_type_id==names['Đi học muộn']).count(),
            'today_absent':today_q.filter(Violation.violation_type_id==names['Nghỉ học không phép']).count(),
            'all_total':all_count,'by_class':window_rows,
            'by_type':{name:sum(row['by_type'][name] for row in window_rows) for name in VIOLATION_NAMES}}

@app.get('/classes/{class_id}/summary')
def class_summary(class_id:int,db:Session=Depends(get_db),user:User=Depends(current_user)):
    year=no_year(db);c=db.get(SchoolClass,class_id)
    if not c or c.school_year_id!=year.id:raise HTTPException(404,'Không tìm thấy lớp')
    assert_class(db,user,class_id)
    students=db.query(Student).filter_by(class_id=c.id).order_by(Student.ordinal).all()
    grouped=count_by_student(db,year.id,[s.id for s in students]); rr=rules(db)
    rows=[]
    for s in students:
        cnt={n:grouped[s.id].get(n,0) for n in VIOLATION_NAMES}
        rows.append({'code':s.code,'full_name':s.full_name,'total':sum(cnt.values()),'by_type':cnt,
                     'warning':warning(cnt,rr),'recommendation':recommendation(cnt)})
    severe=sum(r['by_type']['Hút thuốc']+r['by_type']['Đánh nhau'] for r in rows)
    return {'class_id':c.id,'class_name':c.name,'headcount':len(students),
            'students_with_violations':sum(r['total']>0 for r in rows),'total':sum(r['total'] for r in rows),
            'severe_total':severe,'different_types':len({n for r in rows for n,v in r['by_type'].items() if v>0}),
            'configured_types':len(VIOLATION_NAMES),'students':rows}

@app.get('/warnings')
def warnings(level:str|None=None,only_flagged:bool=False,class_id:int|None=None,
             limit:int=Query(80,ge=1,le=300),offset:int=Query(0,ge=0),
             db:Session=Depends(get_db),user:User=Depends(current_user)):
    year=no_year(db)
    q=db.query(Student).options(joinedload(Student.school_class)).filter(Student.school_year_id==year.id)
    q=scoped(q,db,user,Student.class_id)
    if class_id is not None:assert_class(db,user,class_id);q=q.filter(Student.class_id==class_id)
    ss=q.order_by(Student.class_id,Student.ordinal).all();grouped=count_by_student(db,year.id,[s.id for s in ss]);rr=rules(db)
    out=[]
    for s in ss:
        cnt={n:grouped[s.id].get(n,0) for n in VIOLATION_NAMES};label=warning(cnt,rr)
        if level and label!=level:continue
        if only_flagged and label=='Tốt':continue
        out.append({**student_dict(s),'total':sum(cnt.values()),'warning':label,'recommendation':recommendation(cnt)})
    return {'total':len(out),'items':out[offset:offset+limit]}

@app.get('/reports/weekly')
def weekly(start:date|None=None,end:date|None=None,db:Session=Depends(get_db),user:User=Depends(current_user)):
    year=no_year(db)
    try:begin,finish=week_window(start,end)
    except ValueError as e:raise HTTPException(422,str(e))
    return report_object(year,begin,finish,summary_rows(db,year.id,allowed_classes(db,user),begin,finish))

@app.get('/reports/weekly.xlsx')
def weekly_excel(start:date|None=None,end:date|None=None,db:Session=Depends(get_db),user:User=Depends(current_user)):
    report=weekly(start,end,db,user)
    return Response(to_xlsx(report),media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition':'attachment; filename="thd-weekly.xlsx"','Cache-Control':'no-store'})

@app.get('/reports/weekly.pdf')
def weekly_pdf(start:date|None=None,end:date|None=None,db:Session=Depends(get_db),user:User=Depends(current_user)):
    report=weekly(start,end,db,user)
    return Response(to_pdf(report),media_type='application/pdf',
                    headers={'Content-Disposition':'attachment; filename="thd-weekly.pdf"','Cache-Control':'no-store'})

@app.get('/admin/warning-rules')
def get_warning_rules(db:Session=Depends(get_db),user:User=Depends(require('admin'))):
    return [{'id':r.id,'min_count':r.min_count,'max_count':r.max_count,
             'label':r.label,'recommendation':r.recommendation,'version':r.version} for r in db.query(WarningRule).order_by(WarningRule.min_count)]

class RuleInput(BaseModel):
    min_count:int=Field(ge=0)
    max_count:int|None=Field(None,ge=0)
    label:str=Field(min_length=2,max_length=50)
    recommendation:str=Field(min_length=2,max_length=500)

@app.put('/admin/warning-rules')
def set_warning_rules(body:list[RuleInput],request:Request,db:Session=Depends(get_db),user:User=Depends(require('admin'))):
    try:ordered=validate_rules([x.model_dump() for x in body])
    except ValueError as e:raise HTTPException(422,str(e))
    previous=[{'min_count':r.min_count,'max_count':r.max_count,'label':r.label} for r in db.query(WarningRule).order_by(WarningRule.min_count)]
    next_version=max([r.version for r in db.query(WarningRule)]+[0])+1
    db.query(WarningRule).delete()
    for x in ordered:db.add(WarningRule(**x,version=next_version))
    audit(db,user,'config.warning.changed','warning_rules',next_version,before={'rules':previous},after={'rules':ordered,'impact':'All computed warning labels recompute on next request'},request=request)
    db.commit();return {'version':next_version,'impact':'Mức cảnh báo được tính lại từ nhật ký gốc; báo cáo xuất trước đây không thay đổi'}

class NewUser(BaseModel):
    username:str=Field(min_length=3,max_length=80,pattern=r'^[A-Za-z0-9._-]+$')
    display_name:str=Field(min_length=2,max_length=150)
    password:str=Field(min_length=12)
    role:str
    class_ids:list[int]=Field(default_factory=list)

@app.post('/admin/users',status_code=201)
def add_user(body:NewUser,request:Request,db:Session=Depends(get_db),user:User=Depends(require('admin'))):
    if body.role not in ROLES:raise HTTPException(422,'Vai trò không hợp lệ')
    if db.query(User).filter_by(username=body.username).first():raise HTTPException(409,'Tên tài khoản đã được sử dụng')
    year=no_year(db)
    ids=set(body.class_ids)
    existing={c.id for c in year_range(db,year.id).filter(SchoolClass.id.in_(ids))}
    if existing!=ids:raise HTTPException(422,'Có lớp không tồn tại trong năm học')
    u=User(username=body.username,display_name=body.display_name,role=body.role,password_hash=hash_password(body.password))
    db.add(u);db.flush()
    for cid in sorted(ids):db.add(UserClassAssignment(user_id=u.id,class_id=cid))
    audit(db,user,'user.created','users',u.id,after={'username':u.username,'role':u.role,'class_ids':sorted(ids)},request=request)
    db.commit();return {'id':u.id,'username':u.username,'role':u.role,'class_ids':sorted(ids)}

@app.get('/admin/users')
def list_users(db:Session=Depends(get_db),user:User=Depends(require('admin'))):
    return [{'id':u.id,'username':u.username,'display_name':u.display_name,'role':u.role,'is_active':u.is_active,
             'class_ids':[x[0] for x in db.query(UserClassAssignment.class_id).filter_by(user_id=u.id)]}
            for u in db.query(User).order_by(User.id)]

class UserUpdate(BaseModel):
    is_active:bool|None=None
    display_name:str|None=Field(None,min_length=2,max_length=150)
    role:str|None=None
    class_ids:list[int]|None=None
    password:str|None=Field(None,min_length=12)

@app.patch('/admin/users/{user_id}')
def edit_user(user_id:int,body:UserUpdate,request:Request,db:Session=Depends(get_db),user:User=Depends(require('admin'))):
    target=db.get(User,user_id)
    if not target:raise HTTPException(404,'Không tìm thấy tài khoản')
    if target.id==user.id and (body.is_active is False or body.role not in (None,'admin')):
        raise HTTPException(409,'Không được tự vô hiệu hóa hoặc hạ quyền quản trị')
    prev={'active':target.is_active,'role':target.role,'display_name':target.display_name}
    if body.role is not None:
        if body.role not in ROLES:raise HTTPException(422,'Vai trò không hợp lệ')
        target.role=body.role
    if body.is_active is not None:target.is_active=body.is_active
    if body.display_name is not None:target.display_name=body.display_name
    if body.password is not None:target.password_hash=hash_password(body.password)
    if body.class_ids is not None:
        ids=set(body.class_ids);year=no_year(db)
        valid={c.id for c in year_range(db,year.id).filter(SchoolClass.id.in_(ids))}
        if ids!=valid:raise HTTPException(422,'Lớp không hợp lệ')
        db.query(UserClassAssignment).filter_by(user_id=target.id).delete()
        db.add_all([UserClassAssignment(user_id=target.id,class_id=cid) for cid in sorted(ids)])
    audit(db,user,'user.updated','users',target.id,before=prev,after={'active':target.is_active,'role':target.role,'password_reset':body.password is not None,'class_ids':body.class_ids},request=request)
    db.commit();return {'id':target.id,'updated':True}

@app.get('/admin/audit-logs')
def audit_logs(limit:int=Query(60,ge=1,le=200),db:Session=Depends(get_db),user:User=Depends(require('admin'))):
    return [{'id':x.id,'action':x.action,'entity':x.entity,'entity_id':x.entity_id,
             'actor_id':x.actor_id,'at':x.happened_at.isoformat(),'before':x.previous,'after':x.current}
             for x in db.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit)]

@app.get('/admin/import-jobs')
def import_jobs(db:Session=Depends(get_db),user:User=Depends(require('admin'))):
    return [{'id':j.id,'sha256':j.file_sha256,'created':j.created,'updated':j.updated,'unchanged':j.unchanged,'status':j.status}
            for j in db.query(ImportJob).order_by(ImportJob.id.desc()).limit(30)]

@app.get('/healthz',include_in_schema=False)
def healthz(): return {'status':'ok'}

class NewYear(BaseModel):
    name:str=Field(pattern=r'^\d{4}-\d{4}$')

@app.post('/admin/school-years',status_code=201)
def add_school_year(body:NewYear,request:Request,db:Session=Depends(get_db),user:User=Depends(require('admin'))):
    if db.query(SchoolYear).filter_by(name=body.name).first():raise HTTPException(409,'Năm học đã tồn tại')
    y=SchoolYear(name=body.name,active=False);db.add(y);db.flush()
    audit(db,user,'school_year.created','school_years',y.id,after={'name':y.name},request=request)
    db.commit();return {'id':y.id,'name':y.name,'active':False}

@app.post('/admin/school-years/{year_id}/activate')
def activate_year(year_id:int,request:Request,db:Session=Depends(get_db),user:User=Depends(require('admin'))):
    year=db.get(SchoolYear,year_id)
    if not year:raise HTTPException(404,'Không tìm thấy năm học')
    previous=active_year(db)
    db.query(SchoolYear).update({SchoolYear.active:False})
    year.active=True
    audit(db,user,'school_year.activated','school_years',year.id,before={'name':previous.name if previous else None},after={'name':year.name},request=request)
    db.commit();return {'active_year':year.name}

class NewClass(BaseModel):
    name:str=Field(min_length=2,max_length=20)
    grade:int=Field(ge=10,le=12)
    school_year_id:int|None=None

@app.post('/admin/classes',status_code=201)
def add_class(body:NewClass,request:Request,db:Session=Depends(get_db),user:User=Depends(require('admin'))):
    year=db.get(SchoolYear,body.school_year_id) if body.school_year_id else no_year(db)
    if not year:raise HTTPException(404,'Năm học không tồn tại')
    if not body.name.startswith(str(body.grade)):raise HTTPException(422,'Tên lớp phải khớp khối')
    if db.query(SchoolClass).filter_by(name=body.name,school_year_id=year.id).first():raise HTTPException(409,'Lớp đã tồn tại')
    c=SchoolClass(name=body.name,grade=body.grade,school_year_id=year.id);db.add(c);db.flush()
    audit(db,user,'class.created','classes',c.id,after={'name':c.name,'year':year.name},request=request)
    db.commit();return {'id':c.id,'name':c.name,'grade':c.grade,'school_year_id':year.id}


# Browser-installable PWA. Same origin as the API to avoid CORS and separate deployments.
# The service worker caches ONLY static UI resources; student data endpoints are never cached.
PWA_DIR = Path(__file__).resolve().parent / 'pwa'
if PWA_DIR.is_dir():
    app.mount('/app', StaticFiles(directory=str(PWA_DIR), html=True), name='pwa')

    @app.get('/', include_in_schema=False)
    def pwa_home():
        return RedirectResponse('/app/', status_code=307)

@app.middleware('http')
async def security_headers(request:Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Permissions-Policy'] = 'geolocation=(), camera=(self), microphone=()'
    if request.url.path.startswith('/app/'):
        response.headers['Content-Security-Policy'] = (
            "default-src 'none'; base-uri 'self'; manifest-src 'self'; "
            "script-src 'self'; style-src 'self'; img-src 'self' blob:; "
            "connect-src 'self'; font-src 'self'; form-action 'self'; frame-ancestors 'none'")
    else:
        response.headers['Cache-Control'] = 'no-store'
    return response
