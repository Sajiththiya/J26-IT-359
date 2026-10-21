import io
import wave
import numpy as np
import pytest
import av
from fastapi.testclient import TestClient
import main


def recording(rate=44100, channels=2, seconds=0.3):
    samples = (np.sin(np.arange(int(rate * seconds)) * 2 * np.pi * 440 / rate) * 12000).astype('<i2')
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(np.repeat(samples[:, None], channels, axis=1).tobytes())
    return buffer.getvalue()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, 'DEMO_MODE', True)
    with TestClient(main.app) as client:
        yield client


def test_demo_contract(client):
    assert client.get('/health').json()['demo_mode'] is True
    assert len(client.get('/species').json()['species']) == 10
    data = recording()
    a = client.post('/predict', files={'file': ('bird.wav', data, 'audio/wav')})
    b = client.post('/predict', files={'file': ('bird.wav', data, 'audio/wav')})
    assert a.status_code == 200
    assert a.json() == b.json()
    result = a.json()
    assert result['demo_mode'] and 'not AI predictions' in result['notice']
    assert len(result['top_three']) == 3
    assert result['audio'] == {'sample_rate': 16000, 'channels': 1, 'duration_seconds': 0.3}
    assert all(p['label'] in main.SPECIES for p in result['top_three'])


@pytest.mark.parametrize('name,data,status', [('x.txt', b'test', 415), ('x.wav', b'', 422), ('x.mp3', b'not audio', 422), ('x.wav', b'x' * (main.MAX_BYTES + 1), 413)], ids=['extension', 'empty', 'corrupt', 'oversized'])
def test_invalid_uploads(client, name, data, status):
    response = client.post('/predict', files={'file': (name, data)})
    assert response.status_code == status
    if data == b'not audio':
        assert 'Cannot decode' in response.json()['detail']


def test_missing_checkpoint(client, monkeypatch):
    monkeypatch.setattr(main, 'DEMO_MODE', False)
    monkeypatch.setattr(main, 'model', None)
    assert not client.get('/health').json()['ready']
    response = client.post('/predict', files={'file': ('bird.wav', recording())})
    assert response.status_code == 503
    assert 'checkpoint' in response.json()['detail'].lower()


def test_cors(client):
    response = client.options('/predict', headers={'Origin': 'http://localhost:3000', 'Access-Control-Request-Method': 'POST'})
    assert response.headers['access-control-allow-origin'] == 'http://localhost:3000'


def test_saved_model_report(client):
    from research import RUN, read_json
    response = client.get('/model-info')
    assert response.status_code == 200
    report = response.json()
    assert report['metrics'] == read_json(RUN / 'final' / 'validation_metrics.json')
    assert report['split'] == 'validation'
    assert len(report['species']) == 10
    assert sum(row['support'] for row in report['species']) == report['validation_clips'] == 925
    assert report['test_used_for_selection'] is False
    for figure in report['figures']:
        image = client.get(figure['url'])
        assert image.status_code == 200
        assert image.headers['content-type'] == 'image/png'
    assert client.get('/model-info/figures/not-a-figure').status_code == 404


def test_saved_model_report(client):
    from research import RUN, read_json
    response = client.get('/model-info')
    assert response.status_code == 200
    report = response.json()
    assert report['metrics'] == read_json(RUN / 'final' / 'validation_metrics.json')
    assert report['split'] == 'validation'
    assert len(report['species']) == 10
    assert sum(row['support'] for row in report['species']) == report['validation_clips'] == 925
    assert report['test_used_for_selection'] is False
    for figure in report['figures']:
        image = client.get(figure['url'])
        assert image.status_code == 200
        assert image.headers['content-type'] == 'image/png'
    assert client.get('/model-info/figures/not-a-figure').status_code == 404


@pytest.mark.parametrize('extension,container_format,codec', [('mp3', 'mp3', 'libmp3lame'), ('m4a', 'mp4', 'aac')])
def test_compressed_audio(client, extension, container_format, codec):
    buffer = io.BytesIO()
    with av.open(buffer, 'w', format=container_format) as container:
        stream = container.add_stream(codec, rate=16000)
        stream.layout = 'mono'
        values = (np.sin(np.arange(8000) * 2 * np.pi * 440 / 16000) * 0.2).astype(np.float32).reshape(1, -1)
        frame = av.AudioFrame.from_ndarray(values, format='fltp', layout='mono')
        frame.sample_rate = 16000
        for packet in stream.encode(frame):
            container.mux(packet)
        for packet in stream.encode(None):
            container.mux(packet)
    response = client.post('/predict', files={'file': (f'bird.{extension}', buffer.getvalue())})
    assert response.status_code == 200, response.text
    assert response.json()['audio']['sample_rate'] == 16000


def test_silence_and_duration(client):
    silent = io.BytesIO()
    with wave.open(silent, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(bytes(32000))
    assert client.post('/predict', files={'file': ('silent.wav', silent.getvalue())}).status_code == 422
    assert client.post('/predict', files={'file': ('long.wav', recording(16000, 1, 61))}).status_code == 422
