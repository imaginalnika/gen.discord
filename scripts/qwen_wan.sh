#!/bin/zsh

# Defaults
ASPECT="portrait"
LORA_STRENGTH="0.8"
ENHANCE=false
WORKFLOW_JSON=""
OUTPUT_FILE=""

# Parse flags
while [[ $# -gt 0 ]]; do
  case $1 in
    -a|--aspect)
      ASPECT="$2"
      shift 2
      ;;
    -s|--strength)
      LORA_STRENGTH="$2"
      shift 2
      ;;
    -e|--enhance)
      ENHANCE=true
      shift
      ;;
    -w|--workflow)
      WORKFLOW_JSON="$2"
      shift 2
      ;;
    -o|--output)
      OUTPUT_FILE="$2"
      shift 2
      ;;
    *)
      PROMPT="$1"
      shift
      ;;
  esac
done

if [ -z "$PROMPT" ]; then
  echo "Usage: $0 [-a aspect] [-s strength] [-e] [-w workflow.json] [-o output.png] 'prompt'"
  echo "  -a, --aspect: portrait (960x1920), landscape (1920x960), square (1280x1280) [default: portrait]"
  echo "  -s, --strength: 0.0-1.0 [default: 0.8]"
  echo "  -e, --enhance: enable prompt enhancement [default: disabled]"
  echo "  -w, --workflow: workflow JSON file [default: interactive selection]"
  echo "  -o, --output: output filename [default: {workflow_name}.png]"
  exit 1
fi

# Select workflow JSON if not provided
if [ -z "$WORKFLOW_JSON" ]; then
  SCRIPT_DIR="${0:a:h}"
  cd "$SCRIPT_DIR"

  # Find all JSON files
  JSON_FILES=(*.json(N))

  if [ ${#JSON_FILES[@]} -eq 0 ]; then
    echo "Error: No JSON workflow files found in $SCRIPT_DIR"
    exit 1
  elif [ ${#JSON_FILES[@]} -eq 1 ]; then
    WORKFLOW_JSON="${JSON_FILES[1]}"
    echo "Using workflow: $WORKFLOW_JSON"
  else
    echo "Select workflow:"
    select WORKFLOW_JSON in "${JSON_FILES[@]}"; do
      if [ -n "$WORKFLOW_JSON" ]; then
        echo "Selected: $WORKFLOW_JSON"
        break
      fi
    done
  fi
fi

# Set output filename based on workflow if not provided
if [ -z "$OUTPUT_FILE" ]; then
  OUTPUT_FILE="${WORKFLOW_JSON:r}.png"
fi

echo "Output will be saved to: $OUTPUT_FILE"

# Enhance prompt if enabled
if [ "$ENHANCE" = true ]; then
  echo "Enhancing prompt..."
  SCRIPT_DIR="${0:a:h}"
  echo "Script dir: $SCRIPT_DIR"
  echo "LLM script: $SCRIPT_DIR/llm.sh"

  if [ ! -f "$SCRIPT_DIR/llm.sh" ]; then
    echo "Error: llm.sh not found at $SCRIPT_DIR/llm.sh"
    echo "Enhancement failed, using original prompt"
  else
    ENHANCED=$(bash "$SCRIPT_DIR/llm.sh" "Convert this prompt into a detailed English image generation prompt. Prefix it with 'digital anime illustration of'. Be concise and focused on visual details only. Do not include any explanations, just output the enhanced prompt:

$PROMPT" 2>&1)
    EXIT_CODE=$?

    echo "LLM exit code: $EXIT_CODE"
    echo "LLM output: $ENHANCED"

    if [ $EXIT_CODE -eq 0 ] && [ -n "$ENHANCED" ]; then
      PROMPT="$ENHANCED"
      echo "Enhanced: $PROMPT"
    else
      echo "Enhancement failed, using original prompt"
    fi
  fi
fi

# Set dimensions based on aspect ratio
case $ASPECT in
  portrait)
    WIDTH=960
    HEIGHT=1920
    ;;
  landscape)
    WIDTH=1920
    HEIGHT=960
    ;;
  square)
    WIDTH=1280
    HEIGHT=1280
    ;;
  *)
    echo "Invalid aspect: $ASPECT"
    exit 1
    ;;
esac

# Queue the prompt with custom parameters
RESPONSE=$(jq --arg p "$PROMPT" \
              --argjson w "$WIDTH" \
              --argjson h "$HEIGHT" \
              --argjson s "$LORA_STRENGTH" \
              '.["434"].inputs.text1 = $p | .["129"].inputs.width = $w | .["129"].inputs.height = $h | .["135"].inputs.lora_2.strength = $s' \
              "$WORKFLOW_JSON" | jq -n --slurpfile w /dev/stdin '{prompt: $w[0]}' | curl -s -X POST -H "Content-Type: application/json" -d @- https://wktd28ejiizsa2-3000.proxy.runpod.net/prompt)

PROMPT_ID=$(echo $RESPONSE | jq -r '.prompt_id')
echo "Queued: $PROMPT_ID"

# Poll until complete
while true; do
  STATUS=$(curl -s https://wktd28ejiizsa2-3000.proxy.runpod.net/history/$PROMPT_ID)
  
  if echo $STATUS | jq -e '.["'$PROMPT_ID'"].status.completed' > /dev/null 2>&1; then
    echo "Complete!"
    
    # Get filename from outputs
    FILENAME=$(echo $STATUS | jq -r '.["'$PROMPT_ID'"].outputs."157".images[0].filename')
    SUBFOLDER=$(echo $STATUS | jq -r '.["'$PROMPT_ID'"].outputs."157".images[0].subfolder')
    
    # Download
    curl "https://wktd28ejiizsa2-3000.proxy.runpod.net/view?filename=$FILENAME&subfolder=$SUBFOLDER&type=output" -o "$OUTPUT_FILE"
    echo "Saved to $OUTPUT_FILE"
    break
  fi
  
  echo "Still generating..."
  sleep 2
done
