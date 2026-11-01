#!/bin/sh
# A volatile diagnostic override; does not select a region or write EEPROM.
unit=org.tizen.tv.factory-service.service
dir=/run/systemd/system/$unit.d
conf=$dir/zz-tv-region-research.conf
lib=/run/tv-callsite-research/tv-localset-runtime-probe.so
log=/run/tv-callsite-research/rollback.log

if [ -e "$dir" ] || [ ! -r "$lib" ]; then
    echo 'Preflight failed: existing unit drop-in directory or missing library.'
    exit 1
fi
mkdir "$dir" || exit 1
rollback() {
    if [ -f "$conf" ]; then
        echo 'ROLLBACK_BEGIN'
        rm -f "$conf"
        rmdir "$dir" 2>/dev/null
        systemctl daemon-reload
        systemctl restart "$unit"
        echo 'ROLLBACK_END'
    else
        rmdir "$dir" 2>/dev/null
    fi
}
trap 'rollback' EXIT HUP INT TERM
printf '[Service]\nEnvironment=LD_PRELOAD=%s\n' "$lib" > "$conf" || exit 1
wait_ready() {
    attempts=0
    while [ "$attempts" -lt 20 ]; do
        if gdbus call --system --timeout 2 --dest org.tizen.tv.factory-service --object-path /TIFacSerObj --method org.tizen.tv.factoryservice.GetLocalSetStr 43 > /run/tv-callsite-research/readiness.log 2>&1; then
            cat /run/tv-callsite-research/readiness.log
            return 0
        fi
        attempts=$((attempts + 1))
        sleep 1
    done
    cat /run/tv-callsite-research/readiness.log
    return 1
}
# If the parent or its network connection is interrupted, a separate process
# makes a second attempt to remove the volatile override and restart normally.
(
    sleep 60
    if [ -f "$conf" ]; then
        rm -f "$conf"
        rmdir "$dir" 2>/dev/null
        systemctl daemon-reload
        systemctl restart "$unit"
    fi
) > "$log" 2>&1 < /dev/null &
watchdog=$!
echo 'RELOAD_BEGIN'
systemctl daemon-reload || exit 1
echo 'RESTART_BEGIN'
systemctl restart "$unit" || exit 1
echo 'TEST_SERVICE_STATE'
systemctl show "$unit" -p ActiveState -p MainPID -p Environment -p DropInPaths -p NRestarts
echo 'TEST_WAIT_READY'
wait_ready || exit 1
pid=$(systemctl show "$unit" -p MainPID --value)
grep 'tv-localset-runtime-probe' "/proc/$pid/maps" || :
echo 'TEST_LOCALSET_1'
gdbus call --system --timeout 5 --dest org.tizen.tv.factory-service --object-path /TIFacSerObj --method org.tizen.tv.factoryservice.GetLocalSetStr 1
echo 'TEST_LOCALSET_43'
gdbus call --system --timeout 5 --dest org.tizen.tv.factory-service --object-path /TIFacSerObj --method org.tizen.tv.factoryservice.GetLocalSetStr 43
echo 'TEST_COMPLETE'
rollback
trap - EXIT HUP INT TERM
kill "$watchdog" 2>/dev/null || :
echo 'RESTORED_SERVICE_STATE'
systemctl show "$unit" -p ActiveState -p MainPID -p Environment -p DropInPaths -p NRestarts
echo 'RESTORED_WAIT_READY'
wait_ready || exit 1
echo 'RESTORED_LOCALSET_1'
gdbus call --system --timeout 5 --dest org.tizen.tv.factory-service --object-path /TIFacSerObj --method org.tizen.tv.factoryservice.GetLocalSetStr 1
echo 'RESTORED_LOCALSET_43'
gdbus call --system --timeout 5 --dest org.tizen.tv.factory-service --object-path /TIFacSerObj --method org.tizen.tv.factoryservice.GetLocalSetStr 43
