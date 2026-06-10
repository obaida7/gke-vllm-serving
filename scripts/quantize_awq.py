# quantize_awq.py
# Production script for 4-bit AWQ (Activation-aware Weight Quantization)
# AWQ is highly optimized for GPU inference engines like vLLM and TensorRT-LLM,
# providing a 4x memory footprint reduction with minimal perplexity degradation.

import os
import sys
from awq import AutoAWQForCausalLM
from transformers import AutoTokenizer

def main():
    # We use a lightweight model suitable for demonstration and fast execution
    model_id = "Qwen/Qwen2.5-1.5B-Instruct"
    quant_path = os.path.abspath("model-cache/Qwen2.5-1.5B-Instruct-AWQ")
    
    quant_config = {
        "zero_point": True,
        "q_group_size": 128,
        "w_bit": 4,
        "version": "GEMM"
    }
    
    print(f"=== Starting AWQ Quantization for {model_id} ===")
    print(f"Configuration: {quant_config}")
    
    # 1. Load Model and Tokenizer
    print("\nLoading model from Hugging Face (requires GPU and VRAM)...")
    try:
        model = AutoAWQForCausalLM.from_pretrained(
            model_id, 
            safetensors=True, 
            low_cpu_mem_usage=True
        )
        tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    except Exception as e:
        print(f"Failed to load model: {e}")
        print("\nNote: AutoAWQ quantization requires a CUDA-enabled GPU to run.")
        print("In your GKE/GCP environment, you can run this script on an n1-standard-4 VM with a T4 GPU.")
        sys.exit(1)

    # 2. Quantize Model (requires calibration dataset)
    print("\nStarting model quantization... This runs calibration to minimize quality loss.")
    model.quantize(
        tokenizer, 
        quant_config=quant_config
    )
    
    # 3. Save Quantized Model and Tokenizer
    print(f"\nSaving AWQ quantized model and configurations to: {quant_path}")
    os.makedirs(quant_path, exist_ok=True)
    model.save_quantized(quant_path)
    tokenizer.save_pretrained(quant_path)
    
    print("\n=== Quantization Complete! ===")
    print(f"AWQ model size: {os.path.getsize(os.path.join(quant_path, 'model.safetensors')) / (1024 * 1024):.2f} MB")
    print("This model is now ready to be deployed via vLLM with '--quantization awq'.")

if __name__ == "__main__":
    main()
