import argparse
import subprocess
import os
import sys
import json
import hashlib
from datetime import datetime

def check_git_clean(repo_path):
    try:
        # Check if there are any uncommitted changes over tracked files
        status = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=repo_path, stderr=subprocess.DEVNULL).strip()
        return len(status) == 0
    except subprocess.CalledProcessError:
        return False

def get_git_hash(repo_path):
    try:
        return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=repo_path).strip().decode('utf-8')
    except subprocess.CalledProcessError:
        return "nohash"

def auto_commit(repo_path):
    print(f"[{repo_path}] Auto-committing changes...")
    subprocess.run(['git', 'add', '.'], cwd=repo_path, check=True)
    subprocess.run(['git', 'commit', '-m', 'WIP auto-commit'], cwd=repo_path, check=True)

def hash_params(params_dict):
    j = json.dumps(params_dict, sort_keys=True)
    return hashlib.md5(j.encode('utf-8')).hexdigest()[:8]

def load_params(proj_dir):

    try:
        cmd_code = "import sys, json; sys.path.insert(0, '.'); import params; print(json.dumps(params.PARAMS))"
        cmd = ["uv", "run", "python", "-c", cmd_code]
        result = subprocess.run(cmd, cwd=proj_dir, capture_output=True, text=True, check=True)
        params_val = json.loads(result.stdout)
        if isinstance(params_val, list):
            if len(params_val) > 0:
                return params_val
            else:
                print(f"Warning: PARAMS list in {proj_dir}/params.py is empty. Using empty parameters.")
                return [{}]
        elif isinstance(params_val, dict):
            return [params_val]
        else:
            print(f"Error: PARAMS in params.py must be a dict or a list of dicts.")
    except subprocess.CalledProcessError as e:
        print(f"Error loading params.py from {proj_dir}:\n{e.stderr}")
    except json.JSONDecodeError as e:
        print(f"Error parsing PARAMS from {proj_dir}/params.py (must be JSON serializable):\n{e}")
    except Exception as e:
        print(f"Warning: Could not load PARAMS from {proj_dir}/params.py: {e}")
    
    sys.exit(1)


