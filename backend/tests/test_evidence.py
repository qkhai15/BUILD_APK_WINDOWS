"""Private photo evidence endpoints use synthetic test images, never actual student data."""
import io
from PIL import Image
import pytest
import app.main as service


def jpeg(rgb=(190,30,40), size=(80,60)):
    buff=io.BytesIO()
    Image.new('RGB', size, rgb).save(buff, format='JPEG')
    return buff.getvalue()


def violation(client, auth, key):
    response=client.post('/violations', headers={**auth,'Idempotency-Key':key}, json={
        'student_code':'TEST-001','violation_type_id':1,'note':'Giờ trực kiểm tra'
    })
    assert response.status_code==201, response.text
    return response.json()['id']


def upload(client, auth, violation_id, content, mime='image/jpeg'):
    return client.post(f'/violations/{violation_id}/photos',headers=auth,
                       files={'file':('evidence.jpg',content,mime)})


def test_photo_upload_access_dedup_and_exif(env, tmp_path, monkeypatch):
    monkeypatch.setattr(service, 'EVIDENCE_DIR', tmp_path/'private_files')
    c,t,a,b,_=env;rec=t('recorder');admin=t('admin');school=t('leadership')
    ident=violation(c,rec,'4b111111-1111-4111-8111-111111111111')
    img=jpeg();created=upload(c,rec,ident,img)
    assert created.status_code==201,created.text
    photo_id=created.json()['id']
    assert created.json()['duplicate'] is False
    assert upload(c,rec,ident,img).json()['duplicate'] is True
    assert c.get('/violations',headers=rec).json()['items'][0]['photo_count']==1
    assert c.get('/students/TEST-001',headers=rec).json()['history'][0]['photo_count']==1
    assert c.get(f'/violations/{ident}/photos/{photo_id}').status_code==401
    assert c.get(f'/violations/{ident}/photos/{photo_id}',headers=t('homeroom')).status_code==200
    photo=c.get(f'/violations/{ident}/photos/{photo_id}',headers=school)
    assert photo.status_code==200 and photo.content[:2]==b'\xff\xd8'
    assert 'no-store' in photo.headers['cache-control']
    assert not Image.open(io.BytesIO(photo.content)).getexif()
    assert len(list((tmp_path/'private_files').iterdir()))==1
    assert upload(c,t('leadership'),ident,img).status_code==403
    assert upload(c,t('homeroom'),ident,img).status_code==403
    assert c.get('/violations',headers=admin).json()['items'][0]['photo_count']==1
    assert c.post(f'/violations/{ident}/void',headers=rec,json={'reason':'Nhập sai'}).status_code==200
    assert upload(c,rec,ident,jpeg((50,80,110))).status_code==409


def test_photo_restrict_other_class_and_invalid_upload(env, tmp_path, monkeypatch):
    monkeypatch.setattr(service, 'EVIDENCE_DIR', tmp_path/'private_files')
    c,t,a,b,_=env;rec=t('recorder')
    second=c.post('/violations', headers={**t('admin'),'Idempotency-Key':'8d111111-1111-4111-8111-111111111111'},
          json={'student_code':'TEST-002','violation_type_id':1})
    assert second.status_code==201
    ident=second.json()['id']
    assert upload(c,rec,ident,jpeg()).status_code==403
    assert c.get(f'/violations/{ident}/photos/999',headers=rec).status_code==403
    own=violation(c,rec,'7b111111-1111-4111-8111-111111111111')
    assert upload(c,rec,own,b'fake', 'image/jpeg').status_code==415
    assert upload(c,rec,own,b'fake','text/plain').status_code==415
    assert upload(c,rec,own,b'a'*(8*1024*1024+1)).status_code==413
    for i in range(3):
        assert upload(c,rec,own,jpeg((i*40,0,2))).status_code==201
    assert upload(c,rec,own,jpeg((5,6,7))).status_code==422
