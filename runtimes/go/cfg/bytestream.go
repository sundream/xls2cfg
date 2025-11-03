package cfg

import (
	"bytes"
	"encoding/binary"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math"
	"math/big"
	"os"
	"reflect"
)

type ByteStream struct {
	buffer *bytes.Buffer
}

var byteOrder = binary.LittleEndian

func NewByteStream(buf []byte) *ByteStream {
	return &ByteStream{
		buffer: bytes.NewBuffer(buf),
	}
}

func DestroyByteStream(bs *ByteStream) {
	if bs != nil {
		bs.buffer.Reset()
	}
}

func (bs *ByteStream) WriteBool(value bool) {
	if value {
		bs.WriteByte(1)
	} else {
		bs.WriteByte(0)
	}
}

func (bs *ByteStream) WriteByte(value byte) {
	err := bs.buffer.WriteByte(value)
	if err != nil {
		panic(err)
	}
}

func (bs *ByteStream) WriteUInt8(value uint8) {
	bs.WriteByte(value)
}

func (bs *ByteStream) WriteUInt16(value uint16) {
	err := binary.Write(bs.buffer, byteOrder, value)
	if err != nil {
		panic(err)
	}
}

func (bs *ByteStream) WriteUInt32(value uint32) {
	err := binary.Write(bs.buffer, byteOrder, value)
	if err != nil {
		panic(err)
	}
}

func (bs *ByteStream) WriteUInt64(value uint64) {
	err := binary.Write(bs.buffer, byteOrder, value)
	if err != nil {
		panic(err)
	}
}

func (bs *ByteStream) WriteInt8(value int8) {
	bs.WriteUInt8(uint8(value))
}

func (bs *ByteStream) WriteInt16(value int16) {
	bs.WriteUInt16(uint16(value))
}

func (bs *ByteStream) WriteInt32(value int32) {
	bs.WriteUInt32(uint32(value))
}

func (bs *ByteStream) WriteInt64(value int64) {
	bs.WriteUInt64(uint64(value))
}

func (bs *ByteStream) WriteBigInt(value BigInt) {
	bs.WriteString(value.String())
}

func (bs *ByteStream) WritebigInt(value big.Int) {
	bs.WriteString(value.String())
}

func (bs *ByteStream) WriteFloat32(value float32) {
	number := int64(float64(value) * math.Pow10(5))
	bs.WriteInt64(number)
}

func (bs *ByteStream) WriteFloat(value float32) {
	bs.WriteFloat32(value)
}

func (bs *ByteStream) WriteFloat64(value float64) {
	number := int64(float64(value) * math.Pow10(8))
	bs.WriteInt64(number)
}

func (bs *ByteStream) WriteDouble(value float64) {
	bs.WriteFloat64(value)
}

func (bs *ByteStream) WriteString(value string) {
	bs.WriteUInt16(uint16(len(value)))
	n, err := bs.buffer.WriteString(value)
	if err != nil || n != len(value) {
		panic(err)
	}
}

func (bs *ByteStream) WriteJson(data any) {
	bytes, err := json.Marshal(data)
	if err != nil {
		panic(err)
	}
	bs.WriteString(string(bytes))
}

func (bs *ByteStream) Write(byte []byte, startPos int, length int) {
	n, err := bs.buffer.Write(byte[startPos : startPos+length])
	if err != nil || n != length {
		panic(err)
	}
}

func (bs *ByteStream) ReadBool() (bool, error) {
	b, err := bs.ReadByte()
	return b != 0, err
}

func (bs *ByteStream) ReadByte() (byte, error) {
	b, err := bs.buffer.ReadByte()
	return b, err
}

func (bs *ByteStream) ReadUInt8() (uint8, error) {
	b, err := bs.ReadByte()
	return uint8(b), err
}

func (bs *ByteStream) ReadUInt16() (uint16, error) {
	var value uint16
	err := binary.Read(bs.buffer, binary.LittleEndian, &value)
	return value, err
}

func (bs *ByteStream) ReadUInt32() (uint32, error) {
	var value uint32
	err := binary.Read(bs.buffer, binary.LittleEndian, &value)
	return value, err
}

func (bs *ByteStream) ReadUInt64() (uint64, error) {
	var value uint64
	err := binary.Read(bs.buffer, binary.LittleEndian, &value)
	return value, err
}

func (bs *ByteStream) ReadInt8() (int8, error) {
	value, err := bs.ReadUInt8()
	return int8(value), err
}

func (bs *ByteStream) ReadInt16() (int16, error) {
	value, err := bs.ReadUInt16()
	return int16(value), err
}

func (bs *ByteStream) ReadInt32() (int32, error) {
	value, err := bs.ReadUInt32()
	return int32(value), err
}

func (bs *ByteStream) ReadInt64() (int64, error) {
	value, err := bs.ReadUInt64()
	return int64(value), err
}

func (bs *ByteStream) ReadBigInt() (BigInt, error) {
	var result BigInt
	str, err := bs.ReadString()
	if err != nil {
		return result, err
	}
	_, ok := result.SetString(str, 10)
	if !ok {
		return result, errors.New("invalid bigint string")
	}
	return result, nil
}

