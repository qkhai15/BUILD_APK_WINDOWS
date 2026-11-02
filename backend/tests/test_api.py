from datetime import date,datetime
import io
import zipfile


def create(client,headers,kind=1,key='d7f31ef4-8888-4000-bbbb-111111111111',day='2026-11-02',student='TEST-001'):
    return client.post('/violations',headers={**headers,'Idempotency-Key':key},
                       json={'student_code':student,'violation_type_id':kind,'happened_on':day,'note':'test'})

def test_login_and_scoping(env):
    c,t,a,b,_=env
    assert c.get('/classes',headers=t('recorder')).json()==[{'id':a,'name':'10TEST','grade':10,'students':1}]
    assert c.get('/students/TEST-002',headers=t('homeroom')).status_code==403
    assert c.get('/students/TEST-002',headers=t('leadership')).status_code==200
    assert c.get('/admin/users',headers=t('leadership')).status_code==403
    assert c.get('/violations',headers={}).status_code==401

def test_idempotency_and_updates(env):
    c,t,a,b,_=env
    h=t('recorder')
    r=create(c,h)
    assert r.status_code==201,r.text
    original=r.json()
    second=create(c,h)
    assert second.status_code==201
    assert second.json()['id']==original['id']
    conflict=create(c,h,kind=2)
    assert conflict.status_code==409
    assert c.get('/students/TEST-001',headers=h).json()['total']==1
    assert c.get('/dashboard',headers=h).json()['all_total']==1
    assert c.get(f'/classes/{a}/summary',headers=h).json()['total']==1
    assert c.get('/violations',headers=h).json()['total']==1
    patch=c.patch(f"/violations/{original['id']}",headers=h,json={'violation_type_id':2})
    assert patch.status_code==200,patch.text
    assert c.get('/students/TEST-001',headers=h).json()['by_type']['Nghỉ học không phép']==1
    assert c.post(f"/violations/{original['id']}/void",headers=h,json={'reason':'Nhập nhầm'}).status_code==200
    assert c.get('/students/TEST-001',headers=h).json()['total']==0
    assert c.get('/dashboard',headers=h).json()['all_total']==0
    all_records=c.get('/violations?include_void=true',headers=h).json()
    assert all_records['items'][0]['recorded_at']==original['recorded_at']

def test_cannot_record_outside_class(env):
    c,t,a,b,_=env
    assert create(c,t('recorder'),student='TEST-002').status_code==403
    assert create(c,t('leadership')).status_code==403
    assert create(c,t('homeroom')).status_code==403
    assert create(c,t('admin'),student='TEST-002').status_code==201
    assert c.get('/dashboard',headers=t('recorder')).json()['all_total']==0

def test_week_reporting_and_exports(env):
    c,t,a,b,_=env;h=t('admin')
    assert create(c,h,key='1b111111-1111-4111-8111-111111111111',day='2026-10-31').status_code==201
    assert create(c,h,key='2b111111-1111-4111-8111-111111111111',day='2026-11-02').status_code==201
    r=c.get('/reports/weekly?start=2026-11-02&end=2026-11-07',headers=h)
    assert r.status_code==200,r.text
    assert r.json()['total']==1
    assert r.json()['by_type']['Đi học muộn']==1
    data=c.get('/reports/weekly.xlsx?start=2026-11-02&end=2026-11-07',headers=h)
    assert data.status_code==200
    with zipfile.ZipFile(io.BytesIO(data.content)) as z:assert 'xl/workbook.xml' in z.namelist()
    pdf=c.get('/reports/weekly.pdf?start=2026-11-02&end=2026-11-07',headers=h)
    assert pdf.status_code==200,pdf.text[:200] if pdf.status_code!=200 else 'ok'
    assert pdf.content.startswith(b'%PDF')
    assert c.get('/reports/weekly?start=2026-11-08&end=2026-11-07',headers=h).status_code==422

def test_user_admin_and_warning_rules(env):
    c,t,a,b,_=env;h=t('admin')
    add=c.post('/admin/users',headers=h,json={'username':'new_user','display_name':'Giáo viên','password':'StrongPass12345!','role':'homeroom','class_ids':[a]})
    assert add.status_code==201,add.text
    r=c.get('/admin/warning-rules',headers=h)
    assert len(r.json())==5
    payload=[{k:x[k] for k in ('min_count','max_count','label','recommendation')} for x in r.json()]
    new=c.put('/admin/warning-rules',headers=h,json=payload)
    assert new.status_code==200,new.text
    assert c.get('/admin/audit-logs',headers=h).status_code==200

def test_school_year_and_class_management(env):
    c,t,a,b,_=env;h=t('admin')
    year=c.post('/admin/school-years',headers=h,json={'name':'2027-2028'})
    assert year.status_code==201,year.text
    cid=c.post('/admin/classes',headers=h,json={'name':'12A99','grade':12,'school_year_id':year.json()['id']})
    assert cid.status_code==201,cid.text
    activation=c.post(f"/admin/school-years/{year.json()['id']}/activate",headers=h)
    assert activation.status_code==200
    assert any(x['name']=='12A99' for x in c.get('/classes',headers=h).json())
    assert c.get('/students',headers=h).json()['total']==0

def test_two_users_can_record_without_lost_update(env):
    from concurrent.futures import ThreadPoolExecutor
    c,t,a,b,_=env
    admin=t('admin');recorder=t('recorder')
    def submit(which):
        return create(c,admin if which==0 else recorder,
          key=f'efeeeeee-eee{which}-4eee-8eee-11111111111{which}')
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(submit,[0,1]))
    assert [r.status_code for r in responses]==[201,201],[r.text for r in responses]
    assert c.get('/students/TEST-001',headers=admin).json()['total']==2
    assert c.get('/dashboard',headers=admin).json()['all_total']==2
