#!/bin/bash

# Minimal evaluation script for PDF processing
# Usage: bash run_eval.sh pdfs/*.pdf outputs/

set -e

if [ $# -lt 2 ]; then
    echo "Usage: bash run_eval.sh pdfs/*.pdf outputs/"
    echo "Example: bash run_eval.sh data/dev/*.pdf output_batch/"
    exit 1
fi

# Get output directory (last argument)
OUTPUT_DIR="${!#}"
# Get PDF files (all arguments except last)
PDF_FILES=("${@:1:$#-1}")

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "Processing ${#PDF_FILES[@]} PDFs with parallelism..."
echo "Output directory: $OUTPUT_DIR"

# Start API server in background
echo "Starting FastAPI server..."
python -m src.main &
API_PID=$!

# Wait for server to start
sleep 5

# Check if server is running
if ! curl -s http://localhost:8000/docs > /dev/null; then
    echo "Error: API server failed to start"
    kill $API_PID 2>/dev/null || true
    exit 1
fi

echo "API server started (PID: $API_PID)"

# Process PDFs concurrently using background processes
echo "Submitting ${#PDF_FILES[@]} concurrent requests..."

START_TIME=$(date +%s)
PIDS=()
RESULTS_DIR=$(mktemp -d)

# Submit all requests in parallel
for i in "${!PDF_FILES[@]}"; do
    pdf="${PDF_FILES[$i]}"
    abs_path=$(realpath "$pdf")
    
    {
        echo "Processing: $(basename "$pdf")"
        PDF_START_TIME=$(date +%s.%N)
        
        RESPONSE=$(curl -s -X POST "http://localhost:8000/extract" \
            -H "Content-Type: application/json" \
            -d "{\"pdf_path\": \"$abs_path\"}")
        
        PDF_END_TIME=$(date +%s.%N)
        PDF_DURATION=$(echo "$PDF_END_TIME - $PDF_START_TIME" | bc)
        
        if echo "$RESPONSE" | jq -e '.status == "ok"' > /dev/null 2>&1; then
            OUTPUT_PATH=$(echo "$RESPONSE" | jq -r '.output_json_path')
            ASSETS_DIR=$(echo "$RESPONSE" | jq -r '.assets_dir')
            echo "SUCCESS:$(basename "$pdf"):$OUTPUT_PATH:$ASSETS_DIR:$PDF_DURATION" > "$RESULTS_DIR/result_$i"
        else
            ERROR=$(echo "$RESPONSE" | jq -r '.detail // "Unknown error"')
            echo "ERROR:$(basename "$pdf"):$ERROR:$PDF_DURATION" > "$RESULTS_DIR/result_$i"
        fi
    } &
    
    PIDS+=($!)
done

# Wait for all processes to complete
echo "Waiting for all PDFs to complete..."
for pid in "${PIDS[@]}"; do
    wait $pid
done

END_TIME=$(date +%s)
TOTAL_TIME=$((END_TIME - START_TIME))

# Collect and display results
echo ""
echo "=== RESULTS ==="
echo "Total processing time: ${TOTAL_TIME}s"

SUCCESS_COUNT=0
ERROR_COUNT=0

echo ""
echo "Processing results:"

for i in "${!PDF_FILES[@]}"; do
    if [ -f "$RESULTS_DIR/result_$i" ]; then
        RESULT=$(cat "$RESULTS_DIR/result_$i")
        if [[ $RESULT == SUCCESS:* ]]; then
            IFS=':' read -r status filename output_path assets_dir duration <<< "$RESULT"
            # Format duration to 2 decimal places
            formatted_duration=$(printf "%.2f" "$duration" 2>/dev/null || echo "$duration")
            echo "  ✓ $filename -> $output_path (${formatted_duration}s)"
            ((SUCCESS_COUNT++))
        else
            IFS=':' read -r status filename error duration <<< "$RESULT"
            # Format duration to 2 decimal places, handle cases where duration might be missing
            if [[ -n "$duration" ]]; then
                formatted_duration=$(printf "%.2f" "$duration" 2>/dev/null || echo "$duration")
                echo "  ✗ $filename: $error (${formatted_duration}s)"
            else
                echo "  ✗ $filename: $error"
            fi
            ((ERROR_COUNT++))
        fi
    else
        echo "  ✗ ${PDF_FILES[$i]}: No result file"
        ((ERROR_COUNT++))
    fi
done

echo ""
echo "Summary: $SUCCESS_COUNT successful, $ERROR_COUNT failed"

# Cleanup
rm -rf "$RESULTS_DIR"
echo ""
echo "Stopping API server..."
kill $API_PID 2>/dev/null || true
wait $API_PID 2>/dev/null || true

echo "Evaluation completed!"
