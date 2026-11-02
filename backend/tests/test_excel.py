import os
import pytest
from app.excel_import import read_roster

def test_real_file_structure_if_supplied():
    path=os.getenv('THD_WORKBOOK_PATH')
    if not path or not os.path.isfile(path):pytest.skip('Provide THD_WORKBOOK_PATH; no private student file is bundled')
    roster,classes,report=read_roster(path)
    assert report['student_count']==2260
    assert report['class_count']==48
    assert report['duplicates']==0 and report['missing']==0
    assert len({x['code'] for x in roster})==2260
