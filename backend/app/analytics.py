from collections import defaultdict
from datetime import date, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import func
from .models import Violation, ViolationType, Student, SchoolClass, WarningRule, SchoolYear
from .rules import VIOLATION_NAMES, warning, recommendation

TZ=ZoneInfo('Asia/Ho_Chi_Minh')

def active_year(db):
    return db.query(SchoolYear).filter_by(active=True).one_or_none()

def week_window(start=None,end=None):
    now=date.today() if False else __import__('datetime').datetime.now(TZ).date()
    monday=now-timedelta(days=now.weekday())
    start=start or monday
    end=end or (start+timedelta(days=5))
    if end<start or (end-start).days>365: raise ValueError('Khoảng ngày không hợp lệ (tối đa 366 ngày)')
    return start,end

def rules(db):
    return [(x.min_count,x.max_count,x.label,x.recommendation) for x in db.query(WarningRule).order_by(WarningRule.min_count)]

def count_by_student(db, year_id, student_ids=None):
    q=(db.query(Violation.student_id,ViolationType.name,func.count(Violation.id))
       .join(ViolationType,Violation.violation_type_id==ViolationType.id)
       .filter(Violation.status=='active',Violation.school_year_id==year_id))
    if student_ids is not None: q=q.filter(Violation.student_id.in_(student_ids))
    grouped=defaultdict(lambda:defaultdict(int))
    for sid,name,n in q.group_by(Violation.student_id,ViolationType.name).all(): grouped[sid][name]=n
    return grouped

def student_status(db, student, counts=None):
    if counts is None:
        counts=count_by_student(db,student.school_year_id,[student.id]).get(student.id,{})
    by_type={n:int(counts.get(n,0)) for n in VIOLATION_NAMES}
    return {'total':sum(by_type.values()),'by_type':by_type,'warning':warning(by_type,rules(db)),
            'recommendation':recommendation(by_type)}

def summary_rows(db, year_id, permitted=None, start=None, end=None):
    classes=db.query(SchoolClass).filter_by(school_year_id=year_id).order_by(SchoolClass.grade,SchoolClass.name).all()
    if permitted is not None: classes=[c for c in classes if c.id in permitted]
    ids=[c.id for c in classes]
    grouped=defaultdict(lambda:defaultdict(int))
    q=(db.query(Violation.class_id,ViolationType.name,func.count(Violation.id))
         .join(ViolationType,Violation.violation_type_id==ViolationType.id)
         .filter(Violation.status=='active',Violation.school_year_id==year_id))
    q=q.filter(Violation.class_id.in_(ids))
    if start: q=q.filter(Violation.happened_on>=start)
    if end: q=q.filter(Violation.happened_on<=end)
    for cid,name,n in q.group_by(Violation.class_id,ViolationType.name): grouped[cid][name]=n
    out=[]; rr=rules(db)
    for c in classes:
        counts={n:grouped[c.id].get(n,0) for n in VIOLATION_NAMES}
        out.append({'class_id':c.id,'class_name':c.name,'grade':c.grade,'by_type':counts,'total':sum(counts.values()),
                    'warning':warning(counts,rr)})
    return out
