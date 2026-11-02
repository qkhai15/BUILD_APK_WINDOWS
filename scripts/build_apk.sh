#!/usr/bin/env bash
# Builds a PILOT Android APK. The app can ask for the school HTTPS URL on first login.
set -euo pipefail
API_URL="${1:-}"
if [[ -n "$API_URL" && ! "$API_URL" =~ ^https://[^[:space:]]+ ]]; then
  echo 'Usage: ./scripts/build_apk.sh [https://your-approved-school-server]' >&2
  exit 2
fi
root="$(cd "$(dirname "$0")/.." && pwd)"
command -v flutter >/dev/null || { echo 'Flutter SDK is missing; use private GitHub Actions or install Flutter.' >&2; exit 3; }
cd "$root/mobile"
if [[ ! -d android ]]; then flutter create --platforms=android --project-name thd_student_discipline .; fi
python3 "$root/scripts/prepare_android.py"
flutter pub get
if [[ -f assets/branding/app_icon.png && -f assets/branding/app_icon_foreground.png ]]; then
  dart run flutter_launcher_icons
else
  echo 'No app icon was found; launcher will use Flutter default.' >&2
fi
flutter analyze
# A build-time URL is OPTIONAL. The phone can save the school's HTTPS URL instead.
flutter build apk --debug --dart-define="API_BASE_URL=$API_URL"
echo "PILOT APK: $root/mobile/build/app/outputs/flutter-apk/app-debug.apk"
echo 'If no URL was supplied, tap Cấu hình máy chủ on the login screen to set it.'
