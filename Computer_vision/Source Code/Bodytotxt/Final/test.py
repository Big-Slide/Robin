import os
import yaml
import argparse
from pprint import pprint


def check_config(config_path, fix=False):
    """
    Check and optionally fix configuration files

    Args:
        config_path: Path to the configuration directory
        fix: Whether to fix issues automatically
    """
    print(f"Checking configuration in {config_path}")

    # List of config files to check
    config_files = [
        os.path.join(config_path, "conf-dev.yml"),
        os.path.join(config_path, "conf-prod.yml")
    ]

    for file_path in config_files:
        if not os.path.exists(file_path):
            print(f"⚠️  Config file not found: {file_path}")
            continue

        print(f"\nChecking {file_path}...")

        try:
            # Load the config
            with open(file_path, 'r') as f:
                config = yaml.safe_load(f)

            if not config:
                print(f"⚠️  Empty or invalid config file: {file_path}")
                continue

            # Check AIHIVE_ADDR
            if 'AIHIVE_ADDR' not in config:
                print(f"❌ Missing AIHIVE_ADDR in {file_path}")
                if fix:
                    config['AIHIVE_ADDR'] = "http://api.robin-co.com"  # Default value
                    print(f"  ✅ Added AIHIVE_ADDR: {config['AIHIVE_ADDR']}")
            else:
                print(f"  ✅ AIHIVE_ADDR: {config['AIHIVE_ADDR']}")

            # Check BASE_URL_FILE_LINK
            if 'BASE_URL_FILE_LINK' not in config:
                print(f"❌ Missing BASE_URL_FILE_LINK in {file_path}")

                # Determine default value based on dev/prod
                default_url = "http://localhost:11000" if "dev" in file_path else "http://192.168.0.161:11000"

                if fix:
                    config['BASE_URL_FILE_LINK'] = default_url
                    print(f"  ✅ Added BASE_URL_FILE_LINK: {config['BASE_URL_FILE_LINK']}")
            else:
                # Check if the port needs to be updated from 9000 to 11000
                if ":9000" in config['BASE_URL_FILE_LINK'] and fix:
                    old_url = config['BASE_URL_FILE_LINK']
                    config['BASE_URL_FILE_LINK'] = old_url.replace(":9000", ":11000")
                    print(f"  ✅ Updated BASE_URL_FILE_LINK: {old_url} -> {config['BASE_URL_FILE_LINK']}")
                else:
                    print(f"  ✅ BASE_URL_FILE_LINK: {config['BASE_URL_FILE_LINK']}")

            # Check QUEUE_CONNECTION
            if 'QUEUE_CONNECTION' not in config:
                print(f"❌ Missing QUEUE_CONNECTION in {file_path}")
                default_queue = "amqp://guest:guest@localhost/" if "dev" in file_path else "amqp://guest:guest@queue/"
                if fix:
                    config['QUEUE_CONNECTION'] = default_queue
                    print(f"  ✅ Added QUEUE_CONNECTION: {config['QUEUE_CONNECTION']}")
            else:
                print(f"  ✅ QUEUE_CONNECTION: {config['QUEUE_CONNECTION']}")

            # Save the updated config if fixes were applied
            if fix:
                with open(file_path, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)
                print(f"💾 Saved updated configuration to {file_path}")

        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")

    print("\nConfiguration check completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check and fix webhook configuration")
    parser.add_argument("--backend", default="backend/config", help="Path to backend config directory")
    parser.add_argument("--engine", default="engine/config", help="Path to engine config directory")
    parser.add_argument("--fix", action="store_true", help="Fix issues automatically")

    args = parser.parse_args()

    # Check backend config
    check_config(args.backend, args.fix)

    # Check engine config
    check_config(args.engine, args.fix)

    if args.fix:
        print("\n✅ Configuration has been checked and fixed. Please restart your services.")
    else:
        print("\n✅ Configuration check complete. Run with --fix to automatically fix issues.")