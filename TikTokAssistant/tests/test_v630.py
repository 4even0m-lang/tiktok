"""Ven0m v6.3 Foundation Sprint regressions (cross-platform)."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app_paths
from event_bus import EventBus
from playback_coordinator import PlaybackCoordinator
from simulation_studio import sample_event
import gift_catalog
import settings_store


class UserDataTests(unittest.TestCase):
    def test_separate_root_from_assets(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.dict(os.environ, {'VEN0M_DATA_DIR': d}):
                self.assertEqual(app_paths.writable_file('settings.json'), Path(d) / 'settings.json')
                self.assertNotEqual(app_paths.writable_file('settings.json').parent,
                                    app_paths.BUNDLE_ROOT)
                with self.assertRaises(ValueError):
                    app_paths.writable_file('../unexpected')

    def test_settings_save_utf8_and_atomic(self):
        with tempfile.TemporaryDirectory() as d:
            original = settings_store.CONFIG_PATH
            settings_store.CONFIG_PATH = Path(d) / 'nested' / 'settings.json'
            try:
                settings = settings_store.load_settings()
                settings['username'] = 'اختبار'
                settings['hosts_setup_prompted'] = True
                settings_store.save_settings(settings)
                self.assertEqual(json.loads(settings_store.CONFIG_PATH.read_text(encoding='utf-8'))['username'], 'اختبار')
                self.assertTrue(settings_store.load_settings()['hosts_setup_prompted'])
                self.assertEqual(list(settings_store.CONFIG_PATH.parent.glob('*.tmp')), [])
            finally:
                settings_store.CONFIG_PATH = original

    def test_old_data_migration_does_not_overwrite_user(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            oldroot = base/'installed'; oldroot.mkdir()
            legacy = oldroot/'settings.json'; legacy.write_text('{"username":"old"}',encoding='utf-8')
            new = base/'user'/'settings.json'
            with patch.object(app_paths, 'BUNDLE_ROOT', oldroot):
                self.assertTrue(app_paths.migrate_legacy_file('settings.json',new))
                self.assertEqual(json.loads(new.read_text(encoding='utf-8'))['username'],'old')
                new.write_text('{"username":"new"}',encoding='utf-8')
                self.assertFalse(app_paths.migrate_legacy_file('settings.json',new))
                self.assertEqual(json.loads(new.read_text(encoding='utf-8'))['username'],'new')

    def test_gift_cache_writes_to_user_data(self):
        with tempfile.TemporaryDirectory() as d:
            old = gift_catalog.CATALOG_PATH
            gift_catalog.CATALOG_PATH = Path(d)/'subdir'/'gift_catalog.json'
            try:
                gift_catalog.set_override('Rose',3)
                self.assertTrue(gift_catalog.CATALOG_PATH.is_file())
                self.assertEqual(gift_catalog.price_for('Rose'),3)
            finally:
                gift_catalog.CATALOG_PATH = old


class EventBusTests(unittest.IsolatedAsyncioTestCase):
    async def test_publish_async_sync_and_failure_isolation(self):
        bus = EventBus(history_limit=2)
        received = []
        bus.subscribe(lambda event: received.append(('sync',event.sequence)))
        def failure(event):
            raise RuntimeError('simulate subscriber failure')
        bus.subscribe(failure)
        async def after(event):
            await asyncio.sleep(0)
            received.append(('async',event.sequence))
        bus.subscribe(after)
        with self.assertLogs(level='ERROR'):
            for kind in ('gift','like','follow'):
                await bus.publish({'type':kind,'username':'Tester'},simulated=kind=='gift')
        self.assertEqual(received[-1],('async',3))
        self.assertEqual([e.sequence for e in bus.recent()], [2,3])
        self.assertEqual(bus.recent()[0].kind,'like')

    async def test_reject_invalid_events(self):
        bus = EventBus()
        with self.assertRaises(ValueError):
            await bus.publish({'type':'unknown'})
        self.assertEqual(len(bus.recent()),0)


class PlaybackTests(unittest.TestCase):
    def test_only_one_active_and_ack_is_validated(self):
        now = [10.0]
        scheduler = PlaybackCoordinator(clock=lambda: now[0])
        scheduler.register('screen1');scheduler.register('screen2')
        p1 = scheduler.enqueue('screen1',{'name':'first'},duration_ms=2000)
        p2 = scheduler.enqueue('screen2',{'name':'second'},duration_ms=2000)
        self.assertEqual(scheduler.take_next().id,p1.id)
        self.assertIsNone(scheduler.take_next())
        self.assertFalse(scheduler.complete('unknown-token'))
        self.assertTrue(scheduler.complete(p1.id))
        self.assertEqual(scheduler.take_next().id,p2.id)

    def test_round_robin_fairness(self):
        q=PlaybackCoordinator()
        q.register('a');q.register('b')
        for n in range(3): q.enqueue('a', {'n':n})
        q.enqueue('b',{'n':'b'})
        played=[]
        for _ in range(4):
            active=q.take_next();played.append(active.screen);q.complete(active.id)
        self.assertEqual(played,['a','b','a','a'])

    def test_overflow_timeout_and_recovery(self):
        clock=[0.]
        q=PlaybackCoordinator(default_capacity=1,clock=lambda:clock[0])
        q.register('gift')
        first=q.enqueue('gift',{'x':1},duration_ms=250)
        self.assertIsNone(q.enqueue('gift',{'x':2}))
        self.assertEqual(q.take_next().id, first.id)
        second=q.enqueue('gift',{'x':3})
        clock[0]=2.3
        self.assertTrue(q.expire())
        self.assertEqual(q.take_next().id,second.id)

    def test_unregistration_clears_active_screen(self):
        q=PlaybackCoordinator();q.register('a');q.register('b')
        q.enqueue('a',{})
        q.take_next();q.unregister('a')
        self.assertIsNone(q.active)
        self.assertNotIn('a',q.status()['pending'])

    def test_invalid_limits(self):
        with self.assertRaises(ValueError): PlaybackCoordinator(default_capacity=0)
        q=PlaybackCoordinator();q.register('a')
        with self.assertRaises(ValueError): q.enqueue('a',{},duration_ms=35000)
        with self.assertRaises(KeyError): q.enqueue('unknown',{})


class SimulatorTests(unittest.TestCase):
    def test_samples_always_simulated(self):
        for kind in ('gift','like','follow','comment'):
            obj=sample_event(kind,username='سالم')
            self.assertTrue(obj['test_mode'])
            self.assertEqual(obj['username'],'سالم')
        self.assertEqual(sample_event('like',count=5000000)['count'],1000000)
        with self.assertRaises(ValueError):sample_event('custom')

    def test_frozen_python_presence_checks_disabled(self):
        source = (ROOT/'connection_manager.py').read_text(encoding='utf-8')
        main = (ROOT/'main.py').read_text(encoding='utf-8')
        self.assertIn('if not getattr(sys, "frozen", False) and not script.exists():',source)
        self.assertIn('if not getattr(sys, "frozen", False) and not script.exists():',main)
        self.assertIn('open_simulator',main)


if __name__ == '__main__':
    unittest.main()


class DiagnosticTests(unittest.TestCase):
    def test_log_path_and_rotation_limits(self):
        code = (ROOT / 'diagnostics.py').read_text(encoding='utf-8')
        self.assertIn("location / 'crash.log'", code)
        self.assertIn('backupCount=2', code)
        self.assertIn('encoding=\'utf-8\'', code)

    def test_selftest_refuses_real_user_dir(self):
        from ven0m_selftest import run
        with patch.dict(os.environ, {'VEN0M_DATA_DIR': ''}):
            self.assertEqual(run(), 2)
