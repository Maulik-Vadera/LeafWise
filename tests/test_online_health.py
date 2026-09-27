"""Contract and routing tests. No live service or diagnostic accuracy claim."""
import asyncio
import importlib
from io import BytesIO
from types import SimpleNamespace

import httpx
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from app.plantnet import identify, disease_catalog, parse_disease_result, PlantNetError

main=importlib.import_module('app.main')


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv('PLANTNET_API_KEY','health-test-only')
    with TestClient(main.app) as c:
        yield c


def upload():
    b=BytesIO();Image.new('RGB',(256,256),'green').save(b,'PNG')
    return {'photos':('affected.png',b.getvalue(),'image/png')}


def sample():
    return {'version':'provider-test-version','remainingIdentificationRequests':123,
            'results':[{'name':'APHISP','score':.91,'description':'Aphis sp.'},
                       {'name':'ELSIAM','score':.02,'description':'Elsinoe ampelina'}]}


def test_disease_endpoint_and_multipart_are_real_provider_contract():
    image=Image.new('RGB',(256,256),'green');exif=image.getexif();exif[315]='PRIVATE_PHOTOGRAPHER'
    image.info['exif']=exif.tobytes()
    def handler(req):
        assert req.method=='POST' and req.url.path=='/v2/diseases/identify'
        assert req.url.params['api-key']=='health-test-only'
        assert req.url.params['no-reject']=='false'
        assert req.url.params['include-related-images']=='false'
        body=req.read()
        assert b'name="images"' in body and b'name="organs"' in body
        assert b'PRIVATE_PHOTOGRAPHER' not in body
        return httpx.Response(200,json=sample())
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await identify([image],['leaf'],'health-test-only','disease',c)
    result=asyncio.run(run())
    assert result['mode']=='disease' and result['provider']=='Pl@ntNet'
    assert result['candidates'][0]['name']=='Aphis sp.' and result['candidates'][0]['code']=='APHISP'
    assert result['candidates'][0]['reference_url']=='https://gd.eppo.int/taxon/APHISP'
    assert result['remaining_requests']==123
    assert 'scientific_name' not in result['candidates'][0]


@pytest.mark.parametrize('results,state', [([], 'no_match'),([{'name':'APHISP','score':.4}],'uncertain'),([{'name':'APHISP','score':.8},{'name':'ELSIAM','score':.79}],'uncertain')])
def test_no_match_and_ambiguous_results_do_not_assert_health(results,state):
    result=parse_disease_result({'results':results})
    assert result['status']==state and 'healthy' not in result
    if not results:assert 'does not establish' in result['note']


@pytest.mark.parametrize('item',[{'score':.9},{'name':'APHISP','score':float('nan')},{'name':'APHISP','score':2},{'name':'APHISP','score':True},{'species':{'scientificNameWithoutAuthor':'Solanum tuberosum'},'score':.9}])
def test_bad_disease_schema_cannot_become_prediction(item):
    with pytest.raises(ValueError):parse_disease_result({'results':[item]})


def test_untrusted_reference_code_does_not_become_link():
    r=parse_disease_result({'results':[{'name':'../secret?key=x','score':.8,'description':'<script>example</script>'}]})
    assert r['candidates'][0]['reference_url'] is None


def test_online_health_bypasses_starter_model_for_any_crop(client,monkeypatch):
    # Online health must work even if no local model is available.
    main.app.state.model=SimpleNamespace(ready=False)
    async def call(images,organs,key,mode):
        assert mode=='disease' and organs==['leaf'] and key=='health-test-only'
        return parse_disease_result(sample())
    monkeypatch.setattr(main,'identify',call)
    r=client.post('/api/health',files=upload(),data={'crop':'Soybean','consent':'yes','organs':'leaf'})
    assert r.status_code==200 and r.json()['mode']=='disease'
    assert r.json()['candidates'][0]['code']=='APHISP'


def test_health_needs_key_and_consent(client,monkeypatch):
    def forbidden(*args,**kwargs):pytest.fail('Must not make an external request')
    monkeypatch.setattr(main,'identify',forbidden)
    assert client.post('/api/health',files=upload()).status_code==400
    monkeypatch.delenv('PLANTNET_API_KEY')
    assert client.post('/api/health',files=upload(),data={'consent':'yes'}).status_code==503


def test_health_validates_organs_and_files(client):
    assert client.post('/api/health',files=upload(),data={'consent':'yes','organs':'soil'}).status_code==400
    assert client.post('/api/health',files={'photos':('x.jpg',b'not-image','image/jpeg')},data={'consent':'yes'}).status_code==422


@pytest.mark.parametrize('code',['unauthorized','quota_exhausted','unreachable','timeout'])
def test_health_provider_failure_never_calls_local_model(client,monkeypatch,code):
    def forbidden(*args,**kwargs):pytest.fail('Must not fall back to starter model')
    monkeypatch.setattr(main.app.state.model,'predict',forbidden)
    async def fail(*args,**kwargs):raise PlantNetError(code,'Safe error',429 if code=='quota_exhausted' else 502)
    monkeypatch.setattr(main,'identify',fail)
    r=client.post('/api/health',files=upload(),data={'consent':'yes'})
    assert r.status_code in {429,502} and r.json()['code']==code
    assert 'health-test-only' not in r.text
    assert main.app.state.inflight==0


def test_disease_404_does_not_mean_healthy():
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(404))) as c:
            return await identify([Image.new('RGB',(256,256),'green')],['leaf'],'test','disease',c)
    result=asyncio.run(run())
    assert result['status']=='no_match' and result['candidates']==[]
    assert 'does not establish' in result['note']


def test_current_disease_catalog_contract():
    def handler(req):
        assert req.method=='GET' and req.url.path=='/v2/diseases' and not req.content
        return httpx.Response(200,json=[{'name':'APHISP','label':'Aphis sp.','categories':['Insecta']}])
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await disease_catalog('test',c)
    result=asyncio.run(run())
    assert result['count']==1 and result['entries'][0]['code']=='APHISP'
    assert 'not a list of supported host plants' in result['note']


def test_catalog_route_requires_key_and_preserves_errors(client,monkeypatch):
    async def fail(*args,**kwargs):raise PlantNetError('unauthorized','Key denied')
    monkeypatch.setattr(main,'disease_catalog',fail)
    assert client.post('/api/plantnet/diseases').json()['code']=='unauthorized'
    monkeypatch.delenv('PLANTNET_API_KEY')
    assert client.post('/api/plantnet/diseases').status_code==503
