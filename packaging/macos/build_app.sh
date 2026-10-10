#!/bin/bash
# Build Glue Solar.app and Glue Solar.dmg, which holds it beside a link to /Applications, in dist/ beside this script,
# with the active environment's PyInstaller (docs/dev_guide/macos-app.rst)
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
rm -rf "$here/build" "$here/dist"
python -m PyInstaller --noconfirm --workpath "$here/build" --distpath "$here/dist/app" "$here/glue_solar.spec"
rm -rf "$here/dist/app/glue-solar"  # the folder the app holds
ln -s /Applications "$here/dist/app/Applications"
hdiutil create -volname "Glue Solar" -srcfolder "$here/dist/app" -format UDZO "$here/dist/Glue Solar.dmg"
