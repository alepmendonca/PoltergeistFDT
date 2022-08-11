# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['Runner.py'],
    pathex=[],
    binaries=[('venv/share/py4j/*', 'share/py4j')],
    datas=[('resources', 'resources'), ('mysqldump', 'mysqldump'),
        ('wkhtmltopdf', 'wkhtmltopdf'),
        ('tika-server', 'tika-server'),
        ('efd-pva-inspector/bin', 'efd-pva-inspector/bin'),
        ('venv/Lib/site-packages/autoit/lib/*', 'autoit/lib')],
    hiddenimports=['py4j.java_collections', 'AiimProofGenerator'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
splash = Splash(
    'resources/splash.jpg',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=(20, 320),
    text_size=16,
    text_color='white',
    text_default='Abduzindo...',
    minify_script=True,
    always_on_top=True,
)

exe = EXE(
    pyz,
    a.scripts,
    splash,
    [],
    exclude_binaries=True,
    name='PoltergeistFDT',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources\\ghost.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    splash.binaries,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PoltergeistFDT',
)
