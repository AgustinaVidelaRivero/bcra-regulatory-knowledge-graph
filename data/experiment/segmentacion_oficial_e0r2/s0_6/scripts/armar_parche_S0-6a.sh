#!/bin/zsh
# Arma el parche de E0 de S0-6a (U-SEG-OFICIAL) y el diff del interruptor del prototipo, y prueba el parche en seco sobre
# una copia de los archivos de partida. Nunca toca el repo.
# Uso: armar_parche_S0-6a.sh <dir del código de partida (S0-5b)> <dir del código final> <dir del prototipo> <dir parche/>
#        <dir de prueba (vacío, fuera del repo)>
B="$1"; F="$2"; P="$3"; O="$4"; T="$5"
mkdir -p "$O"; rm -f "$O/parche_e0_S0-6a.diff"
for f in e0_lib.py correr_e0.py selftest_e0.py; do
  diff -u --label "a/$f" --label "b/$f" "$B/$f" "$F/$f" >> "$O/parche_e0_S0-6a.diff"
done
cmp -s "$B/e0_tablas.py" "$F/e0_tablas.py" || echo "AVISO: e0_tablas.py cambió"
diff -u --label "a/correr_e0.py" --label "b/correr_e0.py" "$F/correr_e0.py" "$P/correr_e0.py" > "$O/interruptor_prototipo_S0-6a.diff"
rm -rf "$T"; mkdir -p "$T"; cp "$B"/{e0_lib.py,correr_e0.py,selftest_e0.py} "$T/"
( cd "$T" && patch -p1 --dry-run < "$O/parche_e0_S0-6a.diff" > /dev/null && patch -p1 < "$O/parche_e0_S0-6a.diff" > /dev/null )
echo "patch rc=$?"
for f in e0_lib.py correr_e0.py selftest_e0.py; do cmp -s "$T/$f" "$F/$f" && echo "$f igual al final" || echo "$f DISTINTO"; done
shasum -a 256 "$O/parche_e0_S0-6a.diff" "$O/interruptor_prototipo_S0-6a.diff" | sed 's|  .*/|  |'
for f in e0_lib.py correr_e0.py selftest_e0.py; do
  echo "$f $(shasum -a 256 "$B/$f" | cut -c1-64) $(shasum -a 256 "$F/$f" | cut -c1-64) \
+$(diff "$B/$f" "$F/$f" | grep -c '^>') −$(diff "$B/$f" "$F/$f" | grep -c '^<')"
done
