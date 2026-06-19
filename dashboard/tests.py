from pathlib import Path
import tempfile
import datetime as dt

import h5py

from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Simulation, SimulationRun


@override_settings(ROOT_URLCONF='r2h2_ui.urls')
class Run1HzViewTests(TestCase):
	def setUp(self):
		self.temp_dir = tempfile.TemporaryDirectory()
		self.addCleanup(self.temp_dir.cleanup)
		self.override_media = override_settings(MEDIA_ROOT=self.temp_dir.name)
		self.override_media.enable()
		self.addCleanup(self.override_media.disable)

		self.simulation = Simulation.objects.create(
			name='1Hz Test Simulation',
			datum_date=dt.date(2024, 3, 9),
		)

	def _create_run_file(self, run, *, with_1hz, num_points=3):
		outputs_dir = Path(self.temp_dir.name) / 'outputs'
		outputs_dir.mkdir(parents=True, exist_ok=True)
		abs_path = outputs_dir / f'run_{run.id}.h5'

		with h5py.File(abs_path, 'w') as h5_file:
			meta = h5_file.create_group('meta')
			meta.attrs['simulation_name'] = self.simulation.name
			if with_1hz:
				ts_group = h5_file.create_group('time_series_1hz')
				ts_group.attrs['start_hour'] = 0
				ts_group.attrs['end_hour'] = 1
				time_indices = list(range(num_points))
				values = [float(idx) for idx in range(num_points)]
				ts_group.create_dataset('time_indices', data=time_indices)
				ts_group.create_dataset('arBuffer1', data=values)

		run.output_path = f'outputs/{abs_path.name}'
		run.run_start_date = dt.date(2024, 3, 9)
		run.save(update_fields=['output_path', 'run_start_date'])
		return abs_path

	def test_simulation_detail_shows_view_1hz_link_when_available(self):
		run = SimulationRun.objects.create(simulation=self.simulation, status=SimulationRun.DONE)
		self._create_run_file(run, with_1hz=True)

		response = self.client.get(reverse('dashboard-simulation-detail', args=[self.simulation.id]))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, reverse('dashboard-run-1hz', args=[self.simulation.id, run.id]))
		self.assertContains(response, 'View 1Hz')

	def test_simulation_detail_hides_view_1hz_link_when_group_missing(self):
		run = SimulationRun.objects.create(simulation=self.simulation, status=SimulationRun.DONE)
		self._create_run_file(run, with_1hz=False)

		response = self.client.get(reverse('dashboard-simulation-detail', args=[self.simulation.id]))

		self.assertEqual(response.status_code, 200)
		self.assertNotContains(response, reverse('dashboard-run-1hz', args=[self.simulation.id, run.id]))

	def test_run_1hz_view_renders_plot_page(self):
		run = SimulationRun.objects.create(simulation=self.simulation, status=SimulationRun.DONE)
		self._create_run_file(run, with_1hz=True)

		response = self.client.get(reverse('dashboard-run-1hz', args=[self.simulation.id, run.id]))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'run-1hz-series')
		self.assertContains(response, 'arBuffer1')
		self.assertContains(response, 'Samples Shown')
		self.assertContains(response, 'run-1hz-plot-keys')
		self.assertContains(response, '2024-03-09T00:00:00Z')

	def test_run_1hz_view_redirects_when_group_missing(self):
		run = SimulationRun.objects.create(simulation=self.simulation, status=SimulationRun.DONE)
		self._create_run_file(run, with_1hz=False)

		response = self.client.get(reverse('dashboard-run-1hz', args=[self.simulation.id, run.id]))

		self.assertRedirects(response, reverse('dashboard-simulation-detail', args=[self.simulation.id]))

	def test_run_1hz_data_endpoint_returns_full_resolution_for_small_zoom_window(self):
		run = SimulationRun.objects.create(simulation=self.simulation, status=SimulationRun.DONE)
		self._create_run_file(run, with_1hz=True, num_points=10)

		response = self.client.get(
			reverse('dashboard-run-1hz-data', args=[self.simulation.id, run.id]),
			{
				'start': '2024-03-09T00:00:02Z',
				'end': '2024-03-09T00:00:04Z',
			},
		)

		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertTrue(payload['is_full_resolution'])
		self.assertEqual(payload['downsample_step'], 1)
		self.assertEqual(payload['window_points'], 3)
		self.assertEqual(payload['series'][0]['y'], [2.0, 3.0, 4.0])
		self.assertEqual(payload['window_start'], '2024-03-09T00:00:02Z')

	def test_run_1hz_data_endpoint_downsamples_large_window(self):
		run = SimulationRun.objects.create(simulation=self.simulation, status=SimulationRun.DONE)
		self._create_run_file(run, with_1hz=True, num_points=5001)

		response = self.client.get(reverse('dashboard-run-1hz-data', args=[self.simulation.id, run.id]))

		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertFalse(payload['is_full_resolution'])
		self.assertGreater(payload['downsample_step'], 1)
		self.assertEqual(payload['points_total'], 5001)
		self.assertLessEqual(payload['points_shown'], 4000)
