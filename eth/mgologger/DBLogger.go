package mgologger

import (
	"bytes"
	"encoding/hex"
	"fmt"
	"log"
	"math/big"
	"strings"

	"github.com/ethereum/go-ethereum/common"
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
	Functrace    string
	Eventtrace   string
	TransferLogs string
}

var (
	Logger *mgo.Session
	Db     *mgo.Database

	BaseFunctracestr     string
	BaseEventtracestr    string
	BaseTransfertracestr string

	Functrace     *bytes.Buffer
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
	BaseFunctracestr = "index,calltype,depth,from,to,val,gas,input,output,callstack,traceaddr \n"
	BaseEventtracestr = "address,topics,data\n"
	BaseTransfertracestr = "from,to,tokenAddr,value,calldepth,callnum,traceindex\n"

	Functrace = bytes.NewBuffer(make([]byte, 4000000))
	Eventtrace = bytes.NewBuffer(make([]byte, 1000000))
	Transfertrace = bytes.NewBuffer(make([]byte, 1000000))

	for i := 0; i < 1025; i++ {
		CallStack[i] = 0
		TraceAddr[i] = 0
	}

	CurrentDepth = 0
	TraceIndex = 0
	MaxDepth = 0

	session, err := mgo.DialWithTimeout(url, 0)

	if err != nil {
		log.Fatal(err)
	}

	Logger = session

	Db = session.DB("ethereum")
}

func InitTrace() {
	Functrace.Reset()
	Eventtrace.Reset()
	Transfertrace.Reset()

	for i := 0; i < MaxDepth; i++ {
		CallStack[i] = 0
		TraceAddr[i] = 0
	}

	CurrentDepth = 0
	TraceIndex = 0
	MaxDepth = 0
}

func AddFuncLog(index int, ct string, d int, from string, to string, value string, g uint64, input string, output string) {
	if d == 0 {
		Functrace.WriteString(fmt.Sprintf("%d,%s,%d,%s,%s,%s,%d,0x%s,0x%s,[],[]\n", index, ct, d, from, to, value, g, input, output))
	} else {
		Functrace.WriteString(fmt.Sprintf("%d,%s,%d,%s,%s,%s,%d,0x%s,0x%s,%+v,%+v\n", index, ct, d, from, to, value, g, input, output, CallStack[1:d+1], TraceAddr[1:d+1]))
	}
}

func AddEventLog(addr common.Address, topics []common.Hash, data []byte) {
	Eventtrace.WriteString(fmt.Sprintf("%s,%s,0x%s\n", addr, topics, hex.EncodeToString(data)))
}

// This is invoked in 1 of 3 contexts, 2 of which occure in AddEventLog:
// 1. An ERC20 event
// 2. An ERC721 event
// 3. Any ethereum transfer event. Hooks .transfer()
func AddTransferLog(from string, to string, tokenAddr string, value string, depth int, Type string) {
	var output string

	if depth == 0 {
		output = fmt.Sprintf("%s,%s,%s,0x%s,%d,%d,[]\n", from, to, tokenAddr, value, depth, TraceIndex)
	} else {
		output = fmt.Sprintf("%s,%s,%s,0x%s,%d,%+v,%+v\n", from, to, tokenAddr, value, depth, TraceIndex, CallStack[1:depth+1])
	}

	Transfertrace.WriteString(output)
}

func WriteEntry(block big.Int, tx common.Hash, from string, to string, value big.Int, gasPrice big.Int, gasUsed uint64, extra string) {
	eventTraceStr := strings.TrimSuffix(string(bytes.Trim(Eventtrace.Bytes(), "\x00")), "\n")
	transferTraceStr := strings.TrimSuffix(string(bytes.Trim(Transfertrace.Bytes(), "\x00")), "\n")
	funcTraceStr := strings.TrimSuffix(string(bytes.Trim(Functrace.Bytes(), "\x00")), "\n")

	trace := Collection{
		Block:        block.String(),
		Tx:           tx.String(),
		From:         from,
		To:           to,
		Value:        value.String(),
		GasPrice:     gasPrice.String(),
		GasUsed:      fmt.Sprintf("%d", gasUsed),
		Functrace:    funcTraceStr,
		Eventtrace:   eventTraceStr,
		TransferLogs: transferTraceStr,
	}

	err := Db.C("eth").Insert(trace)

	trace = Collection{}

	if err != nil {
		log.Println(err, ". Unable to log transaction tx: ", tx)
	}
}

func CloseMongo() {
	defer Logger.Close()
}
