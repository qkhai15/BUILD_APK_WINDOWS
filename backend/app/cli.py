import argparse,getpass
from .db import SessionLocal
from .models import User
from .seed import seed_defaults
from .security import hash_password

def main():
    parser=argparse.ArgumentParser()
    cmd=parser.add_subparsers(dest='cmd',required=True)
    seed=cmd.add_parser('seed');seed.add_argument('--year',default='2026-2027')
    admin=cmd.add_parser('create-admin');admin.add_argument('--username',required=True);admin.add_argument('--display-name',required=True)
    args=parser.parse_args()
    with SessionLocal() as db:
        if args.cmd=='seed':
            year=seed_defaults(db,args.year);db.commit();print('Đã khởi tạo danh mục và năm học:',year.name)
        elif args.cmd=='create-admin':
            if db.query(User).filter_by(username=args.username).first():raise SystemExit('Tên tài khoản đã tồn tại')
            password=getpass.getpass('Mật khẩu >=12 ký tự (không hiển thị): ')
            confirmation=getpass.getpass('Nhập lại mật khẩu: ')
            if password != confirmation:raise SystemExit('Mật khẩu không khớp')
            user=User(username=args.username,display_name=args.display_name,role='admin',password_hash=hash_password(password))
            db.add(user);db.commit();print('Đã tạo tài khoản quản trị (không in mật khẩu):',user.username)
if __name__=='__main__':main()
