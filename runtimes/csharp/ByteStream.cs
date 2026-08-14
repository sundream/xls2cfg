using System;
using System.IO;
using System.Collections.Generic;
using System.Text;
using System.Reflection;
using SimpleJSON;

namespace Cfg {
    // 小端字节流
    public class ByteStream {

        private static Queue<ByteStream> pool = new Queue<ByteStream>();
        public static ByteStream GetFromPool () {
            ByteStream stream = null;
            lock(pool) {
                if (pool.Count == 0) {
                    stream = new ByteStream();
                } else {
                    stream = pool.Dequeue();
                }
            }
            return stream;
        }

        public static void PutToPool(ByteStream stream) {
            lock(pool) {
                stream.Clear();
                pool.Enqueue(stream);
            }
        }

        public const int SEEK_BEGIN = 0;
        public const int SEEK_CUR = 1;
        public const int SEEK_END = 2;

        private byte[] buffer;
        private int pos;
        private int size;

        public ByteStream () {
            buffer = new byte[256];
            pos = 0;
        }

        public byte[] Buffer {
            get {return buffer;}
            set {buffer = value;}
        }
        public int Position {
            get {return pos;}
        }

        public int Size {
            get {return size;}
        }
        public int Capacity {
            get {return buffer.Length;}
        }

        public void Expand (int size) {
            if (Capacity - pos < size) {
                int oldCapacity = Capacity;
                int capcity = Capacity;
                while (capcity - pos < size) {
                    capcity = capcity * 2;
                }
                byte [] newBuffer = new byte[capcity];
                Array.Copy(buffer,0,newBuffer,0,oldCapacity);
                buffer = newBuffer;
            }
        }

        public void WriteBool(bool b) {
            WriteByte((byte)(b ? 1 : 0));
        }

        public void WriteByte (byte b) {
            Expand(sizeof(byte));
            buffer[pos++] = b;
            size++;
        }

        public void WriteUInt8(byte value) {
            WriteByte(value);
        }

        public void WriteUInt16(UInt16 value) {
            int len = sizeof(UInt16);
            for (int i = 0; i < len; i++) {
                WriteByte((byte)((value >> i*8) & 0xff));
            }
        }

        public void WriteUInt32(UInt32 value) {
            int len = sizeof(UInt32);
            for (int i = 0; i < len; i++) {
                WriteByte((byte)((value >> i*8) & 0xff));
            }
        }

        public void WriteUInt64(UInt64 value) {
            int len = sizeof(UInt64);
            for (int i = 0; i < len; i++) {
                WriteByte((byte)((value >> i*8) & 0xff));
            }
        }

        public void WriteInt8(sbyte b) {
            WriteUInt8((byte)b);
        }

        public void WriteInt16(Int16 value) {
            WriteUInt16((UInt16)value);
        }

        public void WriteInt32(Int32 value) {
            WriteUInt32((UInt32)value);
        }

        public void WriteInt64(Int64 value) {
            WriteUInt64((UInt64)value);
        }

        public void WriteBigInt(string value) {
            WriteString(value);
        }

        public void WriteDecimal(decimal value) {
            WriteBigInt(value.ToString());
        }

        public void WriteFloat(float value) {
            byte[] bytes = BitConverter.GetBytes(value);
            if (!BitConverter.IsLittleEndian) {
                Array.Reverse(bytes);
            }
            Write(bytes, 0, bytes.Length);
        }

        public void WriteDouble(double value) {
            byte[] bytes = BitConverter.GetBytes(value);
            if (!BitConverter.IsLittleEndian) {
                Array.Reverse(bytes);
            }
            Write(bytes, 0, bytes.Length);
        }

        public void WriteString(string str) {
            byte[] bytes = Encoding.UTF8.GetBytes(str);
            WriteUInt16((UInt16)bytes.Length);
            Write(bytes,0,bytes.Length);
        }

        public void WriteJson(JSONNode value) {
            string data = value.ToString();
            WriteString(data);
        }