// @deprecated
func (bs *ByteStream) ReadbigInt() (big.Int, error) {
	var result big.Int
	str, err := bs.ReadString()
	if err != nil {
		return result, err
	}
	_, ok := result.SetString(str, 10)
	if !ok {
		return result, errors.New("invalid bigint string")
	}
	return result, nil
}

func (bs *ByteStream) ReadFloat32() (float32, error) {
	number, err := bs.ReadInt64()
	if err != nil {
		return 0, err
	}
	return float32(float64(number) / math.Pow10(5)), nil
}

func (bs *ByteStream) ReadFloat() (float32, error) {
	return bs.ReadFloat32()
}

func (bs *ByteStream) ReadFloat64() (float64, error) {
	number, err := bs.ReadInt64()
	if err != nil {
		return 0, err
	}
	return float64(number) / math.Pow10(8), nil
}

func (bs *ByteStream) ReadDouble() (float64, error) {
	return bs.ReadFloat64()
}

func (bs *ByteStream) ReadString() (string, error) {
	length, err := bs.ReadUInt16()
	if err != nil {
		return "", err
	}
	buf := make([]byte, length)
	n, err := io.ReadFull(bs.buffer, buf)
	if err != nil || n != int(length) {
		return "", err
	}
	return string(buf), nil
}

func (bs *ByteStream) ReadJson() (any, error) {
	str, err := bs.ReadString()
	if err != nil {
		return nil, err
	}
	var v any
	err = json.Unmarshal([]byte(str), &v)
	return v, err
}

func (bs *ByteStream) Read(byte []byte, startPos int, length int) error {
	n, err := bs.buffer.Read(byte[startPos : startPos+length])
	if n != length {
		return io.EOF
	}
	return err
}

func (bs *ByteStream) Clear() {
	bs.buffer.Reset()
}

func (bs *ByteStream) ReadFile(filename string) error {
	data, err := os.ReadFile(filename)
	if err != nil {
		return err
	}
	bs.buffer.Write(data)
	return nil
}

func (bs *ByteStream) WriteFile(filename string) {
	err := os.WriteFile(filename, bs.buffer.Bytes(), 0644)
	if err != nil {
		panic(err)
	}
}

func ReadList[V any](bs *ByteStream, result *[]V) error {
	return readList(bs, reflect.ValueOf(result).Elem())
}

func readList(bs *ByteStream, v reflect.Value) error {
	length, err := bs.ReadUInt8()
	if err != nil {
		return err
	}
	slice := reflect.MakeSlice(v.Type(), int(length), int(length))
	for i := 0; i < int(length); i++ {
		if err := readValue(bs, slice.Index(i)); err != nil {
			return err
		}
	}
	v.Set(slice)
	return nil
}

func ReadMap[K comparable, V any](bs *ByteStream, result *map[K]V) error {
	return readMap(bs, reflect.ValueOf(result).Elem())
}

func readMap(bs *ByteStream, v reflect.Value) error {
	length, err := bs.ReadUInt8()
	if err != nil {
		return err
	}
	mapInstance := reflect.MakeMapWithSize(v.Type(), int(length))
	for i := 0; i < int(length); i++ {
		key := reflect.New(v.Type().Key()).Elem()
		value := reflect.New(v.Type().Elem()).Elem()
		if err := readValue(bs, key); err != nil {
			return err
		}
		if err := readValue(bs, value); err != nil {
			return err
		}
		mapInstance.SetMapIndex(key, value)
	}
	v.Set(mapInstance)
	return nil
}

func ReadStruct[T any](bs *ByteStream, result *T) error {
	return readStruct(bs, reflect.ValueOf(result).Elem())
}

func readStruct(bs *ByteStream, v reflect.Value) error {
	for i := 0; i < v.NumField(); i++ {
		field := v.Field(i)
		if field.CanSet() {
			if err := readValue(bs, field); err != nil {
				return err
			}
		}
	}
	return nil
}

func ReadValue[T any](bs *ByteStream, result *T) error {
	return readValue(bs, reflect.ValueOf(result).Elem())
}

