## Starting the LLM
ollama serve
ollama pull qwen2.5:7b-instruct
ollama pull qwen2.5-coder:7b-instruct

## Use the Quantized Models
Quantization	General Qwen2.5 7B	Coder Qwen2.5 7B	Recommendation
Q2_K	        ~3.0 GB	~3.0 GB	Lowest storage requirements
Q3_K_M	        ~3.8 GB	~3.8 GB	Lower memory usage
Q4_K_M	        ~4.7 GB	~4.7 GB	Best starting point for most users
Q5_K_M	        ~5.4 GB	~5.4 GB	Higher quality, more memory
Q6_K	        ~6.3 GB	~6.3 GB	Higher precision
Q8_0	        ~8.1 GB	~8.1 GB	Near-full-precision quantization

## Pull the quantized model
ollama pull qwen2.5:7b-instruct-q4_K_M
ollama pull qwen2.5-coder:7b-instruct-q4_K_M

## Run the quantized model
ollama run qwen2.5:7b-instruct-q4_K_M
ollama run qwen2.5-coder:7b-instruct-q4_K_M


## Testing each module separately
python -m graphs.requirements
python -m graphs.er
python -m graphs.states
python -m graphs.usecases
python -m graphs.objects
python -m graphs.sequence

## Run all stages at once
python -m graphs.pipeline