        public void Write(byte[] bytes,int startPos,int length) {
            Expand(length);
            Array.Copy(bytes,startPos,buffer,pos,length);
            pos += length;
            size += length;
        }

        public bool ReadBool() {
            return ReadByte() != 0;
        }

        public byte ReadByte () {
            return buffer[pos++];
        }

        public byte ReadUInt8() {
            return ReadByte();
        }

        public UInt16 ReadUInt16() {
            /*
            UInt16 number = 0;
            byte b;
            for (int i = 0; i < 2; i++) {
                b = buffer[pos++];
                number |= (UInt16)(b << i * 8);
            }
            return number;
            */
            int readPos = pos;
            pos += 2;
            return BitConverter.ToUInt16(buffer, readPos);
        }

        public UInt32 ReadUInt32() {
            /*
            UInt32 number = 0;
            byte b;
            for (int i = 0; i < 4; i++) {
                b = buffer[pos++];
                number |= (UInt32)b << i * 8;
            }
            return number;
            */
            int readPos = pos;
            pos += 4;
            return BitConverter.ToUInt32(buffer, readPos);
        }

        public UInt64 ReadUInt64() {
            /*
            UInt64 number = 0;
            byte b;
            for (int i = 0; i < 8; i++) {
                b = buffer[pos++];
                number |= (UInt64)b << i * 8;
            }
            return number;
            */
            int readPos = pos;
            pos += 8;
            return BitConverter.ToUInt64(buffer, readPos);
        }

        public sbyte ReadInt8() {
            return (sbyte)ReadUInt8();
        }

        public Int16 ReadInt16() {
            return (Int16)ReadUInt16();
        }

        public Int32 ReadInt32() {
            return (Int32)ReadUInt32();
        }

        public Int64 ReadInt64() {
            return (Int64)ReadUInt64();
        }

        public string ReadBigInt() {
            return ReadString();
        }

        public decimal ReadDecimal() {
            return Convert.ToDecimal(ReadBigInt());
        }

        public float ReadFloat() {
            int readPos = pos;
            pos += 4;
            if (!BitConverter.IsLittleEndian) {
                byte[] bytes = new byte[4];
                Array.Copy(buffer, readPos, bytes, 0, 4);
                Array.Reverse(bytes);
                return BitConverter.ToSingle(bytes, 0);
            }
            return BitConverter.ToSingle(buffer, readPos);
        }

        public double ReadDouble() {
            int readPos = pos;
            pos += 8;
            if (!BitConverter.IsLittleEndian) {
                byte[] bytes = new byte[8];
                Array.Copy(buffer, readPos, bytes, 0, 8);
                Array.Reverse(bytes);
                return BitConverter.ToDouble(bytes, 0);
            }
            return BitConverter.ToDouble(buffer, readPos);
        }

        public string ReadString() {
            int length = ReadUInt16();
            int readPos = pos;
            pos += length;
            return Encoding.UTF8.GetString(buffer,readPos,length);
        }

        public JSONNode ReadJson() {
            string data = ReadString();
            return JSON.Parse(data);
        }

        public int Read (byte[] bytes,int startPos,int length) {
            int canReadBytes = Capacity - pos;
            if (canReadBytes < length) {
                length = canReadBytes;
            }
            if (canReadBytes > 0 ) {
                Array.Copy(buffer,pos,bytes,startPos,length);
            }
            pos += length;
            return length;
        }

        public int Seek (int offset,int whence) {
            switch (whence) {
                case SEEK_BEGIN:
                    pos = 0 + offset;
                    break;
                case SEEK_CUR:
                    pos = pos + offset;
                    break;
                case SEEK_END:
                    pos = size + offset;
                    break;
                default:
                    throw new Exception(string.Format("[ByteStream.Seek] invalid whence:{0}",whence));
            }
            Expand(0);
            return pos;
        }

        public void Clear() {
            pos = 0;
            size = 0;
        }

        public byte[] ToBytes() {
            byte[] data = new byte[size];
            Array.Copy(buffer, 0, data, 0, size);
            return data;
        }

