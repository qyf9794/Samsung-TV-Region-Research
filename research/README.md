# 历史实验代码

这些实验针对三星 **QA75QN85BAJXXZ** 国行电视进行；工厂服务内存地址等细节对应研究时的 `T-PTMUABC-1651.7` 固件，不能仅凭同属 QN85B 系列就套用。

这里保留研究过程中编写的辅助脚本，具体结果及失败记录见[研究记录](../docs/研究记录.md)。

- `disasm.py`：使用 pyelftools 与 Capstone 检查指定的 ARM ELF 动态符号。
- `emulate_filter.py`、`emulate_interposer.py`：使用 Unicorn 与 pyelftools 对特定固件的 ARM 指令离线模拟；需要自行合法取得对应固件程序，仓库不提供。
- `localset-runtime-probe.c`、`preload-*`、`runtime-filter-test.sh`、`loader-baseline-test.sh`：加载/拦截实验。工厂服务预加载实验未成功，且曾导致服务无法就绪；不是改区步骤。
- `memory-filter-test.sh`：针对特定固件暂停工厂服务并更改进程内存的实验。虽然包含恢复尝试，它仍可能中断服务，地址和指令只对应研究版本；不是通用工具。

这些文件是实验记录，不等同于可恢复、可移植或经过完整测试的方案。不要将其中的地址或写入方式用于其他版本。
