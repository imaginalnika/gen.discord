#!/bin/zsh

# Defaults
ASPECT="portrait"
LORA_STRENGTH="0.8"
ENHANCE=false
WORKFLOW_JSON=""
OUTPUT_FILE=""
NUM_IMAGES=4

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
    -n|--number)
      NUM_IMAGES="$2"
      shift 2
      ;;
    *)
      PROMPT="$1"
      shift
      ;;
  esac
done

if [ -z "$PROMPT" ]; then
  echo "Usage: $0 [-a aspect] [-s strength] [-e] [-w workflow.json] [-o output.png] [-n number] 'prompt'"
  echo "  -a, --aspect: portrait (960x1920), landscape (1920x960), square (1280x1280) [default: portrait]"
  echo "  -s, --strength: 0.0-1.0 [default: 0.8]"
  echo "  -e, --enhance: enable prompt enhancement [default: disabled]"
  echo "  -w, --workflow: workflow JSON file [default: interactive selection]"
  echo "  -o, --output: output filename [default: {workflow_name}.png]"
  echo "  -n, --number: number of images to generate [default: 4]"
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

# Generate random seeds
SEED1=$(( ( RANDOM << 30 | RANDOM << 15 | RANDOM ) ))
SEED2=$(( ( RANDOM << 30 | RANDOM << 15 | RANDOM ) ))

echo "Using seeds: $SEED1, $SEED2"

# Queue the prompt with custom parameters
RESPONSE=$(jq --arg p "$PROMPT" \
              --argjson w "$WIDTH" \
              --argjson h "$HEIGHT" \
              --argjson s "$LORA_STRENGTH" \
              --argjson seed1 "$SEED1" \
              --argjson seed2 "$SEED2" \
              --argjson batch "$NUM_IMAGES" \
              '.["434"].inputs.text1 = $p | .["129"].inputs.width = $w | .["129"].inputs.height = $h | .["129"].inputs.batch_size = $batch | .["135"].inputs.lora_2.strength = $s | .["136"].inputs.seed = $seed1 | .["160"].inputs.seed = $seed2' \
              "$WORKFLOW_JSON" | jq -n --slurpfile w /dev/stdin '{prompt: $w[0]}' | curl -s -X POST -H "Content-Type: application/json" -d @- https://wktd28ejiizsa2-3000.proxy.runpod.net/prompt)

PROMPT_ID=$(echo $RESPONSE | jq -r '.prompt_id')
echo "Queued: $PROMPT_ID"

# Poll until complete
while true; do
  STATUS=$(curl -s https://wktd28ejiizsa2-3000.proxy.runpod.net/history/$PROMPT_ID)
  
  if echo $STATUS | jq -e '.["'$PROMPT_ID'"].status.completed' > /dev/null 2>&1; then
    echo "Complete!"

    # Get number of images
    IMAGE_COUNT=$(echo $STATUS | jq -r '.["'$PROMPT_ID'"].outputs."157".images | length')

    # Download each image
    for i in $(seq 0 $(($IMAGE_COUNT - 1))); do
      FILENAME=$(echo $STATUS | jq -r '.["'$PROMPT_ID'"].outputs."157".images['$i'].filename')
      SUBFOLDER=$(echo $STATUS | jq -r '.["'$PROMPT_ID'"].outputs."157".images['$i'].subfolder')

      # Generate output filename
      if [ $IMAGE_COUNT -eq 1 ]; then
        OUTPUT="${OUTPUT_FILE}"
      else
        # Remove .png extension and add index
        BASE="${OUTPUT_FILE%.png}"
        OUTPUT="${BASE}_$(printf '%03d' $((i+1))).png"
      fi

      # Download
      curl "https://wktd28ejiizsa2-3000.proxy.runpod.net/view?filename=$FILENAME&subfolder=$SUBFOLDER&type=output" -o "$OUTPUT"
      echo "Saved to $OUTPUT"
    done

    break
  fi
  
  echo "Still generating..."
  sleep 2
done
