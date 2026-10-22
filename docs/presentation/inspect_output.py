"""Inspect generated artifacts; temp-only imaging tools, no runtime dependencies."""
import json, tempfile, sys, zipfile, re, hashlib
from pathlib import Path
from xml.etree import ElementTree as ET
sys.path.insert(0,str(Path(tempfile.gettempdir())/'meetspace-capstone-tools'))
import pymupdf
from PIL import Image, ImageOps, ImageDraw
ROOT=Path(__file__).resolve().parents[2]
EV=ROOT/'docs/evidence/capstone'
doc=pymupdf.open(ROOT/'MeetSpace_Final_Presentation.pdf')
content=json.loads((ROOT/'docs/presentation/deck_content.json').read_text(encoding='utf8'))
checks=dict(pdf_pages=len(doc),expected_pages=len(content),page_size=[doc[0].rect.width,doc[0].rect.height],page_text_lengths=[len(p.get_text()) for p in doc])
for group in range(3):
    pages=range(group*9,min((group+1)*9,len(doc)))
    sheet=Image.new('RGB',(1200,3*247),'#d9d9df')
    for j,n in enumerate(pages):
        p=doc[n]; pix=p.get_pixmap(matrix=pymupdf.Matrix(0.4,0.4)); im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
        im.thumbnail((390,220)); x=(j%3)*400; y=(j//3)*247
        sheet.paste(im,(x,y)); ImageDraw.Draw(sheet).text((x+10,y+223),f'Slide {n+1}',fill='#30263b')
    sheet.save(EV/f'contact_{group+1}.jpg')
ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
with zipfile.ZipFile(ROOT/'MeetSpace_Final_Presentation.pptx') as z:
    slides=[n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)]
    checks['pptx_slides']=len(slides)
    checks['editable_text_runs']=sum(len(ET.fromstring(z.read(n)).findall('.//a:t',ns)) for n in slides)
    checks['embedded_images']=len([n for n in z.namelist() if n.startswith('ppt/media/')])
checks['sha256']={ext:hashlib.sha256((ROOT/f'MeetSpace_Final_Presentation.{ext}').read_bytes()).hexdigest() for ext in ('pptx','pdf')}
checks['total_reduction_percent']=round((737-230)/737*100,2)
checks['pdf_numbers_present']={v:v in doc[18].get_text() for v in ('68.79','12:17','3:50','8:27')}
(EV/'artifact_check.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(checks,ensure_ascii=False))
