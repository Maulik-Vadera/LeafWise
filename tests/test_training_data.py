import csv
from pathlib import Path
import pytest
from PIL import Image
from training.prepare import prepare

def make_manifest(root):
    rows=[]
    for crop in ['Tomato','Potato']:
        for i in range(8):
            name=f'{crop}-{i}.png';Image.new('RGB',(128,128),(i*20,50 if crop=='Tomato' else 180,30)).save(root/name)
            rows.append({'path':name,'label':f'{crop}___healthy','group':f'{crop}-leaf-{i}'})
    source=root/'input.csv'
    with source.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['path','label','group']);writer.writeheader();writer.writerows(rows)
    return source,rows

def test_no_groups_cross_splits_and_repeatable(tmp_path):
    source,_=make_manifest(tmp_path)
    prepare(source,tmp_path,tmp_path/'a.csv');prepare(source,tmp_path,tmp_path/'b.csv')
    assert (tmp_path/'a.csv').read_bytes()==(tmp_path/'b.csv').read_bytes()
    rows=list(csv.DictReader((tmp_path/'a.csv').open()))
    assert {r['split'] for r in rows}=={'train','val','calibration','test'}
    seen={}
    for row in rows:
        assert row['group'] not in seen or seen[row['group']]==row['split']
        seen[row['group']]=row['split']

def test_missing_groups_are_rejected(tmp_path):
    source,rows=make_manifest(tmp_path);rows[0]['group']=''
    with source.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['path','label','group']);writer.writeheader();writer.writerows(rows)
    with pytest.raises(ValueError,match='Missing'):prepare(source,tmp_path,tmp_path/'split.csv')

def test_conflicting_duplicate_labels_rejected(tmp_path):
    source,rows=make_manifest(tmp_path)
    (tmp_path/rows[8]['path']).write_bytes((tmp_path/rows[0]['path']).read_bytes())
    with pytest.raises(ValueError,match='contradictory'):prepare(source,tmp_path,tmp_path/'split.csv')
