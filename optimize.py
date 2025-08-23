import os
import subprocess

def optimize_for_mac():
    """Mac-specific optimizations"""
    
    # Set environment variables for Metal acceleration
    os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    
    # Optimize Ollama for your RAM
    subprocess.run(['ollama', 'set', 'parameter', 'num_gpu', '1'])
    subprocess.run(['ollama', 'set', 'parameter', 'gpu_memory', '80000'])  # 80GB for model
    
    print("Optimizations applied!")

if __name__ == "__main__":
    optimize_for_mac()

