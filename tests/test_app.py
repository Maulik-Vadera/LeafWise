from io import BytesIO
import asyncio
import json
from pathlib import Path
import numpy as np
import pytest
from PIL import Image
from fastapi.testclient import TestClient
import httpx
from app.main import app
from app.catalog import canonical, entry
from app.imaging import decode_image, ImageProblem, quality, preprocess
from app.inference import LeafModel, decide, softmax
from app.plantnet import identify

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv('PLANTNET_API_KEY',raising=False)
    with TestClient(app) as c:yield c

def photo(size=(256,256),blank=False):
    arr=np.full((*size,3),120,dtype=np.uint8) if blank else np.random.default_rng(12).integers(20,225,(*size,3),dtype=np.uint8)
    buffer=BytesIO();Image.fromarray(arr).save(buffer,'PNG');return buffer.getvalue()

def test_starter_integrity_and_scope(client):
    result=client.get('/api/status').json()
    assert result['ready'] and result['class_count']==15 and len(result['crops'])==3
    assert not result['plantnet_available'] and not result['field_validated']
    assert len(client.get('/api/catalog').json()['entries'])==15

def test_app_assets_and_security_headers(client):
    response=client.get('/')
    assert response.status_code==200 and 'leafwise' in response.text
    assert "default-src 'self'" in response.headers['content-security-policy']
    for path in ['/app.js','/styles.css','/journal.js','/manifest.webmanifest','/icon-192.png','/sw.js']:
        assert client.get(path).status_code==200
    assert client.get('/.env').status_code==404
    assert client.get('/models/model.onnx').status_code==404

def test_no_files_and_bad_bytes(client):
    assert client.post('/api/analyze',data={'crop':'Tomato'}).status_code==400
    r=client.post('/api/analyze',files={'photos':('leaf.jpg',b'not an image','image/jpeg')})
    assert r.status_code==422

def test_valid_bytes_mime_is_not_trusted(client):
    r=client.post('/api/analyze',files={'photos':('leaf.png',photo(),'application/octet-stream')},data={'crop':'Tomato','crop_confirmed':'yes','verification':'local'})
    assert r.status_code==200
    assert r.json()['status'] in {'uncertain','possible_match'}

def test_blank_image_requests_retake(client):
    r=client.post('/api/analyze',files={'photos':('leaf.png',photo(blank=True),'image/png')},data={'crop':'Tomato'})
    assert r.json()['status']=='retake' and r.json()['candidate'] is None

def test_unsupported_crop_not_forced_to_known_label(client):
    r=client.post('/api/analyze',files={'photos':('leaf.png',photo(),'image/png')},data={'crop':'other'})
    assert r.json()['status']=='unsupported' and r.json()['candidates']==[]

def test_missing_crop_requires_confirmation(client):
    r=client.post('/api/analyze',files={'photos':('leaf.png',photo(),'image/png')})
    assert r.json()['status']=='needs_identification'
    assert r.json()['candidate'] is None and r.json()['candidates']==[]

def test_upload_limits_and_origin(client):
    assert client.post('/api/analyze',content=b'a'*(20*1024*1024+1)).status_code==413
    response=client.post('/api/analyze',files=[('photos',(f'{i}.png',photo(),'image/png')) for i in range(4)])
    assert response.status_code==400
    assert client.post('/api/analyze',headers={'Origin':'https://unrelated.example'}).status_code==403
    assert client.get('/api/status',headers={'Host':'unrelated.example'}).status_code==400

def test_remote_requires_key_and_consent(client,monkeypatch):
    assert client.post('/api/identify').status_code==503
    monkeypatch.setenv('PLANTNET_API_KEY','unit-test-not-a-real-key')
    r=client.post('/api/identify',files={'photos':('leaf.png',photo(),'image/png')})
    assert r.status_code==400 and 'Allow' in r.json()['detail']

def test_rate_limit(client):
    for _ in range(20):client.post('/api/analyze')
    assert client.post('/api/analyze').status_code==429

