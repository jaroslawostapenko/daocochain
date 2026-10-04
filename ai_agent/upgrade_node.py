import os
import argparse
from substrateinterface import SubstrateInterface, Keypair

def main():
    parser = argparse.ArgumentParser()
    # Handle path flexibility depending on where script is run from
    default_wasm = "../daocochain-node/target/release/wbuild/solochain-template-runtime/solochain_template_runtime.compact.compressed.wasm"
    if not os.path.exists(default_wasm):
        alt_wasm = "daocochain-node/target/release/wbuild/solochain-template-runtime/solochain_template_runtime.compact.compressed.wasm"
        if os.path.exists(alt_wasm):
            default_wasm = alt_wasm

    parser.add_argument("--wasm-path", default=default_wasm)
    parser.add_argument("--url", default="ws://127.0.0.1:9944")
    args = parser.parse_args()

    if not os.path.exists(args.wasm_path):
        print(f"Error: Wasm file not found at {args.wasm_path}")
        return

    # 1. Connect to substrate
    print(f"Connecting to Substrate node at {args.url}...")
    try:
        substrate = SubstrateInterface(url=args.url)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    # 2. Keypairs for Alice, Bob, Charlie
    alice = Keypair.create_from_uri('//Alice')
    bob = Keypair.create_from_uri('//Bob')
    charlie = Keypair.create_from_uri('//Charlie')

    # Sort signatories (public keys)
    signatories = sorted([alice.ss58_address, bob.ss58_address, charlie.ss58_address])
    threshold = 2

    print(f"Signatories: {signatories}")
    multisig_address = substrate.generate_multisig_account(signatories, threshold)
    print(f"Multisig address (Admin): {multisig_address}")

    # 3. Read Wasm file
    print(f"Reading Wasm blob from {args.wasm_path}...")
    with open(args.wasm_path, "rb") as f:
        wasm_blob = f.read()

    # 4. Construct System.set_code call
    print("Constructing System.set_code call...")
    set_code_call = substrate.compose_call(
        call_module='System',
        call_function='set_code',
        call_params={
            'code': '0x' + wasm_blob.hex()
        }
    )

    # 5. Construct Sudo call
    print("Constructing Sudo.sudo_unchecked_weight call...")
    sudo_call = substrate.compose_call(
        call_module='Sudo',
        call_function='sudo_unchecked_weight',
        call_params={
            'call': set_code_call.value,
            'weight': {'ref_time': 0, 'proof_size': 0}
        }
    )

    call_hash = f"0x{sudo_call.call_hash.hex()}"
    print(f"Sudo Call generated with hash: {call_hash}")

    # 6. Alice approves
    print("Step 1: Alice is approving as multi...")
    alice_other_signatories = [s for s in signatories if s != alice.ss58_address]

    approve_call = substrate.compose_call(
        call_module='Multisig',
        call_function='approve_as_multi',
        call_params={
            'threshold': threshold,
            'other_signatories': alice_other_signatories,
            'maybe_timepoint': None,
            'call_hash': call_hash,
            'max_weight': {'ref_time': 1_000_000_000, 'proof_size': 1_000_000}
        }
    )

    extrinsic = substrate.create_signed_extrinsic(call=approve_call, keypair=alice)
    try:
        receipt = substrate.submit_extrinsic(extrinsic, wait_for_inclusion=True)
        if not receipt.is_success:
            print(f"Alice approval failed. Error message: {receipt.error_message}")
            return
        print("Alice approval successful!")
    except Exception as e:
        print(f"Failed to submit Alice's transaction: {e}")
        return

    # Find the timepoint of Alice's approval
    print("Querying multisig storage to find timepoint...")
    multisig_info = substrate.query(
        module='Multisig',
        storage_function='Multisigs',
        params=[multisig_address, call_hash]
    )

    if multisig_info is None or multisig_info.value is None:
        print("Failed to find multisig info on-chain. Maybe it executed already or failed?")
        return

    timepoint = multisig_info.value['when']
    print(f"Timepoint found: {timepoint}")

    # 7. Bob executes
    print("Step 2: Bob is executing as multi...")
    bob_other_signatories = [s for s in signatories if s != bob.ss58_address]

    as_multi_call = substrate.compose_call(
        call_module='Multisig',
        call_function='as_multi',
        call_params={
            'threshold': threshold,
            'other_signatories': bob_other_signatories,
            'maybe_timepoint': timepoint,
            'call': sudo_call.value,
            'max_weight': {'ref_time': 10_000_000_000, 'proof_size': 10_000_000}
        }
    )

    extrinsic2 = substrate.create_signed_extrinsic(call=as_multi_call, keypair=bob)
    try:
        receipt2 = substrate.submit_extrinsic(extrinsic2, wait_for_inclusion=True)
        if not receipt2.is_success:
            print(f"Bob execution failed. Error message: {receipt2.error_message}")
            return
        print("Bob execution successful! The runtime has been upgraded.")
    except Exception as e:
        print(f"Failed to submit Bob's transaction: {e}")
        return

if __name__ == '__main__':
    main()
