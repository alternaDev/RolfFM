#!/bin/sh

### BEGIN INIT INFO
# Provides:		RolfFM
# Required-Start: 	$remote_fs $syslog
# Required-Stop:	$remote_fs $syslog
# Default-Start:	2 3 4 5
# Default-Stop:		0 1 6
# Short-Description:	RolfFM Music Playback
# Description:		This service Controls the playback of music for RolfFM.
### END INIT INFO


DIR=/home/pi/RolfFM
DAEMON=$DIR/rolffm.py
DAEMON_NAME=RolfFM


DAEMON_OPTS="--logfile /var/log/rolffm.log"

DAEMON_USER=root

PIDFILE=/var/run/$DAEMON_NAME.pid


. /lib/lsb/init-functions


do_start () {
	log_daemon_msg "Starting system $DAEMON_NAME daemon"
	start-stop-daemon --start --background --pidfile $PIDFILE --make-pidfile --user $DAEMON_USER --startas $DAEMON -- $DAEMON_OPTS
	log_end_msg $?
}

do_stop () {
	log_daemon_msg "Stopping system $DAEMON_NAME daemon"
	start-stop-daemon --stop --pidfile $PIDFILE --retry 10
	log_end_msg $?
}

case "$1" in

	start|stop)
		do_${1}
		;;

	restart|reload|force-reload)
		do_stop
		do_start
		;;

	status)
		status_of_proc "$DAEMON_NAME" "$DAEMON" && exit 0 || exit $?
		;;

esac
exit 0
