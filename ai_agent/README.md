# Daocochain AI Agent (Milestone 1.2)

This directory contains the Python scripts to automate the Single-AI Developer Loop.

## Setup

1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Set your OpenAI API key in a `.env` file (if you are using OpenAI for the LLM):
   ```
   OPENAI_API_KEY=your_key_here
   ```

## Running the Agent

Ensure your local Substrate node is running (`cargo run --release -- --dev`).

Then, run the agent:

```bash
python agent.py
```

What the agent does:
1. Reads `daocochain-node/runtime/src/lib.rs`.
2. Prompts the LLM to modify the `EXISTENTIAL_DEPOSIT` variable.
3. Overwrites `lib.rs` with the updated code.
4. Runs `cargo build --release` to compile the new Substrate runtime to Wasm.
5. Invokes `upgrade_node.py`, which submits a multisig transaction (Alice and Bob) to perform an on-chain runtime upgrade (`System.set_code`) via Sudo.
