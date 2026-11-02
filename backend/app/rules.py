"""Literal translation of TRA_CUU!E18:E19 and CANH_BAO!R:S."""
VIOLATION_NAMES = [
    'Đi học muộn','Nghỉ học không phép','Trang phục','Thẻ học sinh',
    'Nhuộm tóc','Khuyên tai','Giày, dép','Không đội mũ bảo hiểm',
    'Hút thuốc','Đánh nhau','Vi phạm khác'
]
SEVERE = {'Hút thuốc', 'Đánh nhau'}
DEFAULT_RULES = [
    (0,0,'Tốt','Tiếp tục duy trì.'),
    (1,2,'Nhắc nhở','GVCN nhắc nhở, theo dõi.'),
    (3,4,'Cần quan tâm','GVCN trao đổi trực tiếp, xác định nguyên nhân.'),
    (5,6,'Cảnh báo','GVCN tăng cường theo dõi, trao đổi CMHS.'),
    (7,None,'Cảnh báo cao','GVCN phối hợp Ban Đức dục và CMHS.'),
]

def recommendation(counts):
    """Preserve IF branch order in Excel; not equivalent to aggregating advice."""
    total = sum(counts.values())
    if counts.get('Hút thuốc',0) >= 1 or counts.get('Đánh nhau',0) >= 1:
        return 'Phối hợp Ban Đức dục và CMHS xử lý ngay vi phạm nghiêm trọng.'
    if counts.get('Nghỉ học không phép',0) >= 2:
        return 'Xác minh nguyên nhân nghỉ học và liên hệ CMHS.'
    if counts.get('Không đội mũ bảo hiểm',0) >= 2:
        return 'Tăng cường nhắc nhở an toàn giao thông.'
    if total >= 7: return 'Phối hợp Ban Đức dục và CMHS.'
    if total >= 5: return 'Tăng cường theo dõi, trao đổi CMHS.'
    if total >= 3: return 'Làm việc trực tiếp, xác định nguyên nhân.'
    if counts.get('Đi học muộn',0) >= 3: return 'Theo dõi giờ đến trường; đi muộn lặp lại.'
    if total >= 1: return 'Nhắc nhở và tiếp tục theo dõi.'
    return 'Tiếp tục duy trì.'

def warning(counts, ranges=None):
    if counts.get('Hút thuốc',0) or counts.get('Đánh nhau',0): return 'Cảnh báo cao'
    total = sum(counts.values())
    ranges = ranges or DEFAULT_RULES
    for low, high, label, *_ in ranges:
        if low <= total and (high is None or total <= high): return label
    raise ValueError('Các ngưỡng cảnh báo không bao phủ tổng số lần vi phạm')

def validate_rules(rules):
    """Intervals cover 0..infinity exactly once; preserve label semantics for severe violations."""
    if not rules: raise ValueError('Cần ít nhất một mức cảnh báo')
    rules = sorted(rules, key=lambda x: x['min_count'])
    expected = 0
    for index, r in enumerate(rules):
        if r['min_count'] != expected: raise ValueError('Ngưỡng cảnh báo phải liên tục, không trùng')
        maximum = r.get('max_count')
        if maximum is None:
            if index != len(rules)-1: raise ValueError('Chỉ mức cuối được không giới hạn')
            if r['label'] != 'Cảnh báo cao': raise ValueError('Mức cao nhất phải là Cảnh báo cao')
        elif maximum < expected: raise ValueError('Ngưỡng kết thúc không hợp lệ')
        else: expected = maximum+1
    if rules[-1].get('max_count') is not None: raise ValueError('Phải có mức cuối không giới hạn')
    return rules
