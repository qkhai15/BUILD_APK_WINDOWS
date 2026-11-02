"""After flutter create, add Android INTERNET permission for HTTPS REST calls."""
from pathlib import Path
import re
f=Path(__file__).resolve().parents[1]/'mobile/android/app/src/main/AndroidManifest.xml'
if not f.exists():
    raise SystemExit('Android project not created. First run flutter create from mobile/.')
s=f.read_text()
permission='<uses-permission android:name="android.permission.INTERNET" />'
if 'android.permission.INTERNET' not in s:
    s,n=re.subn(r'(<manifest\b[^>]*>)',r'\1\n    '+permission,s,count=1,flags=re.S)
    if n!=1:raise SystemExit('Invalid AndroidManifest.xml')
    f.write_text(s)
print('Android HTTPS internet permission present.')
