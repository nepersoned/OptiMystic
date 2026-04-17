#!/usr/bin/env python3
"""
Deploy OptiMystic API to Google Cloud Run
Uses google-cloud-run and google-cloud-build Python libraries
"""
import argparse
import os
import sys
import subprocess
import json
from pathlib import Path

# Windows-specific gcloud path
GCLOUD_PATH = r"C:\Users\kevin\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

def run_cmd(cmd, use_gcloud_path=False, capture=True, **kwargs):
    """Run shell command and return output"""
    # If command starts with 'gcloud', replace with full path on Windows
    if use_gcloud_path and cmd.startswith("gcloud "):
        cmd = f'"{GCLOUD_PATH}" {cmd[7:]}'
    
    print(f"🔧 Running: {cmd}")
    sys.stdout.flush()
    
    if capture:
        result = subprocess.run(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True, encoding="utf-8", errors="replace"
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        if stdout:
            print(stdout)
        if result.returncode != 0:
            if stderr:
                print(f"⚠ stderr: {stderr}")
            if "ERROR" in stderr or result.returncode != 0:
                raise RuntimeError(f"Command failed (exit {result.returncode}): {cmd}\n{stderr}")
        return stdout
    else:
        # Stream output directly (for long-running commands like builds)
        result = subprocess.run(cmd, shell=True, stdin=subprocess.DEVNULL)
        if result.returncode != 0:
            raise RuntimeError(f"Command failed (exit {result.returncode}): {cmd}")
        return ""

def deploy_cloud_run(
    project_id: str,
    region: str = "asia-northeast3",
    service_name: str = "optimystic-api",
    repository: str = "optimystic",
    image_name: str = "api",
    image_tag: str = "latest",
    env_file: str = "deploy/gcp/.env.app",
    allow_unauthenticated: bool = False
):
    """Deploy application to Google Cloud Run"""
    
    print(f"""
╔═══════════════════════════════════════════════╗
║  OptiMystic API → Google Cloud Run Deployment  ║
╚═══════════════════════════════════════════════╝

Configuration:
  Project ID:          {project_id}
  Region:              {region}
  Service Name:        {service_name}
  Repository:          {repository}
  Image:               {image_name}:{image_tag}
  Env File:            {env_file}
  Allow Unauthenticated: {allow_unauthenticated}
""")
    
    # Step 1: Verify gcloud is configured
    print("\n[1/6] Verifying gcloud configuration...")
    try:
        current_project = run_cmd(f'gcloud config set project {project_id}', use_gcloud_path=True)
        print(f"✓ Project set to: {project_id}")
    except Exception as e:
        print(f"⚠ Could not set project: {e}")
        raise
    
    # Step 2: Enable required APIs
    print("\n[2/6] Enabling required Google Cloud APIs...")
    apis = [
        "run.googleapis.com",
        "artifactregistry.googleapis.com",
        "cloudbuild.googleapis.com"
    ]
    run_cmd(
        f'gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com --project={project_id}',
        use_gcloud_path=True, capture=False
    )
    print(f"✓ APIs enabled")
    
    # Step 3: Ensure Artifact Registry repository exists
    print("\n[3/6] Ensuring Artifact Registry repository...")
    try:
        repos = run_cmd(
            f'gcloud artifacts repositories list --location={region} --project={project_id} --format="value(name)"',
            use_gcloud_path=True
        )
        if repository in repos:
            print(f"✓ Repository '{repository}' exists")
        else:
            print(f"  Creating repository '{repository}'...")
            run_cmd(
                f'gcloud artifacts repositories create {repository} '
                f'--repository-format=docker --location={region} '
                f'--description="OptiMystic API images" --project={project_id}',
                use_gcloud_path=True
            )
    except Exception as e:
        print(f"  Creating repository '{repository}'...")
        run_cmd(
            f'gcloud artifacts repositories create {repository} '
            f'--repository-format=docker --location={region} '
            f'--description="OptiMystic API images" --project={project_id}',
            use_gcloud_path=True
        )
    
    # Step 4: Build container image using Cloud Build
    image_uri = f"{region}-docker.pkg.dev/{project_id}/{repository}/{image_name}:{image_tag}"
    print(f"\n[4/6] Building container image → {image_uri}")
    run_cmd(
        f'gcloud builds submit --project={project_id} '
        f'--tag {image_uri} --file docker/Dockerfile .',
        use_gcloud_path=True, capture=False
    )
    print(f"✓ Image built: {image_uri}")
    
    # Step 5: Parse environment variables
    print(f"\n[5/6] Deploying to Cloud Run...")
    env_vars = []
    if Path(env_file).exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    env_vars.append(line)
        print(f"  Loaded {len(env_vars)} environment variables")
    
    env_arg = ""
    if env_vars:
        env_arg = f'--set-env-vars={",".join(env_vars)}'
    
    auth_arg = "--allow-unauthenticated" if allow_unauthenticated else "--no-allow-unauthenticated"
    
    # Deploy to Cloud Run
    deploy_cmd = (
        f'gcloud run deploy {service_name} '
        f'--image={image_uri} '
        f'--region={region} '
        f'--platform=managed '
        f'--project={project_id} '
        f'--port=8000 '
        f'--memory=2Gi '
        f'--cpu=2 '
        f'--timeout=900 '
        f'--concurrency=4 '
        f'{env_arg} '
        f'{auth_arg}'
    )
    run_cmd(deploy_cmd, use_gcloud_path=True, capture=False)
    
    # Step 6: Get service URL
    print(f"\n[6/6] Retrieving service URL...")
    service_url = run_cmd(
        f'gcloud run services describe {service_name} '
        f'--region={region} --project={project_id} '
        f'--format="value(status.url)"',
        use_gcloud_path=True
    )
    
    print(f"""
╔════════════════════════════════════════════════╗
║  ✅ Deployment Successful!                      ║
╚════════════════════════════════════════════════╝

Service URL:   {service_url}
Project:       {project_id}
Region:        {region}
Service:       {service_name}

Next steps:
1. Test the health endpoint:
   curl {service_url}/health

2. View logs:
   gcloud run logs read {service_name} --region={region} --project={project_id}

3. Monitor from console:
   https://console.cloud.google.com/run/detail/{region}/{service_name}?project={project_id}
""")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy OptiMystic API to Google Cloud Run")
    parser.add_argument("--project-id", required=True, help="GCP Project ID")
    parser.add_argument("--region", default="asia-northeast3", help="GCP region")
    parser.add_argument("--service-name", default="optimystic-api", help="Cloud Run service name")
    parser.add_argument("--repository", default="optimystic", help="Artifact Registry repository name")
    parser.add_argument("--image-name", default="api", help="Docker image name")
    parser.add_argument("--image-tag", default="latest", help="Docker image tag")
    parser.add_argument("--env-file", default="deploy/gcp/.env.app", help="Environment file path")
    parser.add_argument("--allow-unauthenticated", action="store_true", help="Allow unauthenticated access")
    
    args = parser.parse_args()
    
    try:
        deploy_cloud_run(
            project_id=args.project_id,
            region=args.region,
            service_name=args.service_name,
            repository=args.repository,
            image_name=args.image_name,
            image_tag=args.image_tag,
            env_file=args.env_file,
            allow_unauthenticated=args.allow_unauthenticated
        )
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        sys.exit(1)
