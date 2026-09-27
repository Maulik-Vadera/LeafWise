"""Regression tests for unknown plants, provider failures and disease routing.

Provider responses are simulated; these tests do not measure recognition accuracy.
"""
import asyncio
import importlib
from io import BytesIO

import httpx
import numpy as np
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from app.inference import decide
from app.plantnet import identify, check_connection, health_scope, parse_result, PlantNetError

main = importlib.import_module('app.main')


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv('PLANTNET_API_KEY', raising=False)
    with TestClient(main.app) as c:
        yield c


def upload():
    pixels = np.random.default_rng(123).integers(25, 225, (256, 256, 3), dtype=np.uint8)
    out = BytesIO()
    Image.fromarray(pixels).save(out, 'PNG')
    return {'photos': ('leaf.png', out.getvalue(), 'image/png')}


def payload(name='Glycine max', score=.97):
    return {'results': [{'score': score, 'species': {
        'scientificNameWithoutAuthor': name, 'commonNames': ['Soybean'],
        'genus': {'scientificNameWithoutAuthor': 'Glycine'},
        'family': {'scientificNameWithoutAuthor': 'Fabaceae'}}}]}


def forbid_inference(*args, **kwargs):
    pytest.fail('The disease classifier must not run on this path')


@pytest.mark.parametrize('crop', ['auto', 'other', 'Soybean'])
def test_unknown_or_unsupported_crop_never_calls_model(client, monkeypatch, crop):
    monkeypatch.setattr(main.app.state.model, 'predict', forbid_inference)
    r = client.post('/api/analyze', files=upload(), data={'crop': crop})
    assert r.status_code == 200
    assert r.json()['candidate'] is None and not r.json()['candidates']
    assert r.json()['status'] in {'needs_identification', 'unsupported'}


def test_confident_potato_logits_cannot_identify_unknown_crop():
    r = decide([[.999, .001]], ['Potato___healthy', 'Tomato___healthy'], 'auto')
    assert r['status'] == 'needs_identification'
    assert r['candidate'] is None and not r['candidates']


def test_wrong_crop_score_does_not_show_another_species():
    r = decide([[.999, .001]], ['Potato___healthy', 'Tomato___healthy'], 'Tomato')
    assert r['status'] == 'uncertain' and r['candidate'] is None and not r['candidates']


def test_known_crop_requires_explicit_confirmation(client, monkeypatch):
    monkeypatch.setattr(main.app.state.model, 'predict', forbid_inference)
    r = client.post('/api/analyze', files=upload(), data={'crop': 'Potato', 'verification': 'local'})
    assert r.json()['status'] == 'needs_confirmation' and not r.json()['candidates']


def test_online_soybean_blocks_potato_disease_model(client, monkeypatch):
    monkeypatch.setenv('PLANTNET_API_KEY', 'test-only')
    monkeypatch.setattr(main.app.state.model, 'predict', forbid_inference)
    async def soy(*args, **kwargs):
        return parse_result(payload(), 'species')
    monkeypatch.setattr(main, 'identify', soy)
    r = client.post('/api/analyze', files=upload(), data={
        'crop': 'Potato', 'crop_confirmed': 'yes', 'verification': 'online', 'consent': 'yes'})
    assert r.status_code == 200 and r.json()['status'] == 'unsupported'
    assert r.json()['identity']['candidates'][0]['scientific_name'] == 'Glycine max'
    assert not r.json()['candidates'] and r.json()['candidate'] is None


def test_soybean_identity_keeps_species_and_reports_health_scope(client, monkeypatch):
    monkeypatch.setenv('PLANTNET_API_KEY', 'test-only')
    monkeypatch.setattr(main.app.state.model, 'predict', forbid_inference)
    async def soy(*args, **kwargs):
        return parse_result(payload(), 'species')
    monkeypatch.setattr(main, 'identify', soy)
    r = client.post('/api/identify', files=upload(), data={'mode': 'species', 'consent': 'yes', 'organs': 'leaf'})
    assert r.status_code == 200
    assert r.json()['candidates'][0]['scientific_name'] == 'Glycine max'
    assert r.json()['health_scope']['status'] == 'unsupported'


@pytest.mark.parametrize('name,score,expected', [('Solanum tuberosum', .99, 'supported'), ('Glycine max', .99, 'unsupported'), ('Solanum tuberosum', .4, 'uncertain')])
def test_species_gate(name, score, expected):
    result = parse_result(payload(name, score), 'species')
    assert health_scope(result, ['Tomato', 'Potato', 'Pepper,_bell'])['status'] == expected


