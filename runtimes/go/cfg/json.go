package cfg

import (
	"errors"
	"fmt"
	"math/big"
	"reflect"
)

func DeserializeBoolFromJson(result *bool, data any) error {
	if boolValue, ok := data.(bool); ok {
		*result = bool(boolValue)
		return nil
	} else {
		return errors.New("type error")
	}
}

func deserializeBoolFromJson(result reflect.Value, data any) error {
	if boolValue, ok := data.(bool); ok {
		result.SetBool(boolValue)
		return nil
	} else {
		return errors.New("type error")
	}
}

func DeserializeIntFromJson[T ~int | ~int8 | ~int16 | ~int32 | ~int64 | ~uint | ~uint8 | ~uint16 | ~uint32 | ~uint64](result *T, data any) error {
	if floatValue, ok := data.(float64); ok {
		*result = T(floatValue)
		return nil
	}
	return errors.New("type error")
}

func deserializeIntFromJson(result reflect.Value, data any) error {
	if floatValue, ok := data.(float64); ok {
		result.SetInt(int64(floatValue))
		return nil
	} else {
		return errors.New("type error")
	}
}

func deserializeUintFromJson(result reflect.Value, data any) error {
	if floatValue, ok := data.(float64); ok {
		result.SetUint(uint64(floatValue))
		return nil
	} else {
		return errors.New("type error")
	}
}

func DeserializeBigIntFromJson(result *BigInt, data any) error {
	if strValue, ok := data.(string); ok {
		_, ok := result.SetString(strValue, 10)
		if !ok {
			return errors.New("invalid bigint string")
		}
		return nil
	}
	return errors.New("type error")
}

func deserializeBigIntFromJson(result reflect.Value, data any) error {
	if strValue, ok := data.(string); ok {
		bigIntPtr := result.Addr().Interface().(*BigInt)
		_, ok := bigIntPtr.SetString(strValue, 10)
		if !ok {
			return errors.New("invalid bigint string")
		}
		return nil
	} else {
		return errors.New("type error")
	}
}

// @deprecated
func DeserializebigIntFromJson(result *big.Int, data any) error {
	if strValue, ok := data.(string); ok {
		_, ok := result.SetString(strValue, 10)
		if !ok {
			return errors.New("invalid bigint string")
		}
		return nil
	}
	return errors.New("type error")
}

func deserializebigIntFromJson(result reflect.Value, data any) error {
	if strValue, ok := data.(string); ok {
		bigIntPtr := result.Addr().Interface().(*big.Int)
		_, ok := bigIntPtr.SetString(strValue, 10)
		if !ok {
			return errors.New("invalid bigint string")
		}
		return nil
	} else {
		return errors.New("type error")
	}
}

func DeserializeFloatFromJson[T ~float32 | ~float64](result *T, data any) error {
	if floatValue, ok := data.(float64); ok {
		*result = T(floatValue)
		return nil
	}
	return errors.New("type error")
}

func deserializeFloatFromJson(result reflect.Value, data any) error {
	if floatValue, ok := data.(float64); ok {
		result.SetFloat(floatValue)
		return nil
	} else {
		return errors.New("type error")
	}
}

func DeserializeStringFromJson(result *string, data any) error {
	if strValue, ok := data.(string); ok {
		*result = string(strValue)
		return nil
	}
	return errors.New("type error")
}

func deserializeStringFromJson(result reflect.Value, data any) error {
	if strValue, ok := data.(string); ok {
		result.SetString(strValue)
		return nil
	} else {
		return errors.New("type error")
	}
}

func DeserializeJsonFromJson(result *any, data any) error {
	*result = data
	return nil
}

func DeserializeListFromJson[T any](result *[]T, data any) error {
	return deserializeListFromJson(reflect.ValueOf(result).Elem(), data)
}

func deserializeListFromJson(result reflect.Value, data any) error {
	if listValue, ok := data.([]any); ok {
		sliceType := result.Type()
		elemType := sliceType.Elem()
		newSlice := reflect.MakeSlice(sliceType, 0, len(listValue))
		for _, item := range listValue {
			elemPtr := reflect.New(elemType)
			if err := deserializeValueFromJson(elemPtr.Elem(), item); err != nil {
				return err
			}
			newSlice = reflect.Append(newSlice, elemPtr.Elem())
		}
		result.Set(newSlice)
		return nil
	} else {
		return errors.New("type error")
	}
}

