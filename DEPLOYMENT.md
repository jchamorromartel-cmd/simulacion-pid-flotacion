# Publicación y despliegue

## Estado

El repositorio se publicó después de recibir autorización expresa del propietario:
https://github.com/jchamorromartel-cmd/simulacion-pid-flotacion
La rama publicada es `main`. No se modificó ningún otro proyecto.
El propietario comunicó que completó el despliegue en Streamlit Community Cloud:
https://simulacion-pid-flotacion.streamlit.app/
La verificación independiente desde el entorno de asistencia no se pudo completar;
comprobar el enlace en una ventana privada antes de entregar. El repositorio
GitHub no sustituye al servidor Streamlit. Los pasos siguientes se conservan
para poder reproducir el despliegue.

Nombre solicitado: `simulacion-pid-flotacion`.
Cuenta detectada mediante GitHub: `jchamorromartel-cmd`.
El conector de GitHub permite consultar repositorios, pero no ofrece creación
de repositorios en esta sesión. Git Credential Manager está instalado en Windows.
La conexión del conector y las credenciales de Git de VS Code son independientes;
se debe verificar la identidad antes de crear y publicar.

## Preparar localmente

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Python recomendado para Cloud: **3.12**. El entorno local probado es Python 3.13.14.
`requirements.txt` contiene solo dependencias de ejecución; las verificaciones
PDF y de navegador están en `requirements-dev.txt`.

## Crear GitHub, después de autorizar la publicación

El script `tools/publish_github.py --authorize-publication` está limitado al nombre
y cuenta indicados. Usa las credenciales de Git Credential Manager en memoria,
comprueba la cuenta y rechaza un repositorio que ya exista. No almacena ni imprime
el token. Si no hay credenciales, inicia sesión con Git Credential Manager o crea
manualmente el repositorio desde GitHub; no pegues tokens en el código ni en el chat.

Alternativa manual, con GitHub abierto en la cuenta correcta:

1. Crear **un repositorio nuevo público**, nombre `simulacion-pid-flotacion`.
   No inicializar README, licencia ni .gitignore desde la web.
2. En esta carpeta revisar `git status` y `git diff --cached`. `.venv`, backups,
   artifacts, results y secretos quedan excluidos mediante `.gitignore`.
3. Ejecutar, solo después de autorizar la publicación:

```powershell
git add .
git commit -m "Completar simulador PID de flotacion, animacion, PDF y documentacion"
git remote add origin https://github.com/jchamorromartel-cmd/simulacion-pid-flotacion.git
git push -u origin main
```

No usar force push. Si GitHub informa que el repositorio ya existe, detenerse y
elegir con el propietario un nombre nuevo; no reutilizar otro proyecto.
Si Git marca propiedad dudosa en el sandbox, ejecutar con la cuenta Windows
propietaria o pasar `-c safe.directory=<ruta exacta de esta carpeta>` a esa llamada;
no desactivar globalmente la protección con `*`.

## Streamlit Community Cloud

No hay un conector de Streamlit Cloud disponible en esta sesión ni acceso a una
sesión autenticada de ese servicio. La comprobación de navegador usa un perfil
aislado y no accede a tus sesiones personales. Pasos mínimos después del push:

1. Entrar en https://share.streamlit.io/ e iniciar sesión con GitHub.
2. Autorizar a Streamlit acceso al **nuevo** repositorio y elegir **Create app**.
3. Seleccionar `jchamorromartel-cmd/simulacion-pid-flotacion`, rama `main`, archivo
   `app.py`. En configuración avanzada elegir Python 3.12, si está disponible.
4. Pulsar **Deploy** y esperar instalación. No hacen falta secretos ni servicios externos.
5. Abrir la URL que devuelve Streamlit sin sesión (ventana privada). Verificar
   animación, perturbación, comparación y descarga PDF. Registrar la URL real
   solo después de esta comprobación. Si hay un error, guardar el log de despliegue.

Fuente oficial: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app

## Comprobación pública pendiente

```text
[x] Autorización expresa del propietario para publicar
[x] Repositorio nuevo creado; identidad y rama verificadas
[x] Commit y push de main
[ ] Instalación y arranque en Cloud sin errores
[ ] URL abierta sin autenticación
[ ] Reproducción, simulación y PDF comprobados desde la URL pública
```
