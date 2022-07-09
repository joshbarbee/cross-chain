package watcher

import (
	"log"
	"os"
	"os/exec"
)

func RestartSvc() {
	cmd := exec.Command("./build/bin/geth --syncmode=full --datadir=./node --config=./config.toml &")

	err := cmd.Run()

	if err != nil {
		log.Fatal(err)
	}

	log.Println("SWITCHING TO FULL SYNC")
	os.Exit(3333333)
}
