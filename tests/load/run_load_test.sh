#!/bin/bash
set -e

HOST="${HOST:-http://localhost:8000}"
USERS="${USERS:-1000}"
SPAWN_RATE="${SPAWN_RATE:-16.67}"
RUN_TIME="${RUN_TIME:-5m}"
RESULTS_DIR="tests/load/results"

mkdir -p "$RESULTS_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="$RESULTS_DIR/report_${TIMESTAMP}.html"
CSV_PREFIX="$RESULTS_DIR/stats_${TIMESTAMP}"

echo "=========================================="
echo "1ai-social Load Test"
echo "=========================================="
echo "Host: $HOST"
echo "Users: $USERS"
echo "Spawn Rate: $SPAWN_RATE users/sec (60s ramp-up)"
echo "Run Time: $RUN_TIME"
echo "Results: $RESULTS_DIR"
echo "=========================================="
echo ""

if ! command -v locust &> /dev/null; then
    echo "ERROR: Locust is not installed."
    echo "Install with: pip install locust"
    exit 1
fi

if ! curl -s -o /dev/null -w "%{http_code}" "$HOST/health/live" | grep -q "200"; then
    echo "WARNING: Service at $HOST is not responding to health checks."
    echo "Make sure the service is running before starting the load test."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "Starting load test..."
echo ""

locust \
    -f tests/load/locustfile.py \
    --host="$HOST" \
    --users="$USERS" \
    --spawn-rate="$SPAWN_RATE" \
    --run-time="$RUN_TIME" \
    --headless \
    --html="$REPORT_FILE" \
    --csv="$CSV_PREFIX" \
    --loglevel=INFO

echo ""
echo "=========================================="
echo "Load Test Complete"
echo "=========================================="
echo "HTML Report: $REPORT_FILE"
echo "CSV Stats: ${CSV_PREFIX}_stats.csv"
echo "CSV Failures: ${CSV_PREFIX}_failures.csv"
echo "CSV Exceptions: ${CSV_PREFIX}_exceptions.csv"
echo "=========================================="
echo ""

if [ -f "${CSV_PREFIX}_stats.csv" ]; then
    echo "📊 Quick Summary:"
    echo ""
    
    awk -F',' 'NR==1 {
        for(i=1; i<=NF; i++) {
            if($i == "Name") name_col=i;
            if($i == "Request Count") req_col=i;
            if($i == "Failure Count") fail_col=i;
            if($i == "Median Response Time") p50_col=i;
            if($i == "95%ile") p95_col=i;
            if($i == "99%ile") p99_col=i;
            if($i == "Average Response Time") avg_col=i;
            if($i == "Requests/s") rps_col=i;
        }
    }
    NR>1 && $name_col == "Aggregated" {
        printf "  Total Requests: %s\n", $req_col;
        printf "  Total Failures: %s\n", $fail_col;
        printf "  Requests/sec: %s\n", $rps_col;
        printf "  Latency p50: %s ms\n", $p50_col;
        printf "  Latency p95: %s ms\n", $p95_col;
        printf "  Latency p99: %s ms\n", $p99_col;
        printf "  Average Latency: %s ms\n", $avg_col;
    }' "${CSV_PREFIX}_stats.csv"
    
    echo ""
    echo "Top 5 Endpoints by Request Count:"
    awk -F',' 'NR>1 && $1 != "Aggregated" {print $2, $1}' "${CSV_PREFIX}_stats.csv" | \
        sort -rn | head -5 | awk '{printf "  %s: %s requests\n", $2, $1}'
    
    echo ""
fi

echo "Open the HTML report for detailed analysis:"
echo "  open $REPORT_FILE"
echo ""
