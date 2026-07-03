# Chain of Agents Implementation


![Chain of Agents](Screenshot%202025-01-29%20at%2015.05.34.png)

Chain of Agents (CoA) implementation in Python and Swift - A framework for long-context tasks using Large Language Models (LLMs).

## Overview

This repository implements the Chain-of-Agents framework as described in:

- [Chain of Agents: Large language models collaborating on long-context tasks](https://research.google/blog/chain-of-agents-large-language-models-collaborating-on-long-context-tasks/) (Google Research Blog)
- [Chain of Agents Paper](https://openreview.net/pdf?id=LuCLf4BJsr) (Research Paper)

The Chain of Agents framework enables efficient processing of long-context tasks by:

1. Breaking down large inputs into manageable chunks
2. Using worker agents to process individual chunks
3. Employing a manager agent to synthesize results

## Features

- Support for PDF document analysis
- Configurable chunk sizes for processing
- Real-time progress tracking
- Streaming responses from both worker and manager agents
- Clean macOS native interface
- Dual processing modes:
  - Cloud-based processing using Together AI's LLaMA models
  - On-device processing using MLX framework
- Support for offline inference with MLX

## Installation

```bash
git clone https://github.com/rudrankriyam/chain-of-agents.git
cd chain-of-agents
pip install -r requirements.txt
```

### Prerequisites

- Python 3.x
- Xcode 15+ (for macOS app)
- Together API key (sign up at [Together.ai](https://together.ai))


## Usage

### Command Line Version

1. Create a `.env` file in the root directory and add your Together API key:

```bash
echo "TOGETHER_API_KEY=your_api_key_here" >> .env
```

2. Run the example script:

```bash
./run.sh
```

This will:
- Set up a Python virtual environment
- Install required dependencies
- Process a sample PDF document using the Chain of Agents framework

### macOS App

1. Start the API server:

```bash
./run_api.sh
```
This will:
- Activate the Python virtual environment
- Start the API server that the macOS app communicates with
- The server will run on `localhost:8000`

2. Open the Xcode project:

```bash
open ChainOfAgents.xcodeproj
```

3. Build and run the app (⌘R)

#### Processing Modes

- **Cloud Processing**: Uses Together AI's hosted models through the API server
- **On-Device Processing**: Uses MLX framework for local inference
  - Automatically downloads and caches the required model
  - No internet connection required after initial model download
  - Lower latency but may have different performance characteristics

The macOS app provides:
- PDF document selection
- Custom query input
- Real-time processing visualization
- Worker agent progress tracking
- Final synthesis display
- Toggle between cloud and on-device processing

## Models

### Cloud Processing
Uses Together AI's hosted models:
- Worker model: `meta-llama/Llama-3.3-70B-Instruct-Turbo-Free`
- Manager model: `meta-llama/Llama-3.3-70B-Instruct-Turbo-Free`

### On-Device Processing
Uses MLX-optimized models:
- Default model: `Llama 3.2 3B` (quantized 4-bit version, `ModelRegistry.llama3_2_3B_4bit`)
- Automatically handles model downloading and caching
- Optimized for Apple Silicon processors

## Technical Details

- Built with SwiftUI for the macOS interface
- Uses MLX framework for efficient on-device inference
- Implements Server-Sent Events (SSE) for real-time progress updates
- Processes document chunks sequentially, passing context between workers
- Automatic memory management for large documents

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Citation

```bibtex
@article{zhang2024chain,
    title={Chain of Agents: Large Language Models Collaborating on Long-Context Tasks},
    author={Zhang, Yusen and Sun, Ruoxi and Chen, Yanfei and Pfister, Tomas and Zhang, Rui and Arık, Sercan Ö.},
    journal={arXiv preprint arXiv:2404.08392},
    year={2024}
}
```

[![Star History Chart](https://api.star-history.com/svg?repos=rudrankriyam/Chain-of-Agents&type=Date)](https://star-history.com/#rudrankriyam/Chain-of-Agents&Date)
