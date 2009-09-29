#!/bin/bash

LOGFILE="/tmp/nicotine_memoryusage.`date +%Y-%m-%d_%H-%M-%S`.log"
POLLTIME="15"

getpid() {
	PID=`ps -C nicotine -o pid=` # in case we managed to rename the process with procname
	if [ -z "$PID" ]; then
		# We use p[y]thon since that way we will not encounter our own sed command in the list
		PID=`ps u | sed -n '/p[y]thon.*nicotine/{s/^[^ ]\+[ ]*//;s/ .*//;p;q}'`
	fi
}

writelog() {
	echo "$1"
	echo "$1" >> "$LOGFILE"
}

getpid
if [ ! -z "$PID" ]; then
	echo "BTW, you can start this script before you start n+"
	echo ""
else
	echo "Waiting for Nicotine+ to come alive..."
	while [ -z "$PID" ]; do
		sleep 1
		getpid
	done
	echo "...found it."
	echo ""
fi

echo "Nicotine+'s PID:   $PID"
echo "Saving to logfile: $LOGFILE"
echo "Poll interval:     $POLLTIME seconds"
echo ""

pidstat -r -p "$PID" "$POLLTIME" | while read line ; do 
	writelog "$line" 
done

writelog "`date +%H:%M:%S` EOF"
