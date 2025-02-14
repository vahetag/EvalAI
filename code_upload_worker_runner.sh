#!/bin/bash
# code_upload_worker_runner.sh
# Usage:
#   ./code_upload_worker_runner.sh start
#   ./code_upload_worker_runner.sh stop
#   ./code_upload_worker_runner.sh restart
#   ./code_upload_worker_runner.sh logs [number_of_lines | -f | -f -n number_of_lines]

# Load environment variables
set -a; . docker/prod_self/docker.env; set +a
set -a; . docker/prod_self/docker_code_upload_worker.env; set +a

# Configuration variables
PYTHON_SCRIPT="./scripts/workers/code_upload_submission_worker.py"
LOG_DIR="worker_logs"
LOG_SUBDIR="code_upload_worker"
LOG_FILE_PREFIX="v"
CURRENT_LOG_RECORD="${LOG_DIR}/${LOG_SUBDIR}/current_log_file_name.txt"
RUN_COMMAND="python3.9 $PYTHON_SCRIPT"

# Check for required commands
check_dependencies() {
    for cmd in git python3.9 tail; do
        if ! command -v $cmd &>/dev/null; then
            echo "$cmd is required but not installed. Aborting."
            exit 1
        fi
    done
}

# Function to check if the worker is already running
is_worker_running() {
    pgrep -f "$RUN_COMMAND" &>/dev/null
}

# Function to start the worker
start_worker() {
    if is_worker_running; then
        echo "Worker is already running. Aborting start."
        exit 1
    fi

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

    echo "Starting code-upload-worker. Log file: $LOG_FILE"

    # Checkout and update code (adjust branches as needed)
    echo "Checking out 'aws-changes' branch..." > "$LOG_FILE"
    git checkout aws-changes >> "$LOG_FILE" 2>&1
    echo "Pulling latest changes from origin/aws-changes..." >> "$LOG_FILE"
    git pull origin aws-changes >> "$LOG_FILE" 2>&1

    # Install/update Python requirements
    python3.9 -m pip install -U -r requirements/code_upload_worker.txt >> "$LOG_FILE" 2>&1

    # Start the worker in the background using nohup
    nohup $RUN_COMMAND >> "$LOG_FILE" 2>&1 &
    echo "code-upload-worker started in background. Log file: $LOG_FILE"
}

# Function to stop the worker
stop_worker() {
    echo "Stopping code-upload-worker..."

    while pid=$(pgrep -f "$RUN_COMMAND"); [ -n "$pid" ]; do
        kill -15 "$pid" 2>/dev/null
        sleep 20
    done
    echo "code-upload-worker stopped (if it was running)."
}

# Function to show the log tail
show_logs() {
    if [[ -f "${CURRENT_LOG_RECORD}" ]]; then
        LOG_FILE=$(cat "${CURRENT_LOG_RECORD}")
        if [[ -f "$LOG_FILE" ]]; then
            if [[ "$1" == "-f" && "$2" == "-n" && "$3" =~ ^[0-9]+$ ]]; then
                echo "Following log file: $LOG_FILE with last $3 lines"
                tail -f -n "$3" "$LOG_FILE"
            elif [[ "$1" == "-f" ]]; then
                echo "Following log file: $LOG_FILE"
                tail -f "$LOG_FILE"
            elif [[ "$1" =~ ^[0-9]+$ ]]; then
                echo "Showing last ${1} lines of log file: $LOG_FILE"
                tail -n "$1" "$LOG_FILE"
            else
                echo "Showing last 100 lines of log file: $LOG_FILE"
                tail -n 100 "$LOG_FILE"
            fi
        else
            echo "Log file ($LOG_FILE) not found."
        fi
    else
        echo "No current log file record found."
    fi
}

# # Function to handle graceful termination
# cleanup() {
#     echo "Cleaning up..."
#     stop_worker
# }

# # Trap to catch Ctrl+C and handle cleanup
# trap cleanup INT TERM

# Check for dependencies
check_dependencies

# Main option parsing
case "$1" in
    start)
        start_worker
        ;;
    stop)
        if is_worker_running; then
            stop_worker
        fi
        ;;
    restart)
        if is_worker_running; then
            stop_worker
        fi
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
