from pathlib import Path

def test_pwa_delivery_and_static_only_cache(env):
    c,t,_,_,_=env
    home=c.get('/',follow_redirects=False)
    assert home.status_code==307 and home.headers['location']=='/app/'
    page=c.get('/app/')
    assert page.status_code==200
    assert 'Quản lý nền nếp' in page.text
    assert "default-src 'none'" in page.headers['content-security-policy']
    assert 'no-referrer' == page.headers['referrer-policy']
    manifest=c.get('/app/manifest.webmanifest')
    assert manifest.status_code==200
    assert manifest.json()['start_url']=='/app/'
    assert len(manifest.json()['icons'])==2
    assert c.get('/app/app.js').status_code==200
    assert c.get('/app/style.css').status_code==200
    worker=c.get('/app/sw.js')
    assert worker.status_code==200
    assert "url.pathname.startsWith('/app/')" in worker.text
    assert c.get('/app/icons/icon-192.png').content[:8]==b'\x89PNG\r\n\x1a\n'
    assert c.get('/students').status_code==401
    assert c.get('/dashboard').headers['cache-control']=='no-store'

def test_two_clients_can_share_live_api_data(env):
    c,token,_,_,_=env
    a,b=token('admin'),token('recorder')
    assert c.get('/violations',headers=a).json()['total']==0
    saved=c.post('/violations',headers={**b,'Idempotency-Key':'web-android-sync-key-000001'},json={
        'student_code':'TEST-001','violation_type_id':1,'happened_on':'2026-11-02','note':'Dữ liệu chung'})
    assert saved.status_code==201,saved.text
    assert c.get('/dashboard',headers=a).json()['all_total']==1
    assert c.get('/students/TEST-001',headers=a).json()['total']==1
    assert c.get('/violations',headers=b).json()['total']==1

def test_pwa_exposes_photo_actions_without_exposing_photos(env):
    c,_,_,_,_=env
    js=c.get('/app/app.js').text
    assert 'recordCamera' in js and 'recordPhotos' in js
    assert 'viewEvidence' in js and 'uploadEvidence' in js
    assert 'Bearer '+"'" not in js or 'Authorization' in js
    assert c.get('/violations/1/photos/1').status_code==401
