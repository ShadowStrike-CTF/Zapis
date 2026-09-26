# zapis.spec — PyInstaller build (onefile, windowed). Build: pyinstaller zapis.spec
# © 2026 ShadowStrike. All rights reserved.
# Aut Viam Inveniam Aut Faciam
block_cipher = None

a = Analysis(
    ['src/zapis/__main__.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('src/zapis/static/index.html', 'zapis/static'),
        ('src/zapis/templates', 'zapis/templates'),
    ],
    # WeasyPrint data files and native libs are handled by the
    # pyinstaller-hooks-contrib hook-weasyprint; the probe build found no
    # missing weasyprint submodules, so no extra hidden imports are needed.
    hiddenimports=[],
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

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='zapis',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
