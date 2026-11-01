#!/bin/sh
# TV-side command, invoked by select_us.py. Only QA75QN85BAJXXZ / 1651.7.
set -eu
mode=${1:---check}
case "$mode" in --check|--apply) ;; *) echo '参数错误'; exit 2 ;; esac
unit=org.tizen.tv.factory-service.service
dest=org.tizen.tv.factory-service
path=/TIFacSerObj
iface=org.tizen.tv.factoryservice
call() { method=$1; shift; gdbus call --system --timeout 8 --dest "$dest" --object-path "$path" --method "$iface.$method" "$@"; }

version=$(call GetVersionInfo)
case "$version" in *T-PTMUABC-1651.7??T-PTMINTV-*'Model : QA75QN85BAJXXZ'*) ;; *) echo '型号或固件不匹配，停止'; exit 1 ;; esac
flag=$(call GetItem 140202)
case "$flag" in *"'0', 'Preventing Import'"*) ;; *) echo 'Preventing Import 不为 0，停止'; exit 1 ;; esac
current=$(call GetItem 401)
case "$current" in *"'CHI_DTV', 'Local Set'"*|*"'AD_AU2', 'Local Set'"*) ;; *) echo '当前 Local Set 非预期，停止'; exit 1 ;; esac
echo "当前: $current"
pid=$(systemctl show "$unit" -p MainPID --value)
[ "$pid" -gt 0 ] && [ "$(readlink "/proc/$pid/exe")" = /usr/bin/TIFSDaemon ] || { echo '工厂服务异常'; exit 1; }
rw() { dd if="/proc/$pid/mem" bs=1 skip="$1" count=4 2>/dev/null | od -An -t u4 | tr -d ' \n'; }
ctrl=$(rw 723592)
case "$ctrl" in ''|*[!0-9]*) echo '无法读取映射'; exit 1 ;; esac
count=$(rw $((ctrl+164)))
case "$count" in ''|*[!0-9]*) echo '无法读取计数'; exit 1 ;; esac
[ "$count" -lt 512 ] || { echo '映射计数异常'; exit 1; }
candidate=$(call GetLocalSetStr 1)
case "$candidate" in *"'AD_AU2'"*) ;; *) echo '美国区选项不可用，停止'; exit 1 ;; esac
after=$(rw $((ctrl+164)))
[ "$after" = "$((count+1))" ] || { echo '映射被其他操作改变，停止'; exit 1; }
node=$(rw $((ctrl+152)))
tries=0
value=
while [ "$node" -gt 0 ] 2>/dev/null && [ "$tries" -lt 32 ]; do
    key=$(rw $((node+16)))
    case "$key" in ''|*[!0-9]*) break ;; esac
    if [ "$key" = "$count" ]; then value=$(rw $((node+20))); break; fi
    if [ "$key" -gt "$count" ]; then node=$(rw $((node+8))); else node=$(rw $((node+12))); fi
    tries=$((tries+1))
done
[ "$value" = 1 ] && [ "$(systemctl show "$unit" -p MainPID --value)" = "$pid" ] || { echo '美国区映射或服务进程发生变化，停止'; exit 1; }
echo "已验证美国区映射：菜单序号 $count → 存储值 1"
if [ "$mode" = --check ]; then echo '检查完成，没有写入地区'; exit 0; fi
case "$current" in *"'AD_AU2', 'Local Set'"*) echo '已经是 AD_AU2，无需再次写入'; exit 0 ;; esac
result=$(call SetParameter 194 "$count")
echo "设置接口返回: $result"
case "$result" in *"((1,),)"*) ;; *) echo '设置未报告成功，停止'; exit 1 ;; esac
updated=$(call GetItem 401)
echo "设置后: $updated"
case "$updated" in *"'AD_AU2', 'Local Set'"*) ;; *) echo '回读不是 AD_AU2，停止'; exit 1 ;; esac
echo '工程地区已设置为 AD_AU2；Smart Hub 国家仍需另行验证。'
