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
            this.buffer = new byte[256];
            this.pos = 0;
        }

        public byte[] Buffer {
            get {return this.buffer;}
            set {this.buffer = value;}
        }
        public int Position {
            get {return this.pos;}
        }

        public int Size {
            get {return this.size;}
        }
        public int Capacity {
            get {return this.buffer.Length;}
        }

        public void Expand (int size) {
            if (this.Capacity - this.pos < size) {
                int oldCapacity = this.Capacity;
                int capcity = this.Capacity;
                while (capcity - this.pos < size) {
                    capcity = capcity * 2;
                }
                byte [] newBuffer = new byte[capcity];
                Array.Copy(this.buffer,0,newBuffer,0,oldCapacity);
                this.buffer = newBuffer;
            }
        }

        public void WriteBool(bool b) {
            this.WriteByte((byte)(b ? 1 : 0));
        }

        public void WriteByte (byte b) {
            this.Expand(sizeof(byte));
            this.buffer[this.pos++] = b;
            this.size++;
        }

        public void WriteUInt8(byte value) {
            this.WriteByte(value);
        }

        public void WriteUInt16(UInt16 value) {
            int len = sizeof(UInt16);
            for (int i = 0; i < len; i++) {
                this.WriteByte((byte)((value >> i*8) & 0xff));
            }
        }

        public void WriteUInt32(UInt32 value) {
            int len = sizeof(UInt32);
            for (int i = 0; i < len; i++) {
                this.WriteByte((byte)((value >> i*8) & 0xff));
            }
        }

        public void WriteUInt64(UInt64 value) {
            int len = sizeof(UInt64);
            for (int i = 0; i < len; i++) {
                this.WriteByte((byte)((value >> i*8) & 0xff));
            }
        }

        public void WriteInt8(sbyte b) {
            this.WriteUInt8((byte)b);
        }

        public void WriteInt16(Int16 value) {
            this.WriteUInt16((UInt16)value);
        }

        public void WriteInt32(Int32 value) {
            this.WriteUInt32((UInt32)value);
        }

        public void WriteInt64(Int64 value) {
            this.WriteUInt64((UInt64)value);
        }

        public void WriteBigInt(string value) {
            this.WriteString(value);
        }

        public void WriteDecimal(decimal value) {
            this.WriteBigInt(value.ToString());
        }

        public void WriteFloat(float value,int power=5) {
            Int64 number = (Int64)(value * Math.Pow(10,power));
            this.WriteInt64(number);
        }

        public void WriteDouble(double value,int power=8) {
            Int64 number = (Int64)(value * Math.Pow(10,power));
            this.WriteInt64(number);
        }

        public void WriteString(string str) {
            byte[] bytes = Encoding.UTF8.GetBytes(str);
            this.WriteUInt16((UInt16)bytes.Length);
            this.Write(bytes,0,bytes.Length);
        }

        public void WriteJson(JSONNode value) {
            string data = value.ToString();
            this.WriteString(data);
        }

        public void Write(byte[] bytes,int startPos,int length) {
            this.Expand(length);
            Array.Copy(bytes,startPos,this.buffer,this.pos,length);
            this.pos += length;
            this.size += length;
        }

        public bool ReadBool() {
            return this.ReadByte() != 0;
        }

        public byte ReadByte () {
            return this.buffer[this.pos++];
        }

        public byte ReadUInt8() {
            return this.ReadByte();
        }

        public UInt16 ReadUInt16() {
            /*
            UInt16 number = 0;
            byte b;
            for (int i = 0; i < 2; i++) {
                b = this.buffer[this.pos++];
                number |= (UInt16)(b << i * 8);
            }
            return number;
            */
            int readPos = this.pos;
            this.pos += 2;
            return BitConverter.ToUInt16(this.buffer, readPos);
        }

        public UInt32 ReadUInt32() {
            /*
            UInt32 number = 0;
            byte b;
            for (int i = 0; i < 4; i++) {
                b = this.buffer[this.pos++];
                number |= (UInt32)b << i * 8;
            }
            return number;
            */
            int readPos = this.pos;
            this.pos += 4;
            return BitConverter.ToUInt32(this.buffer, readPos);
        }

        public UInt64 ReadUInt64() {
            /*
            UInt64 number = 0;
            byte b;
            for (int i = 0; i < 8; i++) {
                b = this.buffer[this.pos++];
                number |= (UInt64)b << i * 8;
            }
            return number;
            */
            int readPos = this.pos;
            this.pos += 8;
            return BitConverter.ToUInt64(this.buffer, readPos);
        }

        public sbyte ReadInt8() {
            return (sbyte)this.ReadUInt8();
        }

        public Int16 ReadInt16() {
            return (Int16)this.ReadUInt16();
        }

        public Int32 ReadInt32() {
            return (Int32)this.ReadUInt32();
        }

        public Int64 ReadInt64() {
            return (Int64)this.ReadUInt64();
        }

        public string ReadBigInt() {
            return this.ReadString();
        }

        public decimal ReadDecimal() {
            return Convert.ToDecimal(this.ReadBigInt());
        }

        public float ReadFloat(int power=5) {
            Int64 number = this.ReadInt64();
            return (float)number / (float)Math.Pow(10,power);
        }

        public double ReadDouble(int power=8) {
            Int64 number = this.ReadInt64();
            return (double)number / (double)Math.Pow(10, power);
        }

        public string ReadString() {
            int length = this.ReadUInt16();
            int pos = this.pos;
            this.pos += length;
            return Encoding.UTF8.GetString(this.buffer,pos,length);
        }

        public JSONNode ReadJson() {
            string data = this.ReadString();
            return JSON.Parse(data);
        }

        public int Read (byte[] bytes,int startPos,int length) {
            int canReadBytes = this.Capacity - this.pos;
            if (canReadBytes < length) {
                length = canReadBytes;
            }
            if (canReadBytes > 0 ) {
                Array.Copy(this.buffer,this.pos,bytes,startPos,length);
            }
            this.pos += length;
            return length;
        }

        public int Seek (int offset,int whence) {
            switch (whence) {
                case ByteStream.SEEK_BEGIN:
                    this.pos = 0 + offset;
                    break;
                case ByteStream.SEEK_CUR:
                    this.pos = this.pos + offset;
                    break;
                case ByteStream.SEEK_END:
                    this.pos = this.size + offset;
                    break;
                default:
                    throw new Exception(string.Format("[ByteStream.Seek] invalid whence:{0}",whence));
            }
            this.Expand(0);
            return this.pos;
        }

        public void Clear() {
            this.pos = 0;
            this.size = 0;
        }

        public void CopyBuffer(byte[] buffer,int index=0, int count=0) {
            if (count == 0) {
                count = buffer.Length;
            }
            this.Expand(count);
            Array.Copy(buffer,index,this.buffer,0,count);
        }

        public void ReadFile(string filename) {
            FileStream fs = new FileStream(filename,FileMode.Open,FileAccess.Read);
            int length = (int)fs.Length;
            this.Expand(length);
            fs.Read(this.buffer, 0, length);
            fs.Close();
        }

        public void WriteFile(string filename) {
            FileStream fs = new FileStream(filename,FileMode.OpenOrCreate,FileAccess.Write);
            int length = (int)this.Position;
            fs.Write(this.buffer,0,length);
            fs.Close();
        }

        public List<V> ReadList<V>() {
            int length = this.ReadUInt8();
            List<V> list = new List<V>(length);
            for (int i = 0; i < length; i++)
            {
                list.Add(this.ReadValue<V>());
            }
            return list;
        }

        public Dictionary<K,V> ReadDictionary<K,V>() {
            int length = this.ReadUInt8();
            Dictionary<K,V> dict = new Dictionary<K,V>(length);
            for (int i = 0; i < length; i++) {
                dict.Add(this.ReadValue<K>(),this.ReadValue<V>());
            }
            return dict;
        }

        public T ReadValue<T>()
        {
            Type type = typeof(T);
            return (T)this.ReadValue(type);
        }

        public object ReadValue(Type type)
        {
            object result = null;
            if (type.IsPrimitive) {
                if (type == typeof(Int32)) {
                    result = this.ReadInt32();
                } else if (type == typeof(Int64)) {
                    result = this.ReadInt64();
                } else if (type == typeof(bool)) {
                    result = this.ReadBool();
                } else if (type == typeof(byte)) {
                    result = this.ReadUInt8();
                } else if (type == typeof(UInt16)) {
                    result = this.ReadUInt16();
                } else if (type == typeof(UInt32)) {
                    result = this.ReadUInt32();
                } else if (type == typeof(UInt64)) {
                    result = this.ReadUInt64();
                } else if (type == typeof(sbyte)) {
                    result = this.ReadInt8();
                } else if (type == typeof(Int16)) {
                    result = this.ReadInt16();
                } else if (type == typeof(float)) {
                    result = this.ReadFloat();
                } else if (type == typeof(double)) {
                    result = this.ReadDouble();
                } else {
                    throw new Exception($"invalid type: {type}");
                }
            } else if (type == typeof(string)) {
                result = this.ReadString();
            }
            else if (type == typeof(JSONNode)) {
                result = this.ReadJson();
            } else if (type == typeof(decimal)) {
                result = this.ReadDecimal();
            } else {
                result = Activator.CreateInstance(type, true);
                if (type.IsGenericType)
                {
                    var genericType = type.GetGenericTypeDefinition();
                    if (genericType == typeof(List<>))
                    {
                        int length = this.ReadUInt8();
                        Type collectionType = type.GetInterface("ICollection`1");
                        Type valueType = collectionType.GetGenericArguments()[0];
                        var f = collectionType.GetMethod("Add");
                        object[] args = new object[1];
                        for (int i = 0; i < length; i++)
                        {
                            args[0] = this.ReadValue(valueType);
                            f.Invoke(result, args);
                        }
                    }
                    else if (genericType == typeof(Dictionary<,>))
                    {
                        int length = this.ReadUInt8();
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
                            args[0] = Activator.CreateInstance(kvType, this.ReadValue(keyType), this.ReadValue(valueType));
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
                        field.SetValue(result, this.ReadValue(field.FieldType));
                    }
                }
            }
            return result;
        }

        public void WriteValue<T>(T value)
        {
            Type type = typeof(T);
            this.WriteValue(type,value);
        }

        public void WriteValue(Type type,object value)
        {
            if (type.IsPrimitive) {
                if (type == typeof(bool)) {
                    this.WriteBool((bool)value);
                } else if (type == typeof(byte)) {
                    this.WriteUInt8((byte)value);
                } else if (type == typeof(UInt16)) {
                    this.WriteUInt16((UInt16)value);
                } else if (type == typeof(UInt32)) {
                    this.WriteUInt32((UInt32)value);
                } else if (type == typeof(UInt64)) {
                    this.WriteUInt64((UInt64)value);
                } else if (type == typeof(sbyte)) {
                    this.WriteInt8((sbyte)value);
                } else if (type == typeof(Int16)) {
                    this.WriteInt16((Int16)value);
                } else if (type == typeof(Int32)) {
                    this.WriteInt32((Int32)value);
                } else if (type == typeof(Int64)) {
                    this.WriteInt64((Int64)value);
                } else if (type == typeof(float)) {
                    this.WriteFloat((float)value);
                } else if (type == typeof(double)) {
                    this.WriteDouble((double)value);
                } else {
                    throw new Exception($"invalid type: {type}");
                }
            } else if (type == typeof(string)) {
                this.WriteString((string)value);
            } else if (type == typeof(JSONNode)) {
                this.WriteJson((JSONNode)value);
            } else if (type == typeof(decimal)) {
                this.WriteDecimal((decimal)value);
            } else {
                if (type.IsGenericType)
                {
                    var genericType = type.GetGenericTypeDefinition();
                    if (genericType == typeof(List<>))
                    {
                        List<object> list = (List<object>)value;
                        int length = list.Count;
                        this.WriteUInt8((byte)length);
                        Type collectionType = type.GetInterface("ICollection`1");
                        Type valueType = collectionType.GetGenericArguments()[0];
                        for (int i = 0; i < length; i++)
                        {
                            this.WriteValue(valueType,list[i]);
                        }
                    }
                    else if (genericType == typeof(Dictionary<,>))
                    {
                        Dictionary<object,object> map = (Dictionary<object,object>)value;
                        int length = map.Count;
                        this.WriteUInt8((byte)length);
                        Type collectionType = type.GetInterface("ICollection`1");
                        Type keyValuePairType = collectionType.GetGenericArguments()[0];
                        Type keyType = keyValuePairType.GetGenericArguments()[0];
                        Type valueType = keyValuePairType.GetGenericArguments()[1];
                        foreach(KeyValuePair<object,object> kv in map)
                        {
                            this.WriteValue(keyType, kv.Key);
                            this.WriteValue(valueType, kv.Value);

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
                        this.WriteValue(field.FieldType, field.GetValue(value));

                    }
                }
            }
        }

    }
}