param([string]$ApiUrl = '')
$ErrorActionPreference='Stop'
if ($ApiUrl -and $ApiUrl -notmatch '^https://\S+$') { throw 'Use an HTTPS server URL, or omit -ApiUrl to configure it on the phone.' }
$root=Split-Path $PSScriptRoot -Parent
Set-Location (Join-Path $root 'mobile')
if (-not (Get-Command flutter -ErrorAction SilentlyContinue)) { throw 'Flutter SDK is missing. Install Flutter, or build using private GitHub Actions.' }
if (-not (Test-Path 'android')) { flutter create --platforms=android --project-name thd_student_discipline .; if($LASTEXITCODE){throw 'flutter create failed'} }
py (Join-Path $root 'scripts\prepare_android.py'); if($LASTEXITCODE){throw 'Android manifest patch failed'}
flutter pub get; if($LASTEXITCODE){throw 'flutter pub get failed'}
if ((Test-Path 'assets/branding/app_icon.png') -and (Test-Path 'assets/branding/app_icon_foreground.png')) {
  dart run flutter_launcher_icons; if($LASTEXITCODE){throw 'Generate app icon failed'}
} else { Write-Warning 'No app icon available; Flutter launcher icon will be used.' }
flutter analyze; if($LASTEXITCODE){throw 'flutter analyze failed'}
flutter build apk --debug "--dart-define=API_BASE_URL=$ApiUrl"; if($LASTEXITCODE){throw 'APK build failed'}
Write-Host 'PILOT APK: mobile\build\app\outputs\flutter-apk\app-debug.apk'
Write-Host 'If URL not supplied, enter the school-approved HTTPS URL on the login screen.'