func readValue(bs *ByteStream, v reflect.Value) error {
	if !v.CanSet() {
		return errors.New("value is not settable")
	}

	switch v.Kind() {
	case reflect.Bool:
		vv, err := bs.ReadBool()
		if err != nil {
			return err
		}
		v.SetBool(vv)
	case reflect.Int8:
		vv, err := bs.ReadInt8()
		if err != nil {
			return err
		}
		v.SetInt(int64(vv))
	case reflect.Int16:
		vv, err := bs.ReadInt16()
		if err != nil {
			return err
		}
		v.SetInt(int64(vv))
	case reflect.Int32:
		vv, err := bs.ReadInt32()
		if err != nil {
			return err
		}
		v.SetInt(int64(vv))
	case reflect.Int64:
		vv, err := bs.ReadInt64()
		if err != nil {
			return err
		}
		v.SetInt(vv)
	case reflect.Uint8:
		vv, err := bs.ReadUInt8()
		if err != nil {
			return err
		}
		v.SetUint(uint64(vv))
	case reflect.Uint16:
		vv, err := bs.ReadUInt16()
		if err != nil {
			return err
		}
		v.SetUint(uint64(vv))
	case reflect.Uint32:
		vv, err := bs.ReadUInt32()
		if err != nil {
			return err
		}
		v.SetUint(uint64(vv))
	case reflect.Uint64:
		vv, err := bs.ReadUInt64()
		if err != nil {
			return err
		}
		v.SetUint(vv)
	case reflect.Float32:
		vv, err := bs.ReadFloat32()
		if err != nil {
			return err
		}
		v.SetFloat(float64(vv))
	case reflect.Float64:
		vv, err := bs.ReadFloat64()
		if err != nil {
			return err
		}
		v.SetFloat(vv)
	case reflect.String:
		vv, err := bs.ReadString()
		if err != nil {
			return err
		}
		v.SetString(vv)
	case reflect.Slice:
		if err := readList(bs, v); err != nil {
			return err
		}
	case reflect.Map:
		if err := readMap(bs, v); err != nil {
			return err
		}
	case reflect.Struct:
		if (v.Type() == reflect.TypeOf(BigInt{})) {
			// BigInt
			result, err := bs.ReadBigInt()
			if err != nil {
				return err
			}
			v.Set(reflect.ValueOf(result))
			return nil
		} else if v.Type() == reflect.TypeOf(big.Int{}) {
			// big.Int
			result, err := bs.ReadbigInt()
			if err != nil {
				return err
			}
			v.Set(reflect.ValueOf(result))
			return nil
		}
		// struct
		readStruct(bs, v)
	case reflect.Interface:
		// json
		data, err := bs.ReadJson()
		if err != nil {
			return err
		}
		v.Set(reflect.ValueOf(data))
	default:
		return errors.New(fmt.Sprintf("unsupported kind: %s", v.Kind()))
	}
	return nil
}

func WriteList[V any](bs *ByteStream, list []V) {
	writeList(bs, reflect.ValueOf(list))
}

func writeList(bs *ByteStream, v reflect.Value) {
	length := v.Len()
	bs.WriteUInt8(uint8(length))
	for i := 0; i < length; i++ {
		writeValue(bs, v.Index(i))
	}
}

func WriteMap[K comparable, V any](bs *ByteStream, m map[K]V) {
	writeMap(bs, reflect.ValueOf(m))
}

func writeMap(bs *ByteStream, v reflect.Value) {
	length := v.Len()
	bs.WriteUInt8(uint8(length))
	for _, key := range v.MapKeys() {
		writeValue(bs, key)
		writeValue(bs, v.MapIndex(key))
	}
}

func WriteStruct[T any](bs *ByteStream, s T) {
	writeStruct(bs, reflect.ValueOf(s))
}

func writeStruct(bs *ByteStream, v reflect.Value) {
	if v.Kind() != reflect.Struct {
		panic("writeStruct: value is not a struct")
	}
	for i := 0; i < v.NumField(); i++ {
		field := v.Field(i)
		writeValue(bs, field)
	}
}

func WriteValue[T any](bs *ByteStream, value T) {
	writeValue(bs, reflect.ValueOf(value))
}

func writeValue(bs *ByteStream, v reflect.Value) {
	switch v.Kind() {
	case reflect.Bool:
		bs.WriteBool(v.Bool())
	case reflect.Int8:
		bs.WriteInt8(int8(v.Int()))
	case reflect.Int16:
		bs.WriteInt16(int16(v.Int()))
	case reflect.Int32:
		bs.WriteInt32(int32(v.Int()))
	case reflect.Int64:
		bs.WriteInt64(v.Int())
	case reflect.Uint8:
		bs.WriteUInt8(uint8(v.Uint()))
	case reflect.Uint16:
		bs.WriteUInt16(uint16(v.Uint()))
	case reflect.Uint32:
		bs.WriteUInt32(uint32(v.Uint()))
	case reflect.Uint64:
		bs.WriteUInt64(v.Uint())
	case reflect.Float32:
		bs.WriteFloat32(float32(v.Float()))
	case reflect.Float64:
		bs.WriteFloat64(v.Float())
	case reflect.String:
		bs.WriteString(v.String())
	case reflect.Slice:
		writeList(bs, v)
	case reflect.Map:
		writeMap(bs, v)
	case reflect.Struct:
		if v.Type() == reflect.TypeOf(BigInt{}) {
			bs.WriteBigInt(v.Interface().(BigInt))
		} else if v.Type() == reflect.TypeOf(big.Int{}) {
			bs.WritebigInt(v.Interface().(big.Int))
		} else {
			writeStruct(bs, v)
		}
	case reflect.Interface:
		data, err := json.Marshal(v.Interface())
		if err != nil {
			panic(err)
		}
		bs.WriteString(string(data))
	default:
		panic(fmt.Sprintf("unsupported kind: %s", v.Kind()))
	}
}
