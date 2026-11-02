import pytest
from app.rules import warning,recommendation,validate_rules,DEFAULT_RULES

def test_all_threshold_boundaries():
    expected=['Tốt','Nhắc nhở','Nhắc nhở','Cần quan tâm','Cần quan tâm','Cảnh báo','Cảnh báo','Cảnh báo cao']
    assert [warning({'Trang phục':i}) for i in range(8)]==expected

def test_severe_always_highest():
    assert warning({'Hút thuốc':1})=='Cảnh báo cao'
    assert warning({'Đánh nhau':1})=='Cảnh báo cao'
    assert recommendation({'Hút thuốc':1}).startswith('Phối hợp Ban Đức dục')

def test_recommendation_priority():
    assert recommendation({'Nghỉ học không phép':2,'Đi học muộn':3})=='Xác minh nguyên nhân nghỉ học và liên hệ CMHS.'
    assert recommendation({'Không đội mũ bảo hiểm':2,'Đi học muộn':4})=='Tăng cường nhắc nhở an toàn giao thông.'
    assert recommendation({'Đi học muộn':3})=='Làm việc trực tiếp, xác định nguyên nhân.'  # total >=3 wins, exactly as Excel

def test_gap_rejected():
    with pytest.raises(ValueError):validate_rules([{'min_count':0,'max_count':0,'label':'Tốt'},{'min_count':2,'max_count':None,'label':'Cảnh báo cao'}])
