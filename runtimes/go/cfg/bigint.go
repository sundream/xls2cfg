package cfg

import (
	"encoding/json"
	"fmt"
	"math/big"
)

// BigInt wraps big.Int to support JSON serialization
type BigInt struct {
    big.Int
}

func (b BigInt) MarshalJSON() ([]byte, error) {
    return json.Marshal(b.String())
}

func (b *BigInt) UnmarshalJSON(data []byte) error {
    var s string
    if err := json.Unmarshal(data, &s); err != nil {
        return err
    }
    if _, ok := b.SetString(s, 10); !ok {
        return fmt.Errorf("invalid big.Int string: %s", s)
    }
    return nil
}