        public void CopyBuffer(byte[] buffer,int index=0, int count=0) {
            if (count == 0) {
                count = buffer.Length;
            }
            Expand(count);
            Array.Copy(buffer,index,this.buffer,0,count);
        }

        public void ReadFile(string filename) {
            FileStream fs = new FileStream(filename,FileMode.Open,FileAccess.Read);
            int length = (int)fs.Length;
            Expand(length);
            fs.Read(buffer, 0, length);
            fs.Close();
        }

        public void WriteFile(string filename) {
            FileStream fs = new FileStream(filename,FileMode.OpenOrCreate,FileAccess.Write);
            int length = (int)Position;
            fs.Write(buffer,0,length);
            fs.Close();
        }

        public void WriteList<V>(List<V> list) {
            int length = list == null ? 0 : list.Count;
            if (length > 255) {
                throw new Exception("list length > 255");
            }
            WriteUInt8((byte)length);
            for (int i = 0; i < length; i++) {
                WriteValue<V>(list[i]);
            }
        }

        public void WriteDictionary<K,V>(Dictionary<K,V> dict) {
            int length = dict == null ? 0 : dict.Count;
            if (length > 255) {
                throw new Exception("map length > 255");
            }
            WriteUInt8((byte)length);
            if (dict == null) {
                return;
            }
            foreach (KeyValuePair<K,V> kv in dict) {
                WriteValue<K>(kv.Key);
                WriteValue<V>(kv.Value);
            }
        }

        public List<V> ReadList<V>() {
            int length = ReadUInt8();
            List<V> list = new List<V>(length);
            for (int i = 0; i < length; i++)
            {
                list.Add(ReadValue<V>());
            }
            return list;
        }

        public Dictionary<K,V> ReadDictionary<K,V>() {
            int length = ReadUInt8();
            Dictionary<K,V> dict = new Dictionary<K,V>(length);
            for (int i = 0; i < length; i++) {
                dict.Add(ReadValue<K>(),ReadValue<V>());
            }
            return dict;
        }

        public T ReadValue<T>()
        {
            Type type = typeof(T);
            return (T)ReadValue(type);
        }

        public object ReadValue(Type type)
        {
            object result = null;
            if (type.IsPrimitive) {
                if (type == typeof(Int32)) {
                    result = ReadInt32();
                } else if (type == typeof(Int64)) {
                    result = ReadInt64();
                } else if (type == typeof(bool)) {
                    result = ReadBool();
                } else if (type == typeof(byte)) {
                    result = ReadUInt8();
                } else if (type == typeof(UInt16)) {
                    result = ReadUInt16();
                } else if (type == typeof(UInt32)) {
                    result = ReadUInt32();
                } else if (type == typeof(UInt64)) {
                    result = ReadUInt64();
                } else if (type == typeof(sbyte)) {
                    result = ReadInt8();
                } else if (type == typeof(Int16)) {
                    result = ReadInt16();
                } else if (type == typeof(float)) {
                    result = ReadFloat();
                } else if (type == typeof(double)) {
                    result = ReadDouble();
                } else {
                    throw new Exception($"invalid type: {type}");
                }
            } else if (type == typeof(string)) {
                result = ReadString();
            }
            else if (type == typeof(JSONNode)) {
                result = ReadJson();
            } else if (type == typeof(decimal)) {
                result = ReadDecimal();
            } else {
                result = Activator.CreateInstance(type, true);
                if (type.IsGenericType)
                {
                    var genericType = type.GetGenericTypeDefinition();
                    if (genericType == typeof(List<>))
                    {
                        int length = ReadUInt8();
                        Type collectionType = type.GetInterface("ICollection`1");
                        Type valueType = collectionType.GetGenericArguments()[0];
                        var f = collectionType.GetMethod("Add");
                        object[] args = new object[1];
                        for (int i = 0; i < length; i++)
                        {
                            args[0] = ReadValue(valueType);
                            f.Invoke(result, args);
                        }
                    }
                    else if (genericType == typeof(Dictionary<,>))
                    {
                        int length = ReadUInt8();
                        Type collectionType = type.GetInterface("ICollection`1");
                        Type keyValuePairType = collectionType.GetGenericArguments()[0];
                        var f = collectionType.GetMethod("Add");
                        Type keyType = keyValuePairType.GetGenericArguments()[0];
                        Type valueType = keyValuePairType.GetGenericArguments()[1];
                        Type typeofKeyValuePair = typeof(KeyValuePair<,>);
                        Type kvType = typeofKeyValuePair.MakeGenericType(keyType, valueType);
                        object[] args = new object[1];
                        for (int i = 0; i < length; i++)
                        {
                            args[0] = Activator.CreateInstance(kvType, ReadValue(keyType), ReadValue(valueType));
                            f.Invoke(result, args);
                        }
                    }
                    else
                    {
                        throw new Exception($"invalid type: {type}");
                    }
                }
                else
                {
                    // class
                    foreach (FieldInfo field in type.GetFields())
                    {
                        field.SetValue(result, ReadValue(field.FieldType));
                    }
                }
            }
            return result;
        }

