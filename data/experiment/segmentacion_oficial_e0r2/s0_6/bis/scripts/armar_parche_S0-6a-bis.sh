#!/bin/zsh
# Arma el parche de E0 de S0-6a-bis (U-SEG-OFICIAL), completo sobre el código de S0-5b; el diff contra el código del
# parche de S0-6a; y el diff del interruptor del prototipo. Prueba en seco los dos primeros sobre copias de los archivos
# de partida. Nunca toca el repo.
# Uso: armar_parche_S0-6a-bis.sh <código de S0-5b> <código de S0-6a> <código final> <prototipo> <dir parche/>
#        <dir de prueba (fuera del repo)>
B="$1"; A="$2"; F="$3"; P="$4"; O="$5"; T="$6"
mkdir -p "$O"; rm -f "$O/parche_e0_S0-6a-bis.diff" "$O/diff_contra_S0-6a_S0-6a-bis.diff"
for f in e0_lib.py correr_e0.py selftest_e0.py; do
  diff -u --label "a/$f" --label "b/$f" "$B/$f" "$F/$f" >> "$O/parche_e0_S0-6a-bis.diff"
  diff -u --label "a/$f" --label "b/$f" "$A/$f" "$F/$f" >> "$O/diff_contra_S0-6a_S0-6a-bis.diff"
done
cmp -s "$B/e0_tablas.py" "$F/e0_tablas.py" || echo "AVISO: e0_tablas.py cambió"
diff -u --label "a/correr_e0.py" --label "b/correr_e0.py" "$F/correr_e0.py" "$P/correr_e0.py" > "$O/interruptor_prototipo_S0-6a-bis.diff"
probar() {   # probar <diff> <código de partida> <nombre de la prueba>
  rm -rf "$T/$3"; mkdir -p "$T/$3"; cp "$2"/{e0_lib.py,correr_e0.py,selftest_e0.py} "$T/$3/"
  ( cd "$T/$3" && patch -p1 --dry-run < "$O/$1" > /dev/null && patch -p1 < "$O/$1" > /dev/null )
  echo "$1 $3 patch rc=$?"
  for f in e0_lib.py correr_e0.py selftest_e0.py; do cmp -s "$T/$3/$f" "$F/$f" && echo "  $f igual al final" || echo "  $f DISTINTO"; done
}
probar parche_e0_S0-6a-bis.diff "$B" sobre_S0-5b
probar diff_contra_S0-6a_S0-6a-bis.diff "$A" sobre_S0-6a
shasum -a 256 "$O/parche_e0_S0-6a-bis.diff" "$O/diff_contra_S0-6a_S0-6a-bis.diff" "$O/interruptor_prototipo_S0-6a-bis.diff" | sed 's|  .*/|  |'
lineas() {   # lineas <nombre> <código de partida>
  for f in e0_lib.py correr_e0.py selftest_e0.py; do
    echo "desde $1: $f $(shasum -a 256 "$2/$f" | cut -c1-64) $(shasum -a 256 "$F/$f" | cut -c1-64) \
+$(diff "$2/$f" "$F/$f" | grep -c '^>') −$(diff "$2/$f" "$F/$f" | grep -c '^<')"
  done
}
lineas S0-5b "$B"
lineas S0-6a "$A"
