#!/bin/bash
# Build iris-plan-latest-mac: the latest conda-forge releases of main's dependencies, glue-qt 0.4.2 and irispy
# f058705 by pip --no-deps, main's tests and docs extras, the pre-commit's ruff, and main's worktree editable.
set -u
ENV=iris-plan-latest-mac
MM=/Users/nabil/mamba
W=/Users/nabil/Git/glue-solar-main
cd "$(dirname "$0")" || exit 1
micromamba create -y -n $ENV -c conda-forge python=3.13 \
  asdf astropy dask dkist glue-core gwcs matplotlib mpl-scatter-density ndcube numpy pillow pyqt6 qtpy reproject scipy sunpy \
  pytest pytest-qt pytest-xdist pytest-cov pytest-mock pooch filelock qtconsole-base pip git > create.log 2>&1 || { echo "CREATE FAILED"; tail -20 create.log; exit 1; }
PY=$MM/envs/$ENV/bin/python
# conda-forge lags main's floors (2026-10-31: glue-core 1.27.0, echo 0.15.0, dkist 1.17.0, pyqt6 6.11.0): PyPI's latest
$PY -m pip install -U --no-deps glue-core echo dkist > pip.log 2>&1 || echo "floor upgrades failed"
$PY -m pip install -U PyQt6 pvextractor sunraster 'ipython<9' >> pip.log 2>&1 || echo "PyQt6 or missing deps failed"
$PY -m pip install --no-deps glue-qt==0.4.2 >> pip.log 2>&1 || echo "glue-qt install failed"
$PY -m pip install --no-deps "irispy-lmsal @ git+https://github.com/LM-SAL/irispy.git@f0587057b255015c820b4fb4239cfbec67b5e354" >> pip.log 2>&1 || echo "irispy install failed"
EXTRAS=$($PY -c "import tomllib;d=tomllib.load(open('$W/pyproject.toml','rb'))['project']['optional-dependencies'];print(' '.join(repr(x) for x in d.get('tests',[])+d.get('docs',[])))")
echo "extras: $EXTRAS"
eval $PY -m pip install $EXTRAS >> pip.log 2>&1 || echo "extras install failed"
RUFF=$(grep -A1 'ruff-pre-commit' $W/.pre-commit-config.yaml | grep -o 'v[0-9][0-9.]*' | head -1)
echo "ruff pin: $RUFF"
$PY -m pip install setuptools-scm "ruff==${RUFF#v}" >> pip.log 2>&1 || echo "ruff install failed"
$PY -m pip install --no-deps -e $W >> pip.log 2>&1 || echo "editable install failed"
$PY -m pip check > check.log 2>&1; echo "pip check: $(head -c 600 check.log)"
$PY -c "from importlib.metadata import version as v; print(*(f'{p} {v(p)}' for p in ('astropy','ndcube','sunpy','dkist','glue-core','glue-qt','irispy-lmsal','PyQt6','numpy','pytest','ruff','glue-solar')), sep='\n')" > versions.log 2>&1
cat versions.log
echo DONE
