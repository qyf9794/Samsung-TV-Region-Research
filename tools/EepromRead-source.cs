using System;
using System.Runtime.InteropServices;
using System.Security.Cryptography;

internal static class Program
{
    [StructLayout(LayoutKind.Sequential)]
    private struct ReadRequest
    {
        public uint Address;
        public uint Length;
        public uint Reserved;
        public IntPtr Buffer;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct I2cMessage
    {
        public ushort Address;
        public ushort Flags;
        public ushort Length;
        public IntPtr Buffer;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct I2cTransaction
    {
        public IntPtr Messages;
        public uint Count;
    }

    [DllImport("libc", SetLastError = true)]
    private static extern int open(string path, int flags);
    [DllImport("libc", SetLastError = true)]
    private static extern int ioctl(int fd, uint request, ref ReadRequest argument);
    [DllImport("libc", SetLastError = true, EntryPoint = "ioctl")]
    private static extern int ioctlI2c(int fd, uint request, ref I2cTransaction argument);
    [DllImport("libc", SetLastError = true)]
    private static extern int close(int fd);

    private const uint EepromRead = 0x80044906;
    private const uint FactoryStart = 0x3e00;
    private const int FactoryLength = 0x4000;
    private const int ChunkLength = 256;

    // Same two-message random-read transaction used by the TV's EEPROM driver:
    // write only the two-byte address pointer, then read data. No data-write message.
    private static byte[] ReadI2c(int fd, byte sentinel)
    {
        const int page = 64;
        byte[] output = new byte[0x10000];
        IntPtr address = Marshal.AllocHGlobal(2);
        IntPtr buffer = Marshal.AllocHGlobal(page);
        IntPtr messages = Marshal.AllocHGlobal(24);
        try
        {
            for (int offset = 0; offset < output.Length; offset += page)
            {
                Marshal.WriteByte(address, 0, (byte)(offset >> 8));
                Marshal.WriteByte(address, 1, (byte)offset);
                for (int i = 0; i < page; i++) Marshal.WriteByte(buffer, i, sentinel);
                var pointerMessage = new I2cMessage { Address = 0x50, Flags = 0, Length = 2, Buffer = address };
                var readMessage = new I2cMessage { Address = 0x50, Flags = 1, Length = page, Buffer = buffer };
                Marshal.StructureToPtr(pointerMessage, messages, false);
                Marshal.StructureToPtr(readMessage, IntPtr.Add(messages, 12), false);
                var transaction = new I2cTransaction { Messages = messages, Count = 2 };
                int result = ioctlI2c(fd, 0x0707, ref transaction); // I2C_RDWR
                if (result != 2) throw new InvalidOperationException("I2C read failed at " + offset + ": result " + result + ", errno " + Marshal.GetLastWin32Error());
                Marshal.Copy(buffer, output, offset, page);
            }
            return output;
        }
        finally
        {
            Marshal.FreeHGlobal(messages);
            Marshal.FreeHGlobal(buffer);
            Marshal.FreeHGlobal(address);
        }
    }

    private static byte[] ReadRange(int fd, uint start, int length, byte sentinel)
    {
        byte[] output = new byte[length];
        IntPtr buffer = Marshal.AllocHGlobal(ChunkLength);
        try
        {
            for (int offset = 0; offset < length; offset += ChunkLength)
            {
                for (int i = 0; i < ChunkLength; i++) Marshal.WriteByte(buffer, i, sentinel);
                var request = new ReadRequest {
                    Address = start + (uint)offset,
                    Length = ChunkLength,
                    Reserved = 0,
                    Buffer = buffer
                };
                int result = ioctl(fd, EepromRead, ref request);
                if (result < 0)
                    throw new InvalidOperationException("read ioctl failed at " + offset + ": errno " + Marshal.GetLastWin32Error());
                Marshal.Copy(buffer, output, offset, ChunkLength);
            }
            return output;
        }
        finally { Marshal.FreeHGlobal(buffer); }
    }

    private static int Main(string[] args)
    {
        if (args.Length == 1 && args[0] == "--hello")
        {
            Console.WriteLine("managed-runtime-ok ptr=" + IntPtr.Size);
            return 0;
        }
        if (args.Length != 1 || (args[0] != "--read-factory" && args[0] != "--read-all" && args[0] != "--read-i2c")) return 2;
        if (IntPtr.Size != 4 || Marshal.SizeOf<ReadRequest>() != 16)
            throw new InvalidOperationException("unexpected target ABI");
        bool directI2c = args[0] == "--read-i2c";
        if (directI2c && (Marshal.SizeOf<I2cMessage>() != 12 || Marshal.SizeOf<I2cTransaction>() != 8))
            throw new InvalidOperationException("unexpected I2C ABI");
        int fd = open(directI2c ? "/dev/i2c-3" : "/dev/eeprom", directI2c ? 2 : 0);
        if (fd < 0) throw new InvalidOperationException("open failed: errno " + Marshal.GetLastWin32Error());
        try
        {
            uint start = args[0] == "--read-factory" ? FactoryStart : 0;
            int length = args[0] == "--read-factory" ? FactoryLength : 0x10000;
            byte[] first = directI2c ? ReadI2c(fd, 0xa5) : ReadRange(fd, start, length, 0xa5);
            byte[] second = directI2c ? ReadI2c(fd, 0x5a) : ReadRange(fd, start, length, 0x5a);
            for (int i = 0; i < first.Length; i++)
                if (first[i] != second[i]) throw new InvalidOperationException("two EEPROM reads differ at " + i);
            using (var sha = SHA256.Create())
                Console.WriteLine("SHA256=" + BitConverter.ToString(sha.ComputeHash(first)).Replace("-", "").ToLowerInvariant());
            Console.WriteLine("FACTORY_BASE64=" + Convert.ToBase64String(first));
            return 0;
        }
        finally { close(fd); }
    }
}