        public void WriteValue<T>(T value)
        {
            Type type = typeof(T);
            WriteValue(type,value);
        }

        public void WriteValue(Type type,object value)
        {
            if (type.IsPrimitive) {
                if (type == typeof(bool)) {
                    WriteBool((bool)value);
                } else if (type == typeof(byte)) {
                    WriteUInt8((byte)value);
                } else if (type == typeof(UInt16)) {
                    WriteUInt16((UInt16)value);
                } else if (type == typeof(UInt32)) {
                    WriteUInt32((UInt32)value);
                } else if (type == typeof(UInt64)) {
                    WriteUInt64((UInt64)value);
                } else if (type == typeof(sbyte)) {
                    WriteInt8((sbyte)value);
                } else if (type == typeof(Int16)) {
                    WriteInt16((Int16)value);
                } else if (type == typeof(Int32)) {
                    WriteInt32((Int32)value);
                } else if (type == typeof(Int64)) {
                    WriteInt64((Int64)value);
                } else if (type == typeof(float)) {
                    WriteFloat((float)value);
                } else if (type == typeof(double)) {
                    WriteDouble((double)value);
                } else {
                    throw new Exception($"invalid type: {type}");
                }
            } else if (type == typeof(string)) {
                WriteString((string)value);
            } else if (type == typeof(JSONNode)) {
                WriteJson((JSONNode)value);
            } else if (type == typeof(decimal)) {
                WriteDecimal((decimal)value);
            } else {
                if (type.IsGenericType)
                {
                    var genericType = type.GetGenericTypeDefinition();
                    if (genericType == typeof(List<>))
                    {
                        List<object> list = (List<object>)value;
                        int length = list.Count;
                        WriteUInt8((byte)length);
                        Type collectionType = type.GetInterface("ICollection`1");
                        Type valueType = collectionType.GetGenericArguments()[0];
                        for (int i = 0; i < length; i++)
                        {
                            WriteValue(valueType,list[i]);
                        }
                    }
                    else if (genericType == typeof(Dictionary<,>))
                    {
                        Dictionary<object,object> map = (Dictionary<object,object>)value;
                        int length = map.Count;
                        WriteUInt8((byte)length);
                        Type collectionType = type.GetInterface("ICollection`1");
                        Type keyValuePairType = collectionType.GetGenericArguments()[0];
                        Type keyType = keyValuePairType.GetGenericArguments()[0];
                        Type valueType = keyValuePairType.GetGenericArguments()[1];
                        foreach(KeyValuePair<object,object> kv in map)
                        {
                            WriteValue(keyType, kv.Key);
                            WriteValue(valueType, kv.Value);

                        }
                    }
                    else
                    {
                        throw new Exception($"invalid type: {type}");
                    }
                }
                else
                {
                    // class
                    foreach (FieldInfo field in type.GetFields())
                    {
                        WriteValue(field.FieldType, field.GetValue(value));

                    }
                }
            }
        }

    }
}
