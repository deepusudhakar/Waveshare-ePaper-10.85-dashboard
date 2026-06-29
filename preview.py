#!/usr/bin/env python3
"""Render the dashboard to a PNG on a dev machine — no e-paper hardware needed.

The real `render_screen(epd, fonts)` only uses `epd.width`/`epd.height` and the
shared `data_store`, so a stub EPD plus some data is enough to produce a
pixel-accurate preview of the panel.

    uv run python preview.py            # offline, deterministic mock data
    uv run python preview.py --live     # start the real fetch thread, then render
    uv run python preview.py -o out.png # custom output path

Mock mode is instant and needs no network — best for iterating on layout.
Live mode exercises the real (auth-free) weather/crypto/ping fetch path.
"""
import argparse
import os
import sys
import time

from PIL import ImageFont

# `import main` is what the lazy-hardware-import change makes possible off-Pi.
import main
from main import render_screen, data_store, FONT_DIR

# The 10.85" panel is 1360x480; render_screen only reads .width/.height.
EPD_WIDTH, EPD_HEIGHT = 1360, 480


class StubEPD:
    width = EPD_WIDTH
    height = EPD_HEIGHT


def build_fonts():
    """Replicate the font set main() loads, so the preview matches the panel."""
    def load_font(name, size):
        return ImageFont.truetype(os.path.join(FONT_DIR, name), size)

    return {
        '20': load_font('Aldrich-Regular.ttc', 20),
        '24': load_font('Aldrich-Regular.ttc', 24),
        '28': load_font('Aldrich-Regular.ttc', 28),
        '32': load_font('Aldrich-Regular.ttc', 32),
        '35': load_font('Aldrich-Regular.ttc', 35),
        '40': load_font('Aldrich-Regular.ttc', 40),
        '60': load_font('Aldrich-Regular.ttc', 60),
        '80': load_font('Aldrich-Regular.ttc', 80),
        'clock': load_font('advanced_led_board-7.ttc', 180),
    }


def load_mock_data():
    """Inject representative values for the always-on widgets.

    Only the fields the default (weather + system/crypto) layout reads are set;
    everything else keeps DataStore's defaults, so disabled widgets fall back
    exactly as they do on the panel.
    """
    now = time.strftime("%Y-%m-%dT%H:00")
    hours = [time.strftime("%Y-%m-%dT%H:00", time.localtime(time.time() + 3600 * i))
             for i in range(1, 6)]
    with data_store.lock:
        data_store.weather = {
            'current': {
                'temperature_2m': 72.4, 'relative_humidity_2m': 55,
                'surface_pressure': 1006.2, 'wind_speed_10m': 8.0,
                'wind_direction_10m': 200, 'weather_code': 2,
                'is_day': 1, 'uv_index': 3.0,
            },
            'hourly': {
                'time': [now] + hours,
                'temperature_2m': [72, 71, 70, 69, 68, 67],
                'precipitation_probability': [10, 20, 35, 35, 40, 40],
                'precipitation': [0.0, 0.0, 0.01, 0.02, 0.03, 0.05],
                'weather_code': [2, 3, 61, 61, 80, 80],
            },
        }
        data_store.aqi = 22
        data_store.sysload = {'cpu': 4, 'ram_free': 123,
                              'history': [3, 5, 4, 6, 4, 4, 5, 3]}
        data_store.crypto = {'btc': 59976, 'eth': 1577,
                             'btc_hist': [1] * 10, 'eth_hist': [1] * 10}
        data_store.ping = {'current': 15, 'history': [12, 15, 14, 16, 15, 13]}


def load_live_data(seconds):
    """Start the real fetch thread and let it populate (weather/crypto/ping)."""
    import threading
    t = threading.Thread(target=main.update_data_thread, daemon=True)
    t.start()
    print(f"Fetching live data for {seconds}s...", file=sys.stderr)
    time.sleep(seconds)


def main_cli():
    ap = argparse.ArgumentParser(description="Render the dashboard to a PNG.")
    ap.add_argument('-o', '--output', default='preview.png', help='output PNG path')
    ap.add_argument('--live', action='store_true',
                    help='fetch real data instead of using the mock fixture')
    ap.add_argument('--live-seconds', type=int, default=8,
                    help='how long to let the live fetch run before rendering')
    args = ap.parse_args()

    if args.live:
        load_live_data(args.live_seconds)
    else:
        load_mock_data()

    image = render_screen(StubEPD(), build_fonts())
    image.save(args.output)
    print(f"Wrote {args.output} ({image.width}x{image.height})")


if __name__ == '__main__':
    main_cli()
