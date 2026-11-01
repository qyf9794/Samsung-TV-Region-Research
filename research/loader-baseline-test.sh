#!/bin/sh
# Minimal library test. No factory data, EEPROM, or region writes.
unit=org.tizen.tv.factory-service.service
dir=/run/systemd/system/$unit.d
conf=$dir/zz-tv-loader-research.conf
base=/run/tv-loader-research
lib=${TV_TEST_LIB:-$base/tv-preload-test.so}
test ! -e "$dir" && test -r "$lib" || exit 1
mkdir "$dir" || exit 1
rollback() {
    if [ -f "$conf" ]; then
        echo ROLLBACK_BEGIN
        rm -f "$conf"
        rmdir "$dir" 2>/dev/null
        systemctl daemon-reload
        systemctl restart "$unit"
        echo ROLLBACK_END
    else
        rmdir "$dir" 2>/dev/null
    fi
}
trap rollback EXIT HUP INT TERM
: > "$base/stderr.log" || exit 1
chmod 666 "$base/stderr.log"
printf '[Service]\nStandardError=file:%s/stderr.log\nRestart=no\n' "$base" > "$conf" || exit 1
if [ "${TV_TEST_SKIP_PRELOAD:-0}" != 1 ]; then
    printf 'Environment=LD_PRELOAD=%s\n' "$lib" >> "$conf" || exit 1
fi
(
    sleep 45
    if [ -f "$conf" ]; then
        rm -f "$conf"
        rmdir "$dir" 2>/dev/null
        systemctl daemon-reload
        systemctl restart "$unit"
    fi
) > "$base/watchdog.log" 2>&1 < /dev/null &
watchdog=$!
systemctl daemon-reload || exit 1
systemctl restart "$unit" || exit 1
echo TEST_BEGIN
ready=0
i=0
while [ "$i" -lt 12 ]; do
    if gdbus call --system --timeout 1 --dest org.tizen.tv.factory-service --object-path /TIFacSerObj --method org.tizen.tv.factoryservice.GetLocalSetStr 43 > "$base/response.log" 2>&1; then
        ready=1
        break
    fi
    i=$((i+1))
    sleep 1
done
echo "READY=$ready POLLS=$i"
cat "$base/response.log"
systemctl show "$unit" -p MainPID -p ActiveState -p SubState -p Result -p NRestarts -p ExecMainCode -p ExecMainStatus -p Environment -p DropInPaths
echo SERVICE_STDERR
cat "$base/stderr.log"
pid=$(systemctl show "$unit" -p MainPID --value)
if [ "$pid" -gt 0 ] 2>/dev/null; then
    ps -o pid,stat,wchan,args -p "$pid"
    grep -E '^(Name|State|TracerPid|Seccomp):' "/proc/$pid/status"
    grep -F "$lib" "/proc/$pid/maps" || echo LIBRARY_NOT_OBSERVED_IN_MAPS
fi
rollback
trap - EXIT HUP INT TERM
kill "$watchdog" 2>/dev/null || :
echo RESTORED
systemctl show "$unit" -p MainPID -p ActiveState -p Environment -p DropInPaths