func DeserializeMapFromJson[K comparable, V any](result *map[K]V, data any) error {
	return deserializeMapFromJson(reflect.ValueOf(result).Elem(), data)
}

func deserializeMapFromJson(result reflect.Value, data any) error {
	if mapValue, ok := data.(map[string]any); ok {
		keyType := result.Type().Key()
		valType := result.Type().Elem()
		newMap := reflect.MakeMap(result.Type())
		for k, v := range mapValue {
			keyPtr := reflect.New(keyType)
			if err := deserializeValueFromJson(keyPtr.Elem(), k); err != nil {
				return err
			}
			valPtr := reflect.New(valType)
			if err := deserializeValueFromJson(valPtr.Elem(), v); err != nil {
				return err
			}
			newMap.SetMapIndex(keyPtr.Elem(), valPtr.Elem())
		}
		result.Set(newMap)
		return nil
	} else {
		return errors.New("type error")
	}
}

func DeserializeStructFromJson[T any](result *T, data any) error {
	return deserializeStructFromJson(reflect.ValueOf(result).Elem(), data)
}

func deserializeStructFromJson(result reflect.Value, data any) error {
	// 使用反射检查 T 是否为结构体
	resultType := result.Type()
	if resultType.Kind() != reflect.Struct {
		return errors.New("t must be a struct")
	}

	// 确保 data 是一个 map
	jsonData, ok := data.(map[string]any)
	if !ok {
		return errors.New("data must be a map[string]any")
	}

	// 遍历结构体字段
	for i := 0; i < resultType.NumField(); i++ {
		field := resultType.Field(i)
		fieldValue := result.Field(i)
		jsonKey := field.Tag.Get("json")
		if jsonKey == "" {
			jsonKey = field.Name
		}

		// 从 JSON 数据中获取值
		if value, ok := jsonData[jsonKey]; ok {
			if fieldValue.CanSet() {
				if err := deserializeValueFromJson(fieldValue, value); err != nil {
					return fmt.Errorf("failed to deserialize field %s: %w", field.Name, err)
				}
			} else {
				return fmt.Errorf("Field %s cannot be set\n", field.Name)
			}
		} else {
			fmt.Printf("JSON key %s not found for field %s at type %s\n", jsonKey, field.Name, resultType.Name())
		}
	}
	return nil
}

func deserializeValueFromJson(result reflect.Value, data any) error {
	switch result.Kind() {
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		if err := deserializeIntFromJson(result, data); err != nil {
			return err
		}
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
		if err := deserializeUintFromJson(result, data); err != nil {
			return err
		}
	case reflect.String:
		if err := deserializeStringFromJson(result, data); err != nil {
			return err
		}
	case reflect.Bool:
		if err := deserializeBoolFromJson(result, data); err != nil {
			return err
		}
	case reflect.Float32, reflect.Float64:
		if err := deserializeFloatFromJson(result, data); err != nil {
			return err
		}
	case reflect.Slice:
		if err := deserializeListFromJson(result, data); err != nil {
			return err
		}
	case reflect.Map:
		if err := deserializeMapFromJson(result, data); err != nil {
			return err
		}
	case reflect.Struct:
		if result.Type() == reflect.TypeOf(BigInt{}) {
			if err := deserializeBigIntFromJson(result, data); err != nil {
				return err
			}
		} else if result.Type() == reflect.TypeOf(big.Int{}) {
			if err := deserializebigIntFromJson(result, data); err != nil {
				return err
			}
		} else if err := deserializeStructFromJson(result, data); err != nil {
			return err
		}
	case reflect.Interface:
		// json
		result.Set(reflect.ValueOf(data))
	default:
		return fmt.Errorf("unsupported type: %s", result.Type())
	}
	return nil
}

func DeserializeValueFromJson[T any](result *T, data any) error {
	return deserializeValueFromJson(reflect.ValueOf(result).Elem(), data)
}
