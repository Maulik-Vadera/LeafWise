"""Public website routing and cloud configuration checks, no live provider calls."""
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app, allowed_hosts

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv('PLANTNET_API_KEY',raising=False)
    with TestClient(app) as client:
        yield client

def test_website_and_scanner_are_distinct(client):
    home=client.get('/')
    assert home.status_code==200 and 'id="hero-title"' in home.text
    assert 'data-install' in home.text and 'href="/app#scan"' in home.text
    for path in ['/app','/app/','/app?mode=health','/scanner.html']:
        result=client.get(path)
        assert result.status_code==200 and 'id="analyze"' in result.text
        assert 'id="hero-title"' not in result.text
    for path in ['/landing.js','/landing.css','/install.js','/install.css','/photos.js']:
        assert client.get(path).status_code==200

def test_manifest_launches_scanner_and_preserves_identity(client):
    manifest=client.get('/manifest.webmanifest').json()
    assert manifest['id']=='/' and manifest['start_url']=='/app#scan'
    assert manifest['display']=='standalone' and manifest['scope']=='/'
    for shortcut in manifest['shortcuts']:
        assert client.get(shortcut['url']).status_code==200

def test_public_site_excludes_private_files(client):
    for path in ['/.env','/.env.example','/vercel.json','/requirements.txt','/app/main.py','/models/model.onnx','/Leafwise_Complete_App_Source.zip']:
        assert client.get(path).status_code==404
    for path in ['/','/app','/install.js','/sw.js','/manifest.webmanifest']:
        r=client.get(path)
        assert r.headers['cache-control']=='no-cache'
        assert r.headers['x-frame-options']=='DENY'

def test_exact_vercel_hosts_and_custom_domain(monkeypatch):
    monkeypatch.setenv('VERCEL','1')
    monkeypatch.setenv('VERCEL_URL','leafwise-preview.vercel.app')
    monkeypatch.setenv('VERCEL_BRANCH_URL','leafwise-main.vercel.app')
    monkeypatch.setenv('VERCEL_PROJECT_PRODUCTION_URL','leafwise.vercel.app')
    monkeypatch.setenv('ALLOWED_HOSTS','localhost, plants.example.org ')
    hosts=allowed_hosts()
    assert set(hosts)=={'localhost','plants.example.org','leafwise-preview.vercel.app','leafwise-main.vercel.app','leafwise.vercel.app'}
    assert '*' not in hosts

def test_cloud_status_never_returns_key_or_local_instructions(client,monkeypatch):
    monkeypatch.setenv('VERCEL','1')
    r=client.get('/api/status').json()
    assert r['hosted'] and not r['local_processing']
    assert 'website owner' in r['plantnet']['message'] and '.env' not in r['plantnet']['message']
    secret='TEST_ONLY_DO_NOT_EXPOSE'
    monkeypatch.setenv('PLANTNET_API_KEY',secret)
    response=client.get('/api/status')
    assert response.json()['plantnet_available'] and secret not in response.text

def test_vercel_config_keeps_live_code_model_and_security_middleware():
    config=json.loads((ROOT/'vercel.json').read_text())
    function=config['functions']['app/main.py']
    assert function['maxDuration']>=55
    assert 'models' not in function['excludeFiles'] and 'web/**' not in function['excludeFiles']
    assert 'cdn = false' in (ROOT/'pyproject.toml').read_text()

@pytest.mark.parametrize('code,phrase',[
    ('unauthorized','website owner'),
    ('quota_exhausted','shared identification allowance'),
])
def test_hosted_provider_errors_are_for_visitors(client,monkeypatch,code,phrase):
    from app import main
    from app.plantnet import PlantNetError
    monkeypatch.setenv('VERCEL','1')
    monkeypatch.setenv('PLANTNET_API_KEY','TEST_ONLY_DO_NOT_EXPOSE')
    async def fail(key):
        raise PlantNetError(code,'Developer setup instructions in .env',502)
    monkeypatch.setattr(main,'check_connection',fail)
    response=client.post('/api/plantnet/check')
    assert response.status_code==502
    assert phrase in response.json()['detail']
    assert '.env' not in response.text and 'TEST_ONLY_DO_NOT_EXPOSE' not in response.text
