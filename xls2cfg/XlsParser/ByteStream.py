import queue
import struct
import json

class ByteStream:
    SEEK_BEGIN = 0
    SEEK_CUR = 1
    SEEK_END = 2

    pool = queue.Queue()

    @staticmethod
    def GetFromPool():
        if (ByteStream.pool.qsize() == 0):
            stream = ByteStream()
        else:
            stream = ByteStream.pool.get()
        return stream

    @staticmethod
    def PutToPool(stream):
        stream.Clear()
        ByteStream.pool.put(stream)

    def __init__(self):
        self.buffer = bytearray(256)
        self.pos = 0
        self.size = 0

    @property
    def Capacity(self):
        return len(self.buffer)

    def Expand(self,size):
        if (self.Capacity - self.pos < size):
            capacity = self.Capacity
            while (capacity - self.pos < size):
                capacity = capacity * 2
            newBuffer = bytearray(capacity)
            newBuffer[:len(self.buffer)] = self.buffer
            self.buffer = newBuffer

    def WriteByte(self, b):
        self.Expand(1)
        self.buffer[self.pos] = b
        self.pos += 1
        self.size += 1

    def WriteBool(self, b):
        self.WriteByte(1 if b else 0)

    def WriteUInt8(self, value):
        self.WriteByte(value)

    def WriteUInt16(self, value):
        for i in range(2):
            self.WriteByte((value >> i * 8) & 0xFF)

    def WriteUInt32(self, value):
        for i in range(4):
            self.WriteByte((value >> i * 8) & 0xFF)

    def WriteUInt64(self, value):
        for i in range(8):
            self.WriteByte((value >> i * 8) & 0xFF)

    def WriteInt8(self, b):
        self.WriteUInt8(b)

    def WriteInt16(self, value):
        self.WriteUInt16(value)

    def WriteInt32(self, value):
        self.WriteUInt32(value)

    def WriteInt64(self, value):
        self.WriteUInt64(value)

    def WriteBigInt(self,value):
        self.WriteString(value)

    def WriteFloat(self, value, power=5):
        num = int(value * (10 ** power))
        self.WriteInt64(num)

    def WriteDouble(self, value, power=8):
        num = int(value * (10 ** power))
        self.WriteInt64(num)

    def WriteString(self, str):
        data = str.encode('utf-8')
        self.WriteUInt16(len(data))
        self.Write(data, 0, len(data))

    def WriteJson(self,value):
        data = json.dumps(value)
        self.WriteString(data)

    def Write(self, bytes, startPos, length):
        self.Expand(length)
        # for i in range(length):
        #     self.buffer[self.pos + i] = bytes[startPos+i]
        self.buffer[self.pos:] = bytes[startPos:startPos+length]
        self.pos += length
        self.size += length

    def ReadByte(self):
        value = self.buffer[self.pos]
        self.pos = self.pos + 1
        return value

    def ReadBool(self):
        return bool(self.ReadByte())

    def ReadUInt8(self):
        return self.ReadByte()

    def ReadUInt16(self):
        num = 0
        for i in range(2):
            b = self.ReadByte()
            num += (b << i * 8)
        return num
        # return struct.unpack('<H', num.to_bytes(2, 'little'))[0]

    def ReadUInt32(self):
        num = 0
        for i in range(4):
            b = self.ReadByte()
            num += (b << i * 8)
        return num
        # return struct.unpack('<I', num.to_bytes(4, 'little'))[0]

    def ReadUInt64(self):
        num = 0
        for i in range(8):
            b = self.ReadByte()
            num += (b << i * 8)
        return num
        # return struct.unpack('<Q', num.to_bytes(8, 'little'))[0]

    def ReadInt8(self):
        value = self.ReadUInt8()
        if value >= 128:
            return value - 256
        else:
            return value

    def ReadInt16(self):
        return struct.unpack('<h', self.ReadBytes(2))[0]

    def ReadInt32(self):
        return struct.unpack('<i', self.ReadBytes(4))[0]

    def ReadInt64(self):
        return struct.unpack('<q', self.ReadBytes(8))[0]

    def ReadBigInt(self):
        return self.ReadString()

    def ReadFloat(self, power=5):
        num = self.ReadInt64()
        return float(num) / (10 ** power)

    def ReadDouble(self, power=8):
        num = self.ReadInt64()
        return float(num) / (10 ** power)

    def ReadString(self):
        length = self.ReadUInt16()
        bytes = self.ReadBytes(length)
        return bytes.decode('utf-8')

    def ReadJson(self):
        jsonStr = self.ReadString()
        return json.loads(jsonStr)

    def Read(self, result,startPos,length):
        canReadBytes = self.Capacity - self.pos
        if canReadBytes < length:
            length = canReadBytes
        result[startPos:] = self.buffer[self.pos:self.pos + length]
        self.pos += length
        return length

    def ReadBytes(self,length):
        bytes = bytearray(length)
        self.Read(bytes,0,length)
        return bytes


    def Seek(self, offset, whence):
        if whence == ByteStream.SEEK_BEGIN:
            self.pos = 0 + offset
        elif whence == ByteStream.SEEK_CUR:
            self.pos = self.pos + offset
        elif whence == ByteStream.SEEK_END:
            self.pos = self.size + offset
        else:
            raise Exception(f"[ByteStream.Seek] invalid whence: {whence}")
        self.Expand(0)
        return self.pos

    def Clear(self):
        self.pos = 0
        self.size = 0

    def ReadFile(self, filename):
        with open(filename, 'rb') as file:
            buffer = file.read()
            self.buffer = bytearray(buffer)

    def ReadBuffer(self,buffer):
        self.Expand(len(buffer))
        self.buffer[:] = buffer

    def WriteFile(self, filename):
        with open(filename, 'wb') as file:
            file.write(self.buffer[:self.pos])

    def WriteValue(self,fieldType,value):
        fieldTypename = fieldType.typename
        if fieldTypename == "bool":
            self.WriteBool(value)
        elif fieldTypename == "int8":
            self.WriteInt8(value)
        elif fieldTypename == "int16":
            self.WriteInt16(value)
        elif fieldTypename == "int32":
            self.WriteInt32(value)
        elif fieldTypename == "int64":
            self.WriteInt64(value)
        elif fieldTypename == "uint8":
            self.WriteUInt8(value)
        elif fieldTypename == "uint16":
            self.WriteUInt16(value)
        elif fieldTypename == "uint32":
            self.WriteUInt32(value)
        elif fieldTypename == "uint64":
            self.WriteUInt64(value)
        elif fieldTypename == "bigint":
            self.WriteBigInt(value)
        elif fieldTypename == "float":
            self.WriteFloat(value)
        elif fieldTypename == "double":
            self.WriteDouble(value)
        elif fieldTypename == "string" or fieldTypename == "i18nstring":
            self.WriteString(value)
        elif fieldTypename == "bit32":
            self.WriteUInt32(value)
        elif fieldTypename == "bit64":
            self.WriteUInt64(value)
        elif fieldTypename == "list":
            lst = value
            self.WriteUInt8(len(lst))
            for value in lst:
                self.WriteValue(fieldType.valueType,value)
        elif fieldTypename == "map":
            map = value
            self.WriteUInt8(len(map))
            for key,value in map.items():
                self.WriteValue(fieldType.keyType,key)
                self.WriteValue(fieldType.valueType,value)
        elif fieldTypename == "json":
            self.WriteJson(value)
        elif fieldType.isClass():
            for clsField in fieldType.fields:
                self.WriteValue(clsField.type,value[clsField.name])
        else:
            raise Exception("unkown type: " + fieldTypename)

    def ReadValue(self,fieldType):
        fieldTypename = fieldType.typename
        if fieldTypename == "bool":
            value = self.ReadBool()
        elif fieldTypename == "int8":
            value = self.ReadInt8()
        elif fieldTypename == "int16":
            value = self.ReadInt16()
        elif fieldTypename == "int32":
            value = self.ReadInt32()
        elif fieldTypename == "int64":
            value = self.ReadInt64()
        elif fieldTypename == "uint8":
            value = self.ReadUInt8()
        elif fieldTypename == "uint16":
            value = self.ReadUInt16()
        elif fieldTypename == "uint32":
            value = self.ReadUInt32()
        elif fieldTypename == "uint64":
            value = self.ReadUInt64()
        elif fieldTypename == "bigint":
            value = self.ReadBigInt()
        elif fieldTypename == "float":
            value = self.ReadFloat()
        elif fieldTypename == "double":
            value = self.ReadDouble()
        elif fieldTypename == "string" or fieldTypename == "i18nstring":
            value = self.ReadString()
        elif fieldTypename == "bit32":
            value = self.ReadUInt32()
        elif fieldTypename == "bit64":
            value = self.ReadUInt64()
        elif fieldTypename == "list":
            lst = []
            length = self.ReadUInt8()
            for i in range(length):
                lst.append(self.ReadValue(fieldType.valueType))
            value = lst
        elif fieldTypename == "map":
            map = {}
            length = self.ReadUInt8()
            for i in range(length):
                key = self.ReadValue(fieldType.keyType)
                value = self.ReadValue(fieldType.valueType)
                map[key] = value
            value = map
        elif fieldTypename == "json":
            value = self.ReadJson()
        elif fieldType.isClass():
            instance = {}
            for clsField in fieldType.fields:
                instance[clsField.name] = self.ReadValue(clsField.type)
            value = instance
        else:
            raise Exception("unkown type: " + fieldTypename)
        return value