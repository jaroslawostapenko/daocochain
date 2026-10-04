import os
import subprocess
import re
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

load_dotenv()

# The system prompt to instruct the LLM on how to modify the file.
SYSTEM_PROMPT = """You are an expert Rust blockchain developer working with Substrate.
Your task is to modify the `EXISTENTIAL_DEPOSIT` parameter in a provided Rust file.
You should ONLY return the full file content of the modified file. Do not wrap it in markdown block. Do not add any explanation."""

def main():
    print("Starting AI Developer Loop...")

    llm = ChatOpenAI(model="gpt-4", temperature=0)

    # 1. Read the Rust file
    lib_path = "../daocochain-node/runtime/src/lib.rs"
    if not os.path.exists(lib_path):
        # We might be running from root
        lib_path = "daocochain-node/runtime/src/lib.rs"

    print(f"Reading file: {lib_path}")
    with open(lib_path, "r") as f:
        file_content = f.read()

    # 2. Prompt LLM
    print("Prompting LLM to modify EXISTENTIAL_DEPOSIT...")
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Modify the EXISTENTIAL_DEPOSIT in this file to be `MILLI_UNIT * 2;` (from just `MILLI_UNIT;` if it exists, or whatever it is currently). Output the entire file exactly as it should be.\n\nFile:\n{file_content}")
    ]

    response = llm.invoke(messages)
    new_file_content = response.content

    # Optional regex to strip markdown blocks if the LLM ignores instructions
    match = re.search(r"```(?:rust)?\s*(.*?)\s*```", new_file_content, re.DOTALL)
    if match:
        new_file_content = match.group(1)

    # 3. Write back
    print("Writing modified file back...")
    with open(lib_path, "w") as f:
        f.write(new_file_content)

    # 4. Compile Wasm
    print("Compiling Substrate runtime to Wasm...")
    try:
        # Assuming we are running from project root or ai_agent directory
        project_dir = "daocochain-node" if os.path.exists("daocochain-node") else "../daocochain-node"

        subprocess.run(
            ["cargo", "build", "--release"],
            cwd=project_dir,
            check=True
        )
        print("Compilation successful.")
    except subprocess.CalledProcessError as e:
        print(f"Compilation failed: {e}")
        return

    # 5. Run upgrade script
    print("Triggering the on-chain upgrade via multisig...")
    try:
        script_path = "ai_agent/upgrade_node.py" if os.path.exists("ai_agent/upgrade_node.py") else "upgrade_node.py"
        subprocess.run(["python", script_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Upgrade script failed: {e}")
        return

    print("AI Developer Loop completed successfully!")

if __name__ == '__main__':
    main()
