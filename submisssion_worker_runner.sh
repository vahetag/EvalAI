#!/bin/bash
# submssion_worker_runner.sh
# Usage:
#   ./submssion_worker_runner.sh start
#   ./submssion_worker_runner.sh stop
#   ./submssion_worker_runner.sh restart
#   ./submssion_worker_runner.sh logs [number_of_lines]

# Load environment variables
set -a; . docker/prod_self/docker.env; set +a

# Configuration variables
PYTHON_MODULE="scripts.workers.submission_worker"
LOG_DIR="worker_logs"
LOG_SUBDIR="submission_worker"
LOG_FILE_PREFIX="v"
CURRENT_LOG_RECORD="${LOG_DIR}/${LOG_SUBDIR}/current_log_file_name.txt"

# Function to start the worker
start_worker() {
    echo "Stopping any previous instance..."
    pkill -f "$PYTHON_MODULE" 2>/dev/null
    sleep 10;

    # Create log directory if needed
    mkdir -p "${LOG_DIR}/${LOG_SUBDIR}"
    
    # Determine the current date and next log number
    CURRENT_DATE=$(date +"%d_%m_%y")
    LOG_NUM=0

    # Find the highest log number for the current date
    for FILE in ${LOG_DIR}/${LOG_SUBDIR}/${LOG_FILE_PREFIX}_${CURRENT_DATE}_*.out; do
        if [[ $FILE =~ ${LOG_DIR}/${LOG_SUBDIR}/${LOG_FILE_PREFIX}_${CURRENT_DATE}_([0-9]+)\.out ]]; then
            NUM=${BASH_REMATCH[1]}
            DECIMAL_NUM=$((10#$NUM))
            if (( DECIMAL_NUM > LOG_NUM )); then
                LOG_NUM=$DECIMAL_NUM
            fi
        fi
    done

    # Increment and pad the log number
    ((LOG_NUM++))
    printf -v PADDED_LOG_NUM "%02d" "$LOG_NUM"
    LOG_FILE="${LOG_DIR}/${LOG_SUBDIR}/${LOG_FILE_PREFIX}_${CURRENT_DATE}_${PADDED_LOG_NUM}.out"

    # Save the current log file name for future reference
    echo "$LOG_FILE" > "${CURRENT_LOG_RECORD}"

    echo "Starting submission-worker. Log file: $LOG_FILE"

    # Checkout and update code (adjust branches as needed)
    echo "Checkout to 'aws-changes' branch..." > "$LOG_FILE"
    git checkout aws-changes >> "$LOG_FILE" 2>&1
    echo "Pulling latest changes from origin/aws-changes..." >> "$LOG_FILE"
    git pull origin aws-changes >> "$LOG_FILE" 2>&1

    # Install/update Python requirements
    python3.9 -m pip install -U -r requirements/prod_2.txt -r requirements/worker_2.txt >> "$LOG_FILE" 2>&1

    # Start the worker in the background using nohup
    python3.9 -m $PYTHON_MODULE >> "$LOG_FILE" 2>&1 &
    echo "submission-worker started in background. Log file: $LOG_FILE"
}

# Function to stop the worker
stop_worker() {
    echo "Stopping submission-worker..."
    pkill -f "$PYTHON_MODULE" 2>/dev/null
    sleep 10;
    echo "submission-worker stopped (if it was running)."
}

# Function to show the log tail
show_logs() {
    # Default to 100 lines if not provided
    LINES=${1:-100}

    if [[ -f "${CURRENT_LOG_RECORD}" ]]; then
        LOG_FILE=$(cat "${CURRENT_LOG_RECORD}")
        if [[ -f "$LOG_FILE" ]]; then
            echo "Showing last ${LINES} lines of log file: $LOG_FILE"
            tail -n "$LINES" "$LOG_FILE"
        else
            echo "Log file ($LOG_FILE) not found."
        fi
    else
        echo "No current log file record found."
    fi
}

# Main option parsing
case "$1" in
    start)
        start_worker
        ;;
    stop)
        stop_worker
        ;;
    restart)
        stop_worker
        # Give a moment for the stop to take effect
        sleep 1
        start_worker
        ;;
    logs)
        # Optionally pass the number of lines (default is 100)
        show_logs "$2"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|logs [number_of_lines]}"
        exit 1
        ;;
esac
