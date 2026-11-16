"""Publicación deliberada de este proyecto nuevo, usando Git Credential Manager.

No ejecutar hasta recibir autorización explícita del propietario.
No acepta otros nombres de repositorio ni usa tokens en argumentos o archivos.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OWNER, NAME = 'jchamorromartel-cmd', 'simulacion-pid-flotacion'
EXPECTED_URL = f'https://github.com/{OWNER}/{NAME}.git'


def git(*args, capture=False, input_text=None, env=None):
    # Excepción de propiedad limitada exactamente a este checkout.
    return subprocess.run(['git', '-c', f'safe.directory={ROOT.as_posix()}', *args],
                          cwd=ROOT, input=input_text, text=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None,
                          env=env, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authorize-publication', action='store_true')
    args = parser.parse_args()
    if not args.authorize_publication:
        parser.error('Se requiere autorización explícita; después usar --authorize-publication.')
    if not (ROOT/'.git').is_dir():
        raise RuntimeError('Falta el repositorio local preparado')
    if git('branch', '--show-current', capture=True).stdout.strip() != 'main':
        raise RuntimeError('La rama debe ser main')
    remotes = git('remote', capture=True).stdout.split()
    if remotes and (remotes != ['origin'] or git('remote', 'get-url', 'origin', capture=True).stdout.strip() != EXPECTED_URL):
        raise RuntimeError('Hay otro remoto: no se modifica')
    # Solo los archivos revisables de esta carpeta; Git aplica .gitignore.
    git('add', '--all', '.')
    files = git('ls-files', '-z', capture=True).stdout.split('\0')
    for name in filter(None, files):
        if any(part in {'.venv', 'backups', 'artifacts', '__pycache__', '.aws'} for part in Path(name).parts):
            raise RuntimeError('Hay archivos excluidos en el índice')
        content = (ROOT/name).read_bytes()
        if re.search(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)', content):
            raise RuntimeError('Se detectó un posible secreto; revisar índice antes de publicar')
    env = dict(os.environ, GCM_INTERACTIVE='never', GIT_TERMINAL_PROMPT='0')
    try:
        credential = git('credential', 'fill', capture=True,
                         input_text='protocol=https\nhost=github.com\n\n', env=env).stdout
    except subprocess.CalledProcessError:
        raise RuntimeError('Git Credential Manager no tiene una sesión utilizable. Iniciar sesión GitHub desde VS Code/GCM y reintentar.') from None
    fields = dict(line.split('=', 1) for line in credential.splitlines() if '=' in line)
    token = fields.get('password')
    if not token:
        raise RuntimeError('Faltan credenciales GitHub. No pegar tokens en el código.')

    def api(path, data=None):
        request = Request('https://api.github.com'+path,
                          data=json.dumps(data).encode() if data is not None else None,
                          headers={'Authorization': 'Bearer '+token, 'Accept': 'application/vnd.github+json',
                                   'Content-Type': 'application/json', 'User-Agent': 'flotacion-pid-publisher'})
        with urlopen(request, timeout=30) as response:
            return json.load(response)

    if api('/user')['login'].lower() != OWNER:
        raise RuntimeError('La cuenta de Git no coincide con la cuenta autorizada')
    state_path = ROOT/'artifacts'/'publication_state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else None
    try:
        repo = api(f'/repos/{OWNER}/{NAME}')
    except HTTPError as error:
        if error.code != 404:
            raise
        repo = None
    if repo is not None and (not state or state.get('repo_id') != repo['id'] or state.get('full_name') != repo['full_name']):
        raise RuntimeError('El repositorio ya existe y no fue creado por este flujo. No se modifica.')
    if repo is None:
        repo = api('/user/repos', {'name': NAME, 'description': 'Simulador académico Streamlit de tres celdas con PID completo, feedforward, animación y PDF.',
                                   'private': False, 'auto_init': False})
        state_path.parent.mkdir(exist_ok=True)
        state_path.write_text(json.dumps({'repo_id': repo['id'], 'full_name': repo['full_name'], 'html_url': repo['html_url']}, indent=2))
    if repo['full_name'].lower() != f'{OWNER}/{NAME}' or repo['private']:
        raise RuntimeError('Repositorio devuelto diferente del solicitado')
    # commit y push solo después de autorización y validación de la cuenta.
    changed = git('diff', '--cached', '--name-only', capture=True).stdout.strip()
    if changed:
        git('commit', '-m', 'Completar simulador PID: animacion, PDF, PLC y pruebas')
    if not remotes:
        git('remote', 'add', 'origin', EXPECTED_URL)
    git('push', '-u', 'origin', 'main', env=env)
    head = git('rev-parse', 'HEAD', capture=True).stdout.strip()
    remote_head = git('ls-remote', 'origin', 'refs/heads/main', capture=True, env=env).stdout.split()[0]
    if head != remote_head:
        raise RuntimeError('El SHA remoto no coincide con el local')
    print(json.dumps({'repository': repo['html_url'], 'branch': 'main', 'sha': head}))


if __name__ == '__main__':
    try:
        main()
    except HTTPError as exc:
        print(f'GitHub devolvió HTTP {exc.code}. Verificar permisos para crear repositorios públicos; no se muestran credenciales.', file=sys.stderr)
        raise SystemExit(1)
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(str(exc) if isinstance(exc, RuntimeError) else 'Falló una operación Git; revisar autenticación y estado local.', file=sys.stderr)
        raise SystemExit(1)
