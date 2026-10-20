"""Validate the built API/worker image against local Compose DB/Redis, then remove test containers/volume.
Synthetic fixtures only; requires image medicare-ai-api:local and unused loopback port 8002.
"""
import os
import subprocess
import time
import uuid
import httpx

suffix = uuid.uuid4().hex[:10]
api_name, worker_name, volume = (f'medicare-check-{part}-{suffix}' for part in ['api','worker','data'])
resources = []
created_volume = False
common = ['--network', 'medicare-ai_default', '-e', 'APP_MODE=development', '-e', 'AUTH_PROVIDER=local',
          '-e', 'STORAGE_PROVIDER=local', '-e', 'LOCAL_DATA_DIR=/data',
          '-e', 'DATABASE_URL=postgresql+psycopg://medicare:local-development-only@postgres:5432/medicare',
          '-e', 'REDIS_URL=redis://redis:6379/1', '-v', f'{volume}:/data']


def docker(*args):
    return subprocess.run(['docker', *args], check=True, capture_output=True, text=True).stdout.strip()


try:
    docker('volume', 'create', volume)
    created_volume = True
    docker('run', '-d', '--name', api_name, *common, '-p', '127.0.0.1:8002:8000', 'medicare-ai-api:local')
    resources.append(api_name)
    docker('run', '-d', '--name', worker_name, *common, 'medicare-ai-api:local', '.venv/bin/celery',
           '-A', 'app.jobs:celery', 'worker', '--loglevel=WARNING', '--concurrency=1')
    resources.append(worker_name)
    for attempt in range(40):
        try:
            response = httpx.get('http://127.0.0.1:8002/health', timeout=2)
            if response.status_code == 200:
                break
        except httpx.HTTPError:
            pass
        time.sleep(1)
    else:
        raise RuntimeError('Container API failed readiness')
    os.environ['MEDICARE_API_BASE'] = 'http://127.0.0.1:8002'
    from smoke import main
    main()
    assert docker('exec', api_name, 'id', '-u') == '10001'
    print('PASS: non-root API + worker container integration with shared encrypted storage')
finally:
    for name in resources:
        subprocess.run(['docker', 'rm', '-f', name], check=False, capture_output=True)
    if created_volume:
        subprocess.run(['docker', 'volume', 'rm', volume], check=False, capture_output=True)
