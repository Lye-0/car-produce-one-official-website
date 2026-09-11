import unittest
from copy import deepcopy
from site_media_layout import site_asset_plan, JOURNEY_JOBS, PORTAL_JOBS

class SiteLayoutTests(unittest.TestCase):
    def fixture(self):
        return {'production': True, 'version': 'test', 'profiles': {
            profile: {job: {'fps': 30, 'frames': 271, 'poster': f'{profile}/{job}/00000.webp', 'variants': [
                {'codec': codec, 'src': f'{profile}/{job}/{job}-{codec}.mp4', 'sha256': 'keep-original-hash'} for codec in ('hevc','h264')
            ]} for job in JOURNEY_JOBS + PORTAL_JOBS} for profile in ('desktop','mobile')}}
    def test_split_preserves_all_runtime_assets_and_source_manifest(self):
        source=self.fixture();before=deepcopy(source);posters={'desktop': {'monitor-idle':'/media/images/fallback/desktop/monitor-idle.webp'}}
        journey,portals,copies=site_asset_plan(source,posters)
        self.assertEqual(source,before);self.assertEqual(len(copies),42)
        self.assertEqual(len({destination for _,destination in copies}),42)
        self.assertEqual(sum(destination.endswith('.mp4') for _,destination in copies),28)
        self.assertEqual(journey['posters'],posters)
        for profile in ('desktop','mobile'):
            self.assertEqual(set(journey['profiles'][profile]),set(JOURNEY_JOBS))
            self.assertEqual(set(portals[profile]),set(PORTAL_JOBS))
            self.assertEqual(portals[profile]['portal']['variants'][1]['src'],f'/media/videos/{profile}/portal/h264.mp4')
            self.assertEqual(portals[profile]['portal']['variants'][1]['sha256'],'keep-original-hash')
    def test_incomplete_exports_are_not_installable(self):
        source=self.fixture();source['profiles']['mobile'].pop('route')
        with self.assertRaises(AssertionError):site_asset_plan(source,{})
    def test_sources_cannot_escape_export_directory(self):
        source=self.fixture();source['profiles']['desktop']['route']['variants'][0]['src']='../../private.mp4'
        with self.assertRaises(AssertionError):site_asset_plan(source,{})

if __name__=='__main__':unittest.main()
