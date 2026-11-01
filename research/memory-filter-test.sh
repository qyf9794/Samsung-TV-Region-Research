#!/bin/sh
# One reversible, process-memory-only comparison test on the inspected build.
# Never calls a setting method and never writes an EEPROM device.
unit=org.tizen.tv.factory-service.service
base=/run/tv-memory-filter-test
offset_words=229844   # 0x703a8 / 2
pid=$(systemctl show "$unit" -p MainPID --value)
start=$(awk '{print $22}' "/proc/$pid/stat")
same_process() {
    [ "$(systemctl show "$unit" -p MainPID --value)" = "$pid" ] &&
    [ "$(readlink "/proc/$pid/exe")" = /usr/bin/TIFSDaemon ] &&
    [ "$(awk '{print $22}' "/proc/$pid/stat" 2>/dev/null)" = "$start" ]
}
read_code() {
    dd if="/proc/$pid/mem" bs=2 skip="$offset_words" count=1 2>/dev/null | od -An -t x1 | tr -d ' \n'
}
write_original() {
    printf '\015\053' | dd of="/proc/$pid/mem" bs=2 seek="$offset_words" count=1 conv=notrunc 2>/dev/null
}
write_candidate() {
    printf '\377\053' | dd of="/proc/$pid/mem" bs=2 seek="$offset_words" count=1 conv=notrunc 2>/dev/null
}
pause_process() {
    kill -STOP "$pid" || return 1
    n=0
    while [ "$n" -lt 20 ]; do
        state=$(awk '/^State:/ {print $2}' "/proc/$pid/status" 2>/dev/null)
        [ "$state" = T ] && return 0
        [ "$state" = t ] && return 0
        n=$((n+1))
        sleep 0.1
    done
    kill -CONT "$pid" 2>/dev/null
    return 1
}
rollback() {
    if same_process && pause_process; then
        current=$(read_code)
        case "$current" in
            ff2b) write_original; echo "RESTORED_CODE=$(read_code)" ;;
            0d2b) echo CODE_ALREADY_ORIGINAL ;;
            *) echo "UNEXPECTED_CODE=$current" ;;
        esac
        kill -CONT "$pid" 2>/dev/null
    else
        kill -CONT "$pid" 2>/dev/null
        echo PROCESS_CHANGED_OR_UNAVAILABLE
    fi
}
if [ -z "$pid" ] || [ "$pid" = 0 ] || ! same_process || [ "$(read_code)" != 0d2b ]; then
    echo PREFLIGHT_FAILED
    exit 1
fi
trap rollback EXIT HUP INT TERM
# The watchdog is a second, independent attempt to restore and resume if the
# controlling shell is interrupted. A new process starts from unmodified disk.
(
    sleep 35
    rollback
) > "$base/watchdog.log" 2>&1 < /dev/null &
watchdog=$!
echo "PID=$pid ORIGINAL=$(read_code)"
if ! pause_process; then echo PAUSE_FAILED; exit 1; fi
if ! same_process || [ "$(read_code)" != 0d2b ]; then
    kill -CONT "$pid" 2>/dev/null
    echo PROCESS_CHANGED_DURING_PAUSE
    exit 1
fi
write_candidate || { kill -CONT "$pid" 2>/dev/null; echo WRITE_FAILED; exit 1; }
echo "PATCHED_CODE=$(read_code)"
kill -CONT "$pid" || exit 1
echo TEST_LOCALSET_1
gdbus call --system --timeout 5 --dest org.tizen.tv.factory-service --object-path /TIFacSerObj --method org.tizen.tv.factoryservice.GetLocalSetStr 1
echo TEST_LOCALSET_43
gdbus call --system --timeout 5 --dest org.tizen.tv.factory-service --object-path /TIFacSerObj --method org.tizen.tv.factoryservice.GetLocalSetStr 43
rollback
trap - EXIT HUP INT TERM
kill "$watchdog" 2>/dev/null || :
echo "FINAL_CODE=$(read_code)"
echo FINAL_SERVICE_STATE
systemctl show "$unit" -p MainPID -p ActiveState -p Environment -p DropInPaths
echo FINAL_LOCALSET_1
gdbus call --system --timeout 5 --dest org.tizen.tv.factory-service --object-path /TIFacSerObj --method org.tizen.tv.factoryservice.GetLocalSetStr 1
echo FINAL_LOCALSET_43
gdbus call --system --timeout 5 --dest org.tizen.tv.factory-service --object-path /TIFacSerObj --method org.tizen.tv.factoryservice.GetLocalSetStr 43
