import os
os.environ['JWT_SECRET']='temporary-test-secret-1234567890-abcdef'
import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base,get_db
from app.main import app
from app.models import User,SchoolClass,Student,UserClassAssignment
from app.seed import seed_defaults
from app.security import hash_password

@pytest.fixture
def env(tmp_path):
    engine=create_engine(f'sqlite:///{tmp_path}/test.db',connect_args={'check_same_thread':False})
    Base.metadata.create_all(engine)
    factory=sessionmaker(bind=engine,expire_on_commit=False)
    with factory() as db:
        year=seed_defaults(db)
        cls=SchoolClass(school_year_id=year.id,name='10TEST',grade=10)
        other=SchoolClass(school_year_id=year.id,name='11TEST',grade=11)
        db.add_all([cls,other]);db.flush()
        db.add_all([Student(code='TEST-001',ordinal=1,full_name='Học sinh thử nghiệm',class_id=cls.id,school_year_id=year.id,birth_date=date(2010,1,1),gender='Nam'),
                    Student(code='TEST-002',ordinal=1,full_name='Học sinh hai',class_id=other.id,school_year_id=year.id,birth_date=date(2010,1,2),gender='Nữ')])
        users=[]
        for role in ['admin','leadership','homeroom','recorder']:
            u=User(username=role,display_name=role,role=role,password_hash=hash_password('TestPass123456!'))
            db.add(u);db.flush();users.append(u)
        for u in users[-2:]:db.add(UserClassAssignment(user_id=u.id,class_id=cls.id))
        db.commit()
        cls_id=cls.id;other_id=other.id
    def override():
        with factory() as db:yield db
    app.dependency_overrides[get_db]=override
    with TestClient(app) as client:
        def token(role):
            response=client.post('/auth/login',json={'username':role,'password':'TestPass123456!'})
            assert response.status_code==200,response.text
            return {'Authorization':'Bearer '+response.json()['access_token']}
        yield client,token,cls_id,other_id,factory
    app.dependency_overrides.clear();engine.dispose()
