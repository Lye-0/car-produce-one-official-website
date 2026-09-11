"""Map validated render exports to the stable runtime media layout."""
from copy import deepcopy
from pathlib import PurePosixPath

PROFILES = ('desktop', 'mobile')
JOURNEY_JOBS = ('drive', 'junction', 'route', 'tools-idle', 'magazines-idle')
PORTAL_JOBS = ('portal', 'monitor-idle')

def site_asset_plan(export, fallback_posters):
    manifest = deepcopy(export)
    assert manifest['production'] is True
    assert set(manifest['profiles']) == set(PROFILES)
    copies = []
    portal = {}
    for profile in PROFILES:
        assets = manifest['profiles'][profile]
        assert set(assets) == set(JOURNEY_JOBS + PORTAL_JOBS)
        for job, asset in assets.items():
            source_poster = asset['poster']
            assert '..' not in PurePosixPath(source_poster).parts and not PurePosixPath(source_poster).is_absolute()
            asset['poster'] = f'/media/images/posters/{profile}/{job}.webp'
            copies.append((source_poster, asset['poster']))
            assert {v['codec'] for v in asset['variants']} == {'hevc', 'h264'}
            assert len(asset['variants']) == 2
            for variant in asset['variants']:
                source = variant['src']
                assert '..' not in PurePosixPath(source).parts and not PurePosixPath(source).is_absolute()
                variant['src'] = f'/media/videos/{profile}/{job}/{variant["codec"]}.mp4'
                copies.append((source, variant['src']))
        portal[profile] = {job: assets.pop(job) for job in PORTAL_JOBS}
    manifest['posters'] = deepcopy(fallback_posters)
    return manifest, portal, copies
