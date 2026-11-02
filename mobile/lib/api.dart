import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:http_parser/http_parser.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

class ApiException implements Exception {
  final int status;
  final String message;
  const ApiException(this.status, this.message);
  @override
  String toString() => message;
}

class ThdApi extends ChangeNotifier {
  // Optional build-time default. A school-approved HTTPS endpoint can be
  // configured later on the phone, so a single APK works across deployments.
  static const defaultBaseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: '');
  static const _storage = FlutterSecureStorage();
  String _baseUrl = defaultBaseUrl;
  String get baseUrl => _baseUrl;
  bool get hasServer => _baseUrl.isNotEmpty;
  String? _token;
  String? role;
  String? displayName;
  bool ready = false;
  bool get signedIn => _token != null;
  bool get canRecord => const {'admin', 'recorder'}.contains(role);
  bool get isAdmin => role == 'admin';

  Future<void> restore() async {
    try {
      final savedUrl = await _storage.read(key: 'thd_server_url');
      if (savedUrl != null && savedUrl.isNotEmpty) {
        _baseUrl = _validServerUrl(savedUrl);
      }
      if (!hasServer) {
        _token = null;
        return;
      }
      _token = await _storage.read(key: 'thd_access_token');
      if (_token != null) {
        final me = await get('/auth/me') as Map<String, dynamic>;
        role = me['role'] as String;
        displayName = me['display_name'] as String;
      }
    } catch (_) {
      _token = null;
      await _storage.delete(key: 'thd_access_token');
    } finally {
      ready = true;
      notifyListeners();
    }
  }

  // Never let an arbitrary HTTP URL receive staff credentials in a release.
  String _validServerUrl(String value) {
    final input = value.trim().replaceAll(RegExp(r'/+$'), '');
    final parsed = Uri.tryParse(input);
    if (parsed == null || parsed.host.isEmpty || parsed.userInfo.isNotEmpty ||
        parsed.query.isNotEmpty || parsed.hasFragment ||
        (parsed.path.isNotEmpty && parsed.path != '/') ||
        (parsed.scheme != 'https' && !(kDebugMode && parsed.scheme == 'http'))) {
      throw const ApiException(0, 'Nhập địa chỉ máy chủ HTTPS hợp lệ, ví dụ https://nennep.truong.edu.vn');
    }
    return input;
  }

  Future<void> configureServer(String input) async {
    final newBaseUrl = _validServerUrl(input);
    if (newBaseUrl == _baseUrl) return;
    // Switching between school servers must never reuse an old JWT.
    _token = null;
    role = null;
    displayName = null;
    await _storage.delete(key: 'thd_access_token');
    await _storage.write(key: 'thd_server_url', value: newBaseUrl);
    _baseUrl = newBaseUrl;
    notifyListeners();
  }

  Uri uri(String path, [Map<String, String?> params = const {}]) {
    if (!hasServer) throw const ApiException(0, 'Chưa thiết lập máy chủ. Chọn "Cấu hình máy chủ" ở màn hình đăng nhập.');
    final base = Uri.parse(baseUrl.replaceFirst(RegExp(r'/$'), ''));
    if (base.scheme != 'https' && !kDebugMode) {
      throw const ApiException(0, 'Bản phát hành chỉ cho phép kết nối HTTPS.');
    }
    return Uri.parse('$base$path').replace(queryParameters: params.isEmpty
        ? null
        : {for (final entry in params.entries) if (entry.value != null && entry.value!.isNotEmpty) entry.key: entry.value!});
  }

  Map<String, String> headers([String? idempotencyKey]) => {
        'Accept': 'application/json',
        'Content-Type': 'application/json; charset=utf-8',
        if (_token != null) 'Authorization': 'Bearer $_token',
        if (idempotencyKey != null) 'Idempotency-Key': idempotencyKey,
      };

  Future<dynamic> request(String method, String path, {Map<String, String?> query = const {},
    Object? jsonBody, String? idempotencyKey}) async {
    final url = uri(path, query);
    late http.Response response;
    try {
      final h = headers(idempotencyKey);
      final payload = jsonBody == null ? null : jsonEncode(jsonBody);
      switch (method) {
        case 'POST': response = await http.post(url, headers: h, body: payload).timeout(const Duration(seconds: 20)); break;
        case 'PATCH': response = await http.patch(url, headers: h, body: payload).timeout(const Duration(seconds: 20)); break;
        case 'PUT': response = await http.put(url, headers: h, body: payload).timeout(const Duration(seconds: 20)); break;
        default: response = await http.get(url, headers: h).timeout(const Duration(seconds: 20));
      }
    } on SocketException {
      throw const ApiException(0, 'Không kết nối được máy chủ. Kiểm tra mạng hoặc VPN của trường.');
    } catch (e) {
      if (e is ApiException) rethrow;
      throw const ApiException(0, 'Kết nối lỗi hoặc quá thời gian chờ. Không tự gửi lại bản ghi nếu chưa kiểm tra.');
    }
    dynamic payload;
    try { payload = jsonDecode(utf8.decode(response.bodyBytes)); } catch (_) { payload = null; }
    if (response.statusCode >= 400) {
      final detail = payload is Map ? payload['detail'] : null;
      throw ApiException(response.statusCode, detail is String ? detail : 'Máy chủ báo lỗi ${response.statusCode}.');
    }
    return payload;
  }

  Future<dynamic> get(String path, [Map<String, String?> query = const {}]) => request('GET', path, query: query);
  Future<dynamic> post(String path, Object data, {String? key}) => request('POST', path, jsonBody: data, idempotencyKey: key);
  Future<dynamic> patch(String path, Object data) => request('PATCH', path, jsonBody: data);
  Future<dynamic> put(String path, Object data) => request('PUT', path, jsonBody: data);

  Future<void> login(String username, String password) async {
    final result = await post('/auth/login', {'username': username, 'password': password}) as Map<String, dynamic>;
    _token = result['access_token'] as String;
    role = result['role'] as String;
    displayName = result['display_name'] as String;
    await _storage.write(key: 'thd_access_token', value: _token);
    notifyListeners();
  }

  Future<void> logout() async {
    _token = null;role = null;displayName = null;
    await _storage.delete(key: 'thd_access_token');
    notifyListeners();
  }

  /// Image attachment follows creation; a failed upload can safely be retried.
  /// The server deduplicates identical file content within the same violation.
  Future<dynamic> uploadPhoto(int violationId, Uint8List bytes) async {
    if (bytes.isEmpty || bytes.length > 8 * 1024 * 1024) {
      throw const ApiException(413, 'Mỗi ảnh phải nhỏ hơn 8 MB.');
    }
    final uriValue = uri('/violations/$violationId/photos');
    final request = http.MultipartRequest('POST', uriValue);
    request.headers.addAll(headers()..remove('Content-Type'));
    final isPng = bytes.length >= 8 && bytes[0] == 0x89 && bytes[1] == 0x50;
    final isWebp = bytes.length >= 12 && String.fromCharCodes(bytes.sublist(8, 12)) == 'WEBP';
    final suffix = isPng ? 'png' : (isWebp ? 'webp' : 'jpg');
    request.files.add(http.MultipartFile.fromBytes('file', bytes,
      filename: 'bang-chung.$suffix', contentType: MediaType('image', suffix == 'jpg' ? 'jpeg' : suffix)));
    try {
      final response = await http.Response.fromStream(
        await request.send().timeout(const Duration(seconds: 45)));
      if (response.statusCode >= 400) {
        dynamic data;
        try { data = jsonDecode(utf8.decode(response.bodyBytes)); } catch (_) {}
        throw ApiException(response.statusCode,
          data is Map && data['detail'] is String ? data['detail'] as String : 'Không lưu được ảnh (${response.statusCode}).');
      }
      return jsonDecode(utf8.decode(response.bodyBytes));
    } on ApiException { rethrow; }
    catch (_) { throw const ApiException(0, 'Chưa gửi được ảnh. Kiểm tra Internet rồi bấm tiếp tục gửi ảnh.'); }
  }

  Future<Uint8List> photoBytes(int violationId, int photoId) async {
    try {
      final response = await http.get(uri('/violations/$violationId/photos/$photoId'),
        headers: headers()).timeout(const Duration(seconds: 30));
      if (response.statusCode != 200) {
        throw ApiException(response.statusCode, 'Không mở được ảnh; kiểm tra quyền truy cập và mạng.');
      }
      return response.bodyBytes;
    } on ApiException { rethrow; }
    catch (_) { throw const ApiException(0, 'Không thể tải ảnh từ máy chủ.'); }
  }

  Future<void> export(String filePath, String filename) async {
    final url = uri(filePath);
    http.Response response;
    try { response = await http.get(url, headers: headers()).timeout(const Duration(seconds: 35)); }
    catch (_) { throw const ApiException(0, 'Không tải được báo cáo. Kiểm tra kết nối.'); }
    if (response.statusCode != 200) throw ApiException(response.statusCode, 'Không có quyền xuất báo cáo hoặc máy chủ bị lỗi.');
    final tmp = await getTemporaryDirectory();
    final path = '${tmp.path}/$filename';
    final file = File(path);
    await file.writeAsBytes(response.bodyBytes, flush: true);
    final result = await OpenFilex.open(path);
    if (result.type != ResultType.done) throw ApiException(0, 'Đã tạo tệp trong bộ nhớ riêng của ứng dụng, nhưng chưa có ứng dụng hỗ trợ mở tệp.');
  }
}
