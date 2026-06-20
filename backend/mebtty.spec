# -*- mode: python ; python-option flags: 'u' -*-
# PyInstaller spec file for MebTTY

import os

block_cipher = None

ROOT = SPECPATH
FRONTEND_DIST = os.path.join(ROOT, '..', 'frontend', 'dist')

a = Analysis(
    ['bundle_entry.py'],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (FRONTEND_DIST, 'frontend_dist'),
    ],
    hiddenimports=[
        # MebTTY app modules (not statically imported from bundle_entry.py)
        'app',
        'app.local_users',
        'app.main',
        'app.config',
        'app.database',
        'app.models',
        'app.schemas',
        'app.auth',
        'app.auth.router',
        'app.auth.service',
        'app.auth.dependencies',
        'app.session',
        'app.session.router',
        'app.session.service',
        'app.terminal',
        'app.terminal.router',
        'app.terminal.manager',
        'app.terminal.runtime',
        'app.terminal.host_runtime',
        'app.terminal.ws_handler',
        'app.audit',
        'app.audit.router',
        'app.audit.service',
        'app.file',
        'app.file.router',
        'app.settings',
        'app.settings.router',
        # uvicorn internals
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        # fastapi / starlette
        'starlette.responses',
        'starlette.routing',
        'starlette.middleware',
        'starlette.middleware.cors',
        'starlette.staticfiles',
        'starlette.templating',
        # sqlalchemy
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.ext.asyncio',
        'aiosqlite',
        # auth / crypto
        'jose',
        'bcrypt',
        'cryptography',
        'cryptography.hazmat',
        'cryptography.hazmat.backends',
        'cryptography.hazmat.primitives',
        # multipart (file uploads)
        'multipart',
        'python_multipart',
        # email validation
        'email_validator',
        # httptools (uvicorn optional)
        'httptools',
        # websockets
        'websockets',
        'websockets.legacy',
        'websockets.legacy.server',
        # aiofiles
        'aiofiles',
        # pydantic-settings dotenv
        'dotenv',
        # anyio backends
        'anyio._backends',
        'anyio._backends._asyncio',
        # passlib
        'passlib',
        'passlib.handlers',
        'passlib.handlers.bcrypt',
        # yaml (pydantic-settings)
        'yaml',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'PIL',
        'pandas',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='mebtty',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