@pytest.mark.parametrize('code', ['unauthorized', 'quota_exhausted', 'timeout', 'unreachable'])
def test_online_errors_never_fall_back_to_disease_model(client, monkeypatch, code):
    monkeypatch.setenv('PLANTNET_API_KEY', 'test-only')
    monkeypatch.setattr(main.app.state.model, 'predict', forbid_inference)
    async def fail(*args, **kwargs):
        raise PlantNetError(code, 'Safe provider error', 429 if code == 'quota_exhausted' else 502)
    monkeypatch.setattr(main, 'identify', fail)
    r = client.post('/api/analyze', files=upload(), data={
        'crop': 'Potato', 'crop_confirmed': 'yes', 'verification': 'online', 'consent': 'yes'})
    assert r.status_code in {429, 502} and r.json()['code'] == code
    assert 'test-only' not in r.text


def test_online_health_needs_photo_consent(client, monkeypatch):
    monkeypatch.setenv('PLANTNET_API_KEY', 'test-only')
    monkeypatch.setattr(main, 'identify', forbid_inference)
    r = client.post('/api/analyze', files=upload(), data={
        'crop': 'Potato', 'crop_confirmed': 'yes', 'verification': 'online'})
    assert r.status_code == 400


@pytest.mark.parametrize('name,score,allowed', [('Solanum tuberosum', .99, True), ('Solanum lycopersicum', .99, False), ('Solanum tuberosum', .4, False)])
def test_online_health_checks_species_before_inference(client, monkeypatch, name, score, allowed):
    monkeypatch.setenv('PLANTNET_API_KEY', 'test-only')
    calls = []
    async def species(*args, **kwargs):
        return parse_result(payload(name, score), 'species')
    def predict(*args, **kwargs):
        calls.append(True)
        return {'status': 'uncertain', 'candidate': None, 'candidates': []}
    monkeypatch.setattr(main, 'identify', species)
    monkeypatch.setattr(main.app.state.model, 'predict', predict)
    r = client.post('/api/analyze', files=upload(), data={
        'crop': 'Potato', 'crop_confirmed': 'yes', 'verification': 'online', 'consent': 'yes'})
    assert r.status_code == 200
    assert bool(calls) is allowed and r.json()['species_verified'] is allowed


def test_configured_is_not_connected(client, monkeypatch):
    monkeypatch.setenv('PLANTNET_API_KEY', 'test-only')
    r = client.get('/api/status')
    assert r.json()['plantnet']['state'] == 'configured'
    assert 'not been checked' in r.json()['plantnet']['message']
    assert 'test-only' not in r.text


def test_env_txt_has_actionable_message(client, monkeypatch, tmp_path):
    (tmp_path / '.env.txt').write_text('PLANTNET_API_KEY=not-a-key')
    monkeypatch.setattr(main, 'ROOT', tmp_path)
    assert '.env.txt' in client.get('/api/status').json()['plantnet']['message']


def test_connection_check_sends_no_photos_or_local_inference(client, monkeypatch):
    assert client.post('/api/plantnet/check').status_code == 503
    monkeypatch.setenv('PLANTNET_API_KEY', 'test-only')
    async def checked(key):
        assert key == 'test-only'
        return {'state': 'ready', 'message': 'Key accepted', 'remaining': 8}
    monkeypatch.setattr(main, 'check_connection', checked)
    assert client.post('/api/plantnet/check').json()['remaining'] == 8


@pytest.mark.parametrize('status,code', [(401, 'unauthorized'), (403, 'unauthorized'), (429, 'quota_exhausted'), (500, 'provider_error')])
def test_http_error_codes_are_preserved(status, code):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(status))) as c:
            with pytest.raises(PlantNetError) as exc:
                await identify([Image.new('RGB', (256, 256), 'green')], ['leaf'], 'private-test-key', client=c)
            assert exc.value.code == code and 'private-test-key' not in str(exc.value)
    asyncio.run(run())


@pytest.mark.parametrize('remaining,state', [(8, 'ready'), (0, 'quota_exhausted')])
def test_quota_connection_contract(remaining, state):
    def handler(req):
        assert req.method == 'GET' and req.url.path == '/v2/quota/daily'
        assert not req.content
        return httpx.Response(200, json={'quota': {'identify': {'remaining': remaining}}})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await check_connection('private-test-key', client=c)
    result = asyncio.run(run())
    assert result['remaining'] == remaining and result['state'] == state


def test_invalid_provider_json_is_not_a_species():
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(200, json={'results': [{'species': []}]}))) as c:
            with pytest.raises(PlantNetError, match='unreadable'):
                await identify([Image.new('RGB', (256, 256), 'green')], ['leaf'], 'private-test-key', client=c)
    asyncio.run(run())
