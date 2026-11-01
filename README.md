# 三星国行电视地区切换研究

对一台三星 **QA75QN85BAJXXZ** 国行电视的工厂地区与 Smart Hub 国家设置进行的实机研究。项目包括研究过程、操作记录、备份工具和离线分析辅助程序。它不是三星官方教程，也不是适用于所有三星电视的一键改区工具。

## 已观察到的结果

| 阶段 | 本机情况 | 验证边界 |
| --- | --- | --- |
| 工厂地区 | 固件 `T-PTMUABC-1651.7` 上将 Local Set 从 `CHI_DTV` 改为 `AD_AU2`，并在冷启动后读回。 | 过程涉及多项工厂数据；未在第二台电视上验证自动写入分支，亦未验证恢复方案。 |
| Smart Hub | 后来发现固件为 `T-PTMUABC-1720.7`；调用电视自身接口后，国家代码和网络设备接口读回 `US`。 | 当时没有验证再次重启后的保持情况，也没有通过电视界面确认美国商店或应用可用。 |

**工厂地区与 Smart Hub 国家是两项设置。** 仅看到 `AD_AU2`、`US` 或商店域名变化，不足以证明美国应用商店、账号和流媒体服务均可使用。

## 重要边界

- 工厂参数修改可能造成设备无法正常启动、配置丢失或需要维修。EEPROM 读取副本不是整机备份，**恢复路径尚未验证**；建议具备断电后独立编程器及维修条件。
- 区域、菜单项、内存地址、控制值和软件接口受**型号、主板、固件版本**影响。`tools/` 中的区域选择脚本只针对 QA75QN85BAJXXZ / `T-PTMUABC-1651.7`，并拒绝不匹配版本；不要把其地址和参数直接用于 1720.7 或其他机型。
- `research/` 包含曾使工厂服务无法就绪的临时加载实验，以及会暂停进程并写入进程内存的实验脚本；这些是历史研究材料，不是日常操作步骤。临时恢复机制也不能保证异常中断后一定恢复。
- Smart Hub 重置会退出账号并可能清除应用数据；参见 [Samsung Smart Hub 重置说明](https://www.samsung.com/au/support/tv-audio-video/reset-smart-hub-samsung-tv/)。

## 硬件与软件条件

本次工厂区研究使用国行三星 QA75QN85BAJXXZ、初始固件 `T-PTMUABC-1651.7`，后续 Smart Hub 调查使用 `T-PTMUABC-1720.7`。开发电脑与电视处于可互通的局域网；电视开启开发者模式，并设置开发电脑的局域网 IP。

需要 [Tizen Studio 的 SDB](https://developer.samsung.com/smarttv/develop/getting-started/using-sdk/tv-device.html)、与电脑平台相符的 [samsung-tv-root](https://github.com/chris-ritsen/samsung-tv-root)（本次使用 v0.0.12 临时 root）、Python 3，以及编译 EEPROM 只读程序所需的 .NET SDK。电视需能运行 .NET Core 3.1 程序；具体 root 路线、架构、权限和固件兼容性须自行确认。

EEPROM 工具基于本机 I²C 总线 3、地址 `0x50` 和 `s24c512c` 驱动，只在匹配型号、固件和驱动时运行。它进行两次随机读取并比较，随机读取会先发送两字节地址指针；不发送 EEPROM 数据写入事务。它只覆盖 64 KiB，不是完整设备恢复镜像。

## 文档与工具

- [工程区切换操作记录](docs/工程改美区攻略.md)：1651.7 的连接、备份、检查、修改和重启后核对。
- [Smart Hub 国家调查与验证](docs/SMART-HUB.md)：1720.7 的独立国家设置、已确认结果与未验证内容。
- [完整地区研究记录](docs/研究记录.md)：按时间记录调查、测试、失败方案及真实结果；设备专属备份摘要已隐藏。
- [`tools/`](tools/)：EEPROM 只读备份程序的源码，以及检查和选择美国工厂区的脚本。
- [`research/`](research/)：反汇编、模拟和实验脚本，按研究用途保留，不包含从电视提取的原厂二进制。

备份工具需要先编译：

```sh
cd tools
dotnet build EepromRead.csproj -c Release -o build
cp build/EepromRead.dll build/EepromRead.runtimeconfig.json .
```

随后按[操作记录](docs/工程改美区攻略.md)提供电视 IP、SDB 和 root 工具路径。`select_us.py --check` 会检查条件，`--apply` 会修改工厂地区；其中针对未改区设备的自动写入分支只在模拟数据上检查过，未在第二台电视实测。

## 私有数据与第三方文件

仓库不包含任何设备 EEPROM 或工厂克隆备份、电视导出的固件程序和数据库、设备身份、证书或密钥，也不重新分发 SDB 或 samsung-tv-root。备份可能含有设备专属数据，不应公开；`.gitignore` 为常见备份和构建产物提供保护，但提交前仍需自行检查。

该项目没有声明三星或 Samsung 的支持或认可。使用第三方工具前，请阅读其各自的许可和说明。