def main():
    default_projects = os.environ.get("PENPAL_PROJECT_DIR", "./projects")
    default_gallery = os.environ.get("PENPAL_GALLERY_DIR", "./gallery")

    parser = argparse.ArgumentParser(description="Run a creative coding sketch")
    parser.add_argument("project", help="Name of the project (e.g. 001_hello_world)")
    parser.add_argument("--project-dir", default=default_projects, help="Path to projects directory")
    parser.add_argument("--gallery-dir", default=default_gallery, help="Path to gallery directory")
    parser.add_argument("--dev", action="store_true", help="Run in dev mode (skips strict git checks, outputs to test_outputs/)")
    parser.add_argument("--auto-commit", action="store_true", help="Auto-commit before running if repo is dirty")
    parser.add_argument("--params", type=str, help="JSON string of parameters to use (overrides params files)")
    parser.add_argument("--param-file", type=str, help="Name of param file in experiments folder to run (resolves .py or .json)")
    
    args = parser.parse_args()
    PROJECTS_DIR = os.path.abspath(args.project_dir)
    GALLERY_DIR = os.path.abspath(args.gallery_dir)
    
    proj_name = args.project
    proj_dir = os.path.join(PROJECTS_DIR, proj_name)

    if not os.path.isdir(proj_dir):
        print(f"Error: {proj_dir} is not a directory.")
        sys.exit(1)

    workspace_dir = os.path.dirname(PROJECTS_DIR)
    
    # 1. Git Handling (Skip if dev)
    git_hash = "dev"
    if not args.dev:
        if not os.path.exists(os.path.join(proj_dir, '.git')):
            print(f"Error: {proj_dir} is not a Git repository. Every project must be its own Git repo.")
            sys.exit(1)
            
        if not check_git_clean(proj_dir):
            if args.auto_commit:
                auto_commit(proj_dir)
            else:
                print(f"Error: Project '{args.project}' has uncommitted changes.")
                print("Commit your changes or use --auto-commit or pass --dev.")
                sys.exit(1)
        git_hash = get_git_hash(proj_dir)

    # 2. Load Parameters
    params_list = [{}]
    if args.params:
        # Explicit params provided via --params
        try:
            params_val = json.loads(args.params)
            if isinstance(params_val, list):
                if len(params_val) > 0:
                    params_list = params_val
                else:
                    print(f"Warning: --params list is empty. Using empty parameters.")
            elif isinstance(params_val, dict):
                params_list = [params_val]
            else:
                print(f"Error: --params must be a JSON dict or a list of dicts.")
                sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error parsing --params JSON: {e}")
            sys.exit(1)
    else:
        # Resolution logic: `--param-file` -> `default.py` -> `default.json` -> `example.json`
        experiments_dir = os.path.join(workspace_dir, "experiments", proj_name)
        resolved_path = None
        is_python = False

        # Helper to check files
        def check_path(p):
            if os.path.exists(p):
                return p
            return None

        # 1. Explicit --param-file
        if hasattr(args, 'param_file') and args.param_file:
            pf = args.param_file
            # If it has an extension, use it strictly
            if pf.endswith('.py') or pf.endswith('.json'):
                candidate = os.path.join(experiments_dir, pf)
                if check_path(candidate):
                    resolved_path = candidate
                    is_python = candidate.endswith('.py')
            else:
                # Try .py then .json
                candidate_py = os.path.join(experiments_dir, f"{pf}.py")
                candidate_json = os.path.join(experiments_dir, f"{pf}.json")
                if check_path(candidate_py):
                    resolved_path = candidate_py
                    is_python = True
                elif check_path(candidate_json):
                    resolved_path = candidate_json
                    is_python = False
            
            if not resolved_path:
                print(f"Error: Could not resolve param file '{pf}' in {experiments_dir}")
                sys.exit(1)
        else:
            # Fallbacks
            candidate_default_py = os.path.join(experiments_dir, "default.py")
            candidate_default_json = os.path.join(experiments_dir, "default.json")
            candidate_example = os.path.join(proj_dir, "example.json")

            if check_path(candidate_default_py):
                resolved_path = candidate_default_py
                is_python = True
            elif check_path(candidate_default_json):
                resolved_path = candidate_default_json
                is_python = False
            elif check_path(candidate_example):
                resolved_path = candidate_example
                is_python = False

        if resolved_path:
            print(f"Using parameters from: {resolved_path}")
            if is_python:
                # Need to load via subprocess, but we don't have python execution logic easily separable here yet
                # We will adapt load_params
                try:
                    # Execute in the context of the project using its uv environment
                    # We inject the resolved_path directly into the python script to extract PARAMS
                    script_dir = os.path.dirname(resolved_path)
                    script_name = os.path.splitext(os.path.basename(resolved_path))[0]
                    cmd_code = f"import sys, json; sys.path.insert(0, '{script_dir}'); import {script_name}; print(json.dumps({script_name}.PARAMS))"
                    cmd = ["uv", "run", "python", "-c", cmd_code]
                    result = subprocess.run(cmd, cwd=proj_dir, capture_output=True, text=True, check=True)
                    params_val = json.loads(result.stdout)
                    
                    if isinstance(params_val, list):
                        if len(params_val) > 0:
                            params_list = params_val
                        else:
                            print(f"Warning: PARAMS list in {resolved_path} is empty. Using empty parameters.")
                    elif isinstance(params_val, dict):
                        params_list = [params_val]
                    else:
                        print(f"Error: PARAMS in {resolved_path} must be a dict or a list of dicts.")
                        sys.exit(1)
                except subprocess.CalledProcessError as e:
                    print(f"Error loading {resolved_path}:\n{e.stderr}")
                    sys.exit(1)
                except Exception as e:
                    print(f"Error parsing PARAMS from {resolved_path}:\n{e}")
                    sys.exit(1)
            else:
                try:
                    with open(resolved_path, "r") as f:
                        params_val = json.load(f)
                    if isinstance(params_val, list):
                        if len(params_val) > 0:
                            params_list = params_val
                    elif isinstance(params_val, dict):
                        params_list = [params_val]
                except Exception as e:
                    print(f"Error loading json {resolved_path}: {e}")
                    sys.exit(1)
        else:
            print("No parameter files found. Using empty parameters.")

    # 3. Execution Setup
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    
    main_path = os.path.join(proj_dir, "main.py")
    if not os.path.exists(main_path):
        print(f"Error: {main_path} not found.")
        sys.exit(1)



    print(f"Running {args.project} ({len(params_list)} configurations)...")

    for i, params in enumerate(params_list):
        p_hash = hash_params(params)
        
        # 4. Output Directory Setup
        outputs_root = os.path.join(GALLERY_DIR, proj_name)
        if args.dev:
            out_dir = os.path.join(outputs_root, "test", timestamp)
            base_filename = p_hash
        else:
            out_dir = os.path.join(outputs_root, "svg", git_hash)
            base_filename = f"{timestamp}_{p_hash}"
    
        os.makedirs(out_dir, exist_ok=True)
        
        svg_path = os.path.join(out_dir, f"{base_filename}.svg")
        json_path = os.path.join(out_dir, f"{base_filename}.json")

        # 5. Save JSON metadata
        metadata = {
            "timestamp": timestamp,
            "git_hash": git_hash,
            "params_hash": p_hash,
            "params": params,
            "dev_mode": args.dev
        }
        with open(json_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        # 6. Execute Sketch
        print(f"  [{i+1}/{len(params_list)}] Hash {p_hash} -> {svg_path}")
        
        cmd_code = f"""
import sys
import json
sys.path.insert(0, '.')
import main
params = json.loads(sys.argv[1])
output_path = sys.argv[2]
if not hasattr(main, 'run'):
    print("Error: main.py must define a 'run(params, output_path)' function.")
    sys.exit(1)
main.run(params, output_path)
"""
        cmd = ["uv", "run", "python", "-c", cmd_code, json.dumps(params), svg_path]
        
        try:
            subprocess.run(cmd, cwd=proj_dir, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running sketch (exit code {e.returncode}):")
            if e.stdout:
                print(f"--- STDOUT ---\n{e.stdout}")
            if e.stderr:
                print(f"--- STDERR ---\n{e.stderr}")
            sys.exit(1)

    print("Success!")

if __name__ == "__main__":
    main()
