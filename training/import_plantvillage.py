"""Index original PlantVillage color images using the repository's physical-leaf map."""
import argparse
import csv
import json
import re
from pathlib import Path
from app.catalog import canonical

def key_for(path):
    # Original dataset identifiers follow the UUID___capture-name convention.
    name=path.name.replace('_final_masked','').rsplit('___',1)[-1]
    name=re.split(r'copy',name,flags=re.IGNORECASE)[0]
    name=re.sub(r'\.(jpe?g|png)$','',name,flags=re.IGNORECASE)
    return name.strip().lower()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',required=True,help='Original raw/color directory')
    p.add_argument('--leaf-map',required=True,help='Official leaf_grouping/leaf-map.json')
    p.add_argument('--out',required=True)
    a=p.parse_args();root=Path(a.data).resolve();mapping=json.loads(Path(a.leaf_map).read_text())
    rows=[];unresolved=[]
    for image in sorted(root.rglob('*')):
        if image.suffix.lower() not in {'.jpg','.jpeg','.png'}:continue
        label=canonical(image.parent.name)
        matches=[str(value) for value in mapping.get(key_for(image),[]) if str(value).split(':::')[0]==image.parent.name]
        if len(matches)!=1:
            unresolved.append(str(image.relative_to(root)));continue
        rows.append({'path':str(image.relative_to(root)),'label':label,'group':matches[0]})
    output=Path(a.out);output.parent.mkdir(parents=True,exist_ok=True)
    # Do not silently treat an ungrouped image as an independent plant.
    if unresolved:
        output.with_suffix('.unresolved.json').write_text(json.dumps(unresolved,indent=2))
        raise SystemExit(f'{len(unresolved)} images lack an unambiguous physical-leaf group. Resolve them using source metadata or curate a verified subset; see {output.with_suffix(".unresolved.json")}. No training CSV was written.')
    if not rows:raise SystemExit('No images found. Point --data at raw/color.')
    with output.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['path','label','group']);writer.writeheader();writer.writerows(rows)
    print(f'Indexed {len(rows)} photos across {len(set(r["group"] for r in rows))} physical-leaf groups.')

if __name__=='__main__':main()
