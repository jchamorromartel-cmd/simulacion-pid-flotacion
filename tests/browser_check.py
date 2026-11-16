"""Prueba manual automatizada del navegador: python tests/browser_check.py.

Usa Chrome/Edge instalado; inicia Streamlit en un puerto local aislado.
No requiere ni utiliza una sesión autenticada del navegador.
"""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.request import urlopen
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from simulation import Config, simulate
from pypdf import PdfReader


def main():
    output = ROOT/'artifacts'
    output.mkdir(exist_ok=True)
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
    logfile = (output/'streamlit.log').open('w', encoding='utf-8')
    process = subprocess.Popen([sys.executable, '-m', 'streamlit', 'run', 'app.py',
                                '--server.port', str(port), '--server.address', '127.0.0.1',
                                '--server.headless', 'true', '--browser.gatherUsageStats', 'false'],
                               cwd=ROOT, stdout=logfile, stderr=subprocess.STDOUT)
    try:
        for _ in range(100):
            try:
                with urlopen(f'http://127.0.0.1:{port}/_stcore/health', timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.2)
        else:
            raise RuntimeError('Streamlit no inicia')
        candidates = [shutil.which('google-chrome'), shutil.which('chromium'),
                      'C:/Program Files/Google/Chrome/Application/chrome.exe',
                      'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe']
        executable = next((p for p in candidates if p and Path(p).exists()), None)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, **({'executable_path': executable} if executable else {}))
            page = browser.new_page(viewport={'width': 1440, 'height': 1100}, device_scale_factor=1)
            errors = []
            page.on('pageerror', lambda err: errors.append(str(err)))
            page.goto(f'http://127.0.0.1:{port}', wait_until='networkidle')
            page.get_by_role('heading', name='Control PID de nivel en tres celdas de flotación').wait_for()
            page.wait_for_function("document.querySelectorAll('iframe').length > 0")
            frame = page.frame_locator('iframe').first
            frame.locator('#play').wait_for()
            frame.locator('#timeline').evaluate("e=>{e.value=195;e.dispatchEvent(new Event('input'))}")
            expected = simulate(Config())[195]
            assert f"{expected['h1']:.2f}" in frame.locator('#card1').inner_text()
            frame.locator('#play').click()
            page.wait_for_timeout(400)
            frame.locator('#pause').click()
            paused = frame.locator('#timeline').input_value()
            assert float(paused) > 195
            page.wait_for_timeout(300)
            assert frame.locator('#timeline').input_value() == paused
            frame.locator('#speed').select_option('30')
            frame.locator('#mode').select_option('PID + FF')
            frame.locator('#timeline').evaluate("e=>{e.value=195;e.dispatchEvent(new Event('input'))}")
            ff = simulate(Config(), True)[195]
            assert f"{ff['h2']:.2f}" in frame.locator('#card2').inner_text()
            page.screenshot(path=str(output/'desktop.png'), full_page=True)
            frame.locator('#reset').click()
            assert frame.locator('#timeline').input_value() == '0'
            page.get_by_role('tab', name='Comparación y exportación', exact=True).click()
            with page.expect_download() as info:
                page.get_by_role('button', name='Descargar informe PDF', exact=True).click()
            downloaded = output/'downloaded_report.pdf'
            info.value.save_as(downloaded)
            assert len(PdfReader(downloaded).pages) >= 8
            page.get_by_role('tab', name='Panel principal', exact=True).click()
            page.set_viewport_size({'width': 390, 'height': 844})
            page.wait_for_timeout(300)
            frame.locator('#timeline').evaluate("e=>{e.value=195;e.dispatchEvent(new Event('input'))}")
            assert frame.locator('.card').count() == 3
            assert frame.locator('body').evaluate('e=>e.scrollWidth <= window.innerWidth')
            page.screenshot(path=str(output/'mobile.png'), full_page=True)
            assert not errors, errors
            browser.close()
        result = {'health': 'OK', 'animation_data': 'OK', 'play_pause_reset': 'OK',
                  'mode_and_speed': 'OK', 'pdf_download': 'OK', 'responsive': 'OK', 'javascript_errors': errors}
        (output/'browser_results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps(result))
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        logfile.close()


if __name__ == '__main__':
    main()
