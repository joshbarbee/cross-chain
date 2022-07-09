package mgologger

import (
	"bytes"
	"encoding/hex"
	"fmt"
	"log"
	"math/big"
	"strings"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/globalsign/mgo"
)

type Collection struct {
	Block        string
	Tx           string
	From         string
	To           string
	Value        string
	GasPrice     string
	GasUsed      string
	Eventtrace   string
	TransferLogs string
}

var (
	Logger               *mgo.Session
	Db                   *mgo.Database
	BaseEventtracestr    string
	BaseTransfertracestr string
	BaseERC721str        string
	BaseERC20str         string

	Eventtrace    *bytes.Buffer
	Transfertrace *bytes.Buffer

	CurrentDepth int
	MaxDepth     int

	TransferSig       common.Hash
	ApprovalSig       common.Hash
	ApprovalForAllSig common.Hash

	TraceAddr [1025]uint
	CallStack [1025]uint

	TraceIndex int
)

func InitLogger() {
	url := "mongodb://127.0.0.1:27017"

	// initialize log for current tx
	BaseEventtracestr = "address,topics,data,type,function\n"
	BaseTransfertracestr = "from,to,tokenAddr,value,calldepth,callnum,traceindex,type\n"

	Eventtrace = bytes.NewBuffer(make([]byte, 2000000))
	Transfertrace = bytes.NewBuffer(make([]byte, 200000))

	for i := 0; i < 1025; i++ {
		CallStack[i] = 0
	}

	CurrentDepth = 0
	TraceIndex = 0
	MaxDepth = 0

	// initialize event function signatures for token tracing
	TransferSig = crypto.Keccak256Hash([]byte("Transfer(address,address,uint256)"))
	ApprovalSig = crypto.Keccak256Hash([]byte("Approval(address,address,uint256)"))
	ApprovalForAllSig = crypto.Keccak256Hash([]byte("Approval(address,address,bool)"))

	session, err := mgo.DialWithTimeout(url, 0)

	if err != nil {
		log.Fatal(err)
	}

	Logger = session

	Db = session.DB("ethereum")
}

func InitTrace() {
	Eventtrace.Reset()
	Transfertrace.Reset()

	Eventtrace.WriteString(BaseEventtracestr)
	Transfertrace.WriteString(BaseTransfertracestr)
}

func AddEventLog(addr common.Address, topics []common.Hash, data []byte, logType string, function string) {
	Eventtrace.WriteString(fmt.Sprintf("%s,%s,0x%s,%s,%s\n", addr, topics, hex.EncodeToString(data), logType, function))
}

// This is invoked in 1 of 3 contexts, 2 of which occure in AddEventLog:
// 1. An ERC20 event
// 2. An ERC721 event
// 3. Any ethereum transfer event. Hooks .transfer()
func AddTransferLog(from string, to string, tokenAddr string, value string, depth int, Type string) {
	var output string

	if depth == 0 {
		output = fmt.Sprintf("%s,%s,%s,0x%s,%d,%d,[],%s\n", from, to, tokenAddr, value, depth, TraceIndex, Type)
	} else {
		output = fmt.Sprintf("%s,%s,%s,0x%s,%d,%+v,%+v,%s\n", from, to, tokenAddr, value, depth, TraceIndex, CallStack[1:depth+1], Type)
	}

	Transfertrace.WriteString(output)
}

// we check if erc20 based on following info:
// 1. if event signature is Transfer(from,to,value) or Approval(owner,spender,value)
// 2. length of topics is 3
func IsERC20(tokenAddr common.Address, topics []common.Hash, data []byte, depth int) (ret bool, function string) {
	if len(topics) != 3 {
		return false, ""
	}

	switch topics[0] {
	case TransferSig:
		from := topics[1].String()
		to := topics[2].String()
		tokenAddr := tokenAddr.String()
		value := hex.EncodeToString(data)
		AddTransferLog(from, to, tokenAddr, value, depth, "ERC20")
		return true, "Transfer"
	case ApprovalSig:
		return true, "Approval"
	default:
		return false, ""
	}
}

// we check if erc721 based on following info
// 1. if event sig is Transfer(from,to,value) or Approval(owner,spender,value) or ApporvalForAll(address,address,bool)
// 2. length of topics is 4
func IsERC721(tokenAddr common.Address, topics []common.Hash, data []byte, depth int) (ret bool, function string) {
	if len(topics) != 4 {
		return false, ""
	}

	switch topics[0] {
	case TransferSig:
		from := topics[1].String()
		to := topics[2].String()
		tokenAddr := tokenAddr.String()
		value := hex.EncodeToString(data)
		AddTransferLog(from, to, tokenAddr, value, depth, "ERC721")
		return true, "Transfer"
	case ApprovalSig:
		return true, "Approval"
	case ApprovalForAllSig:
		return true, "ApprovalForAll"
	default:
		return false, ""
	}
}

func WriteEntry(block big.Int, tx common.Hash, from string, to string, value big.Int, gasPrice big.Int, gasUsed uint64, extra string) {
	eventTraceStr := strings.TrimSuffix(string(bytes.Trim(Eventtrace.Bytes(), "\x00")), "\n")
	transferTraceStr := strings.TrimSuffix(string(bytes.Trim(Transfertrace.Bytes(), "\x00")), "\n")

	trace := Collection{
		Block:        block.String(),
		Tx:           tx.String(),
		From:         from,
		To:           to,
		Value:        value.String(),
		GasPrice:     gasPrice.String(),
		GasUsed:      fmt.Sprintf("%d", gasUsed),
		Eventtrace:   eventTraceStr,
		TransferLogs: transferTraceStr,
	}

	err := Db.C("bsc").Insert(trace)

	trace = Collection{}

	if err != nil {
		log.Println(err, ". Unable to log transaction tx: ", tx)
	}
}

func CloseMongo() {
	defer Logger.Close()
}
