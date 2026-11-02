import 'package:flutter/material.dart';

// Logos 1 and 2 are displayed INSIDE the app. The third logo is reserved for
// the Android launcher / PWA home-screen icon and must not be shown here.
// Supply authentic files using scripts/apply_branding.py; no invented school
// emblems or student data are included in the source archive.
class SchoolBranding extends StatelessWidget {
  final double logoSize;
  final bool withSchoolName;
  final MainAxisAlignment alignment;

  const SchoolBranding({
    super.key,
    this.logoSize = 68,
    this.withSchoolName = false,
    this.alignment = MainAxisAlignment.center,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Row(
          mainAxisAlignment: alignment,
          mainAxisSize: MainAxisSize.min,
          children: [
            _logo('assets/branding/logo_1.png', 'Logo 1', Icons.school_outlined),
            SizedBox(width: logoSize * .26),
            _logo('assets/branding/logo_2.png', 'Logo 2', Icons.shield_outlined),
          ],
        ),
        if (withSchoolName) ...[
          const SizedBox(height: 14),
          const Text(
            'TRƯỜNG THPT TRẦN HƯNG ĐẠO – THANH XUÂN',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, letterSpacing: .25),
          ),
        ],
      ],
    );
  }

  Widget _logo(String path, String label, IconData fallback) {
    return Semantics(
      label: label,
      image: true,
      child: SizedBox(
        width: logoSize,
        height: logoSize,
        child: Image.asset(
          path,
          fit: BoxFit.contain,
          errorBuilder: (_, __, ___) => Icon(
            fallback,
            size: logoSize * .72,
            color: const Color(0xFF135C8B),
          ),
        ),
      ),
    );
  }
}
