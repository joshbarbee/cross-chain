// Code generated by MockGen. DO NOT EDIT.
// Source: github.com/ethereum/go-ethereum/consensus/bor (interfaces: IHeimdallClient)

// Package mocks is a generated GoMock package.
package mocks

import (
	reflect "reflect"

	clerk "github.com/ethereum/go-ethereum/consensus/bor/clerk"
	checkpoint "github.com/ethereum/go-ethereum/consensus/bor/heimdall/checkpoint"
	span "github.com/ethereum/go-ethereum/consensus/bor/heimdall/span"
	gomock "github.com/golang/mock/gomock"
)

// MockIHeimdallClient is a mock of IHeimdallClient interface.
type MockIHeimdallClient struct {
	ctrl     *gomock.Controller
	recorder *MockIHeimdallClientMockRecorder
}

// MockIHeimdallClientMockRecorder is the mock recorder for MockIHeimdallClient.
type MockIHeimdallClientMockRecorder struct {
	mock *MockIHeimdallClient
}

// NewMockIHeimdallClient creates a new mock instance.
func NewMockIHeimdallClient(ctrl *gomock.Controller) *MockIHeimdallClient {
	mock := &MockIHeimdallClient{ctrl: ctrl}
	mock.recorder = &MockIHeimdallClientMockRecorder{mock}
	return mock
}

// EXPECT returns an object that allows the caller to indicate expected use.
func (m *MockIHeimdallClient) EXPECT() *MockIHeimdallClientMockRecorder {
	return m.recorder
}

// Close mocks base method.
func (m *MockIHeimdallClient) Close() {
	m.ctrl.T.Helper()
	m.ctrl.Call(m, "Close")
}

// Close indicates an expected call of Close.
func (mr *MockIHeimdallClientMockRecorder) Close() *gomock.Call {
	mr.mock.ctrl.T.Helper()
	return mr.mock.ctrl.RecordCallWithMethodType(mr.mock, "Close", reflect.TypeOf((*MockIHeimdallClient)(nil).Close))
}

// FetchLatestCheckpoint mocks base method.
func (m *MockIHeimdallClient) FetchLatestCheckpoint() (*checkpoint.Checkpoint, error) {
	m.ctrl.T.Helper()
	ret := m.ctrl.Call(m, "FetchLatestCheckpoint")
	ret0, _ := ret[0].(*checkpoint.Checkpoint)
	ret1, _ := ret[1].(error)
	return ret0, ret1
}

// FetchLatestCheckpoint indicates an expected call of FetchLatestCheckpoint.
func (mr *MockIHeimdallClientMockRecorder) FetchLatestCheckpoint() *gomock.Call {
	mr.mock.ctrl.T.Helper()
	return mr.mock.ctrl.RecordCallWithMethodType(mr.mock, "FetchLatestCheckpoint", reflect.TypeOf((*MockIHeimdallClient)(nil).FetchLatestCheckpoint))
}

// Span mocks base method.
func (m *MockIHeimdallClient) Span(arg0 uint64) (*span.HeimdallSpan, error) {
	m.ctrl.T.Helper()
	ret := m.ctrl.Call(m, "Span", arg0)
	ret0, _ := ret[0].(*span.HeimdallSpan)
	ret1, _ := ret[1].(error)
	return ret0, ret1
}

// Span indicates an expected call of Span.
func (mr *MockIHeimdallClientMockRecorder) Span(arg0 interface{}) *gomock.Call {
	mr.mock.ctrl.T.Helper()
	return mr.mock.ctrl.RecordCallWithMethodType(mr.mock, "Span", reflect.TypeOf((*MockIHeimdallClient)(nil).Span), arg0)
}

// StateSyncEvents mocks base method.
func (m *MockIHeimdallClient) StateSyncEvents(arg0 uint64, arg1 int64) ([]*clerk.EventRecordWithTime, error) {
	m.ctrl.T.Helper()
	ret := m.ctrl.Call(m, "StateSyncEvents", arg0, arg1)
	ret0, _ := ret[0].([]*clerk.EventRecordWithTime)
	ret1, _ := ret[1].(error)
	return ret0, ret1
}

// StateSyncEvents indicates an expected call of StateSyncEvents.
func (mr *MockIHeimdallClientMockRecorder) StateSyncEvents(arg0, arg1 interface{}) *gomock.Call {
	mr.mock.ctrl.T.Helper()
	return mr.mock.ctrl.RecordCallWithMethodType(mr.mock, "StateSyncEvents", reflect.TypeOf((*MockIHeimdallClient)(nil).StateSyncEvents), arg0, arg1)
}