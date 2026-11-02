from .models import ViolationType, WarningRule, SchoolYear, Role
from .rules import VIOLATION_NAMES, SEVERE, DEFAULT_RULES

def seed_defaults(db, year_name='2026-2027'):
    year=db.query(SchoolYear).filter_by(name=year_name).one_or_none()
    if not year:
        has_active=db.query(SchoolYear).filter_by(active=True).first()
        year=SchoolYear(name=year_name,active=(has_active is None));db.add(year);db.flush()
    for role, description in [('admin','Quản trị viên'),('leadership','Ban giám hiệu / Đức dục'),('homeroom','Giáo viên chủ nhiệm'),('recorder','Giáo viên trực / người nhập liệu')]:
        if not db.get(Role,role):db.add(Role(name=role,description=description))
    for i,name in enumerate(VIOLATION_NAMES,1):
        if not db.query(ViolationType).filter_by(name=name).first():
            db.add(ViolationType(name=name,display_order=i,severe=name in SEVERE))
    if not db.query(WarningRule).first():
        for low,hi,label,rec in DEFAULT_RULES:
            db.add(WarningRule(min_count=low,max_count=hi,label=label,recommendation=rec,version=1))
    db.flush()
    return year
