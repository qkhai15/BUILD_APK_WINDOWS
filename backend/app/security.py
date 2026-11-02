import os
from datetime import datetime, timedelta, timezone
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .db import get_db
from .models import User, UserClassAssignment

ph = PasswordHasher()
bearer = HTTPBearer(auto_error=False)
ROLES = ('admin', 'leadership', 'homeroom', 'recorder')

def hash_password(password: str):
    if len(password)<12: raise ValueError('Mật khẩu phải dài ít nhất 12 ký tự')
    return ph.hash(password)

def verify_password(hash_: str, candidate: str) -> bool:
    try: return ph.verify(hash_, candidate)
    except (VerifyMismatchError, VerificationError): return False

def jwt_secret():
    secret = os.getenv('JWT_SECRET','')
    if len(secret) < 32: raise RuntimeError('JWT_SECRET must be at least 32 characters long')
    return secret

def token_for(user: User):
    now = datetime.now(timezone.utc)
    return jwt.encode({'sub':str(user.id),'iat':now,'exp':now+timedelta(hours=8)},jwt_secret(), algorithm='HS256')

def current_user(auth: HTTPAuthorizationCredentials|None = Depends(bearer), db:Session=Depends(get_db)):
    if not auth: raise HTTPException(status.HTTP_401_UNAUTHORIZED,'Chưa đăng nhập')
    try:
        claims=jwt.decode(auth.credentials,jwt_secret(),algorithms=['HS256'],options={'require':['sub','exp']})
        user=db.get(User,int(claims['sub']))
    except (jwt.PyJWTError,ValueError,TypeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,'Phiên đăng nhập không hợp lệ')
    if not user or not user.is_active: raise HTTPException(status.HTTP_401_UNAUTHORIZED,'Tài khoản không hoạt động')
    return user

def require(*roles):
    def dep(user:User=Depends(current_user)):
        if user.role not in roles: raise HTTPException(403,'Không có quyền thực hiện')
        return user
    return dep

def allowed_classes(db:Session,user:User):
    if user.role in ('admin','leadership'): return None
    return set([row[0] for row in db.query(UserClassAssignment.class_id).filter(UserClassAssignment.user_id==user.id).all()])

def assert_class(db:Session,user:User,class_id:int):
    allowed=allowed_classes(db,user)
    if allowed is not None and class_id not in allowed:
        raise HTTPException(403,'Không có quyền truy cập lớp này')
