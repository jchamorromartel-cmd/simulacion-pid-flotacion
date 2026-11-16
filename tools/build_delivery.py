"""Crear un ZIP entregable: ejecutar desde el entorno con requirements instalado.

Incluye fuentes versionadas y un informe nominal; excluye el entorno virtual,
Git, secretos, respaldos y resultados temporales. No publica ni despliega nada.
"""
import ast
import hashlib
from pathlib import Path
import subprocess
import zipfile
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reporting import pdf_report
from simulation import Config, simulate


def main():
    """Empaquetar, verificar CRC/sintaxis y dejar instrucciones de entrega."""
    output = ROOT/'entrega'
    output.mkdir(exist_ok=True)
    path = output/'simulacion-pid-flotacion.zip'
    tracked = subprocess.run(['git', '-c', f'safe.directory={ROOT.as_posix()}',
                              'ls-files', '-z'], cwd=ROOT, check=True,
                             capture_output=True).stdout.decode('utf-8').split('\0')
    names = set(filter(None, tracked)) | {'ENTREGA_DOCENTE.md', 'tools/build_delivery.py'}
    forbidden = {'.git', '.venv', '__pycache__', 'backups', 'artifacts', 'entrega'}
    for name in names:
        if forbidden.intersection(Path(name).parts) or name.endswith('secrets.toml') or name.startswith('.env'):
            raise RuntimeError('Archivo excluido detectado en la selección')
    config = Config()
    report = pdf_report(config, {'PID': simulate(config), 'PID + FF': simulate(config, True)})
    prefix = 'simulacion-pid-flotacion/'
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(names):
            archive.write(ROOT/name, prefix+name)
        archive.writestr(prefix+'informes/informe_resultados.pdf', report)
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise RuntimeError('Falló la integridad del ZIP')
        for name in archive.namelist():
            if name.endswith('.py'):
                ast.parse(archive.read(name).decode('utf-8-sig'), filename=name)
        assert prefix+'app.py' in archive.namelist()
        assert prefix+'simulation.py' in archive.namelist()
        assert prefix+'requirements.txt' in archive.namelist()
        count = len(archive.namelist())
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    (output/'SHA256.txt').write_text(f'{digest}  {path.name}\n', encoding='utf-8')
    message = ('Docente:\n\nAdjunto el proyecto de simulación y control PID de tres celdas de flotación. '
               'El ZIP contiene el código Python comentado, los modelos matemáticos, '
               'el diseño Ladder/ST, las pruebas, las instrucciones y un informe PDF.\n\n'
               'Aplicación web: https://simulacion-pid-flotacion.streamlit.app/\n'
               'Repositorio: https://github.com/jchamorromartel-cmd/simulacion-pid-flotacion\n\n'
               'Archivo principal: app.py. Los modelos y el PID están en simulation.py.\n')
    (output/'MENSAJE_PARA_DOCENTE.txt').write_text(message, encoding='utf-8')
    print(f'ZIP: {path}\nArchivos: {count}\nBytes: {path.stat().st_size}\nSHA256: {digest}')


if __name__ == '__main__':
    main()
