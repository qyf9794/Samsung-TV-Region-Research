# Smart Hub 国家：独立调查与验证

## 实际观察

工厂 Local Set 改为 `AD_AU2` 并冷启动后，电视仍报告 `db/comss/countrycode=CN`，说明工厂地区与 Smart Hub 国家可以不同。重置 Smart Hub 后发现电视固件为 `T-PTMUABC-1720.7`，无法确定升级时间或原因；本仓库 1651.7 专用工厂脚本不适用于该固件。

随后在 1720.7 电视上使用电视自身的 `comss_set_gpm_countrycode` 接口传入 `US`，接口返回 `()`。两次读取 `db/comss/countrycode` 均为 `US`，电视网络接口也报告 `countryCode=US`；商店域名为 `.com`。**没有在当时验证再次重启后的持久性，也没有通过电视界面确认美国应用商店或美国应用可用。**

设置前 `WASConfigTable` 的 `SYNC_STATE` 为 2，调用后为 1；其含义未经确认。该固件的应用服务包含国家变化后触发 Smart Hub 重置的分支，可能影响账号、协议和应用。国家列表中包含 `US` 不代表当前应用商店已经切换。

## 只读核对

连接和 root 工具参数见[工程区操作记录](工程改美区攻略.md)。临时 root 后可只读核对：

```sh
vconftool get db/comss/countrycode
vconftool get rtc/db/comss/gpmurl/store
gdbus introspect --system --dest comss.server --object-path /comss/server
gdbus call --system --dest comss.server --object-path /comss/server --method comss.server.interface.comss_get_countrylist
```

`comss.server`、`/comss/server`、`comss.server.interface` 及方法签名来自 1720.7 的程序静态检查。上述完整命令是根据记录和接口信息重建的示例，**没有在公开整理过程中再次运行验证**；其他固件的服务、参数和可用权限可能不同。

## 当时的国家设置接口

静态检查显示 `comss_set_gpm_countrycode` 接收一个字符串参数，依据该接口重建的调用形式如下：

```sh
gdbus call --system --dest comss.server --object-path /comss/server --method comss.server.interface.comss_set_gpm_countrycode US
```

这是**修改 Smart Hub 国家**的写操作，不是只读检查；可能触发应用重新初始化。研究记录确认当时调用该方法并读回 US，但没有保留完整终端命令，上面的命令行未重新实机验证。执行前应先核对接口、备份和数据影响；不应把它当成已经验证可重复使用的自动化步骤。

若要核对美国商店，需在设置后、冷启动后以及必要的协议/账号配置完成后分别检查国家值和实际商店界面。服务器域名、国家代码或 D-Bus 成功返回都不能替代可用性验证。