def test_exif_is_removed():
    im=Image.new('RGB',(256,256),'green');exif=im.getexif();exif[315]='Private photographer'
    b=BytesIO();im.save(b,'JPEG',exif=exif)
    clean=decode_image(b.getvalue())
    assert not clean.getexif() and not clean.info

def test_small_image_and_oversized_file():
    with pytest.raises(ImageProblem):decode_image(photo((60,60)))
    with pytest.raises(ImageProblem):decode_image(b'0'*(6*1024*1024+1))

def test_preprocess_shape_range_and_orientation():
    im=Image.new('RGB',(400,200),(255,0,0))
    cfg={'size':224,'resize_short':256,'mean':[.5]*3,'std':[.5]*3}
    tensor=preprocess(im,cfg)
    assert tensor.shape==(1,3,224,224) and tensor.dtype==np.float32
    assert tensor[0,0].min()==1 and tensor[0,1].max()==-1

def test_aliases():
    assert canonical('Tomato__Tomato_YellowLeaf__Curl_Virus')=='Tomato___Tomato_Yellow_Leaf_Curl_Virus'
    assert canonical('Pepper__bell___Bacterial_spot')=='Pepper,_bell___Bacterial_spot'
    with pytest.raises(ValueError):canonical('Unknown crop')

def test_selective_decisions():
    labels=['Tomato___healthy','Tomato___Late_blight','Potato___healthy']
    assert decide([[.95,.03,.02]],labels,'Tomato')['status']=='possible_match'
    assert decide([[.95,.03,.02]],labels,'Potato')['status']=='uncertain'
    assert decide([[.95,.03,.02]],labels,'auto')['status']=='needs_identification'
    assert decide([[.95,.03,.02],[.04,.95,.01]],labels,'Tomato')['status']=='uncertain'
    assert decide([[.95,.03,.02]],labels,'Tomato',True)['status']=='uncertain'
    assert decide([[.45,.42,.13]],labels,'Tomato')['status']=='uncertain'

def test_softmax_stability():
    scores=softmax([[10000,9999,-10000]])
    assert np.isfinite(scores).all() and np.isclose(scores.sum(),1)

def test_checksums_fail_closed(tmp_path):
    manifest=json.loads((ROOT/'models/manifest.json').read_text())
    (tmp_path/'manifest.json').write_text(json.dumps(manifest));(tmp_path/'model.onnx').write_bytes(b'corrupt')
    assert not LeafModel(tmp_path).ready

def test_plantnet_contract_and_metadata_strip():
    def handler(request):
        assert request.url.path=='/v2/identify/all'
        assert request.url.params['api-key']=='test-key'
        body=request.read()
        assert b'name="images"' in body and b'name="organs"' in body
        assert b'Private photographer' not in body
        return httpx.Response(200,json={'version':'test','results':[{'score':.9,'species':{
            'scientificNameWithoutAuthor':'Mangifera indica','commonNames':['Mango'],
            'genus':{'scientificNameWithoutAuthor':'Mangifera'},'family':{'scientificNameWithoutAuthor':'Anacardiaceae'}}}]})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await identify([Image.new('RGB',(256,256),'green')],['leaf'],'test-key',client=c)
    r=asyncio.run(run());assert r['candidates'][0]['name']=='Mangifera indica'

def test_varieties_are_nested_and_not_species():
    def handler(request):
        assert request.url.path=='/v2/varieties/identify'
        return httpx.Response(200,json={'results':[{'score':.1,'species':{'scientificNameWithoutAuthor':'Malus domestica'},
            'varieties':[{'name':'Example cultivar','score':.8}]}]})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await identify([Image.new('RGB',(256,256),'green')],['leaf'],'test-key','variety',c)
    result=asyncio.run(run())
    assert result['candidates'][0]['name']=='Example cultivar' and result['candidates'][0]['score']==.8

def test_provider_error_hides_key():
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(500))) as c:
            with pytest.raises(ValueError) as info:
                await identify([Image.new('RGB',(256,256),'green')],['leaf'],'secret-test-key',client=c)
            assert 'secret-test-key' not in str(info.value)
    asyncio.run(run())
