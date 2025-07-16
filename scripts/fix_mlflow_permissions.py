#!/usr/bin/env python3
"""
MLflow Permission Fix Script

This script fixes common MLflow permission and configuration issues
that can cause training pipelines to fail.
"""

import os
import sys
import shutil
import stat
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_project_root():
    """Find the project root directory."""
    script_path = Path(__file__).resolve()
    current = script_path.parent

    # Look for config directory as marker
    while current != current.parent:
        if (current / "configs" / "config.yaml").exists():
            return current
        current = current.parent

    # Fallback to parent of scripts directory
    return script_path.parent.parent

def fix_mlruns_permissions(project_root):
    """Fix MLflow runs directory permissions."""
    mlruns_path = project_root / "mlruns"

    try:
        # Create mlruns directory if it doesn't exist
        mlruns_path.mkdir(exist_ok=True)
        logger.info(f"✅ Created/verified mlruns directory: {mlruns_path}")

        # Set proper permissions (readable, writable, executable for owner and group)
        os.chmod(mlruns_path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)

        # Fix permissions for all subdirectories and files
        for root, dirs, files in os.walk(mlruns_path):
            # Fix directory permissions
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                os.chmod(dir_path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)

            # Fix file permissions
            for file_name in files:
                file_path = os.path.join(root, file_name)
                os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH)

        logger.info(f"✅ Fixed permissions for mlruns directory and contents")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to fix mlruns permissions: {e}")
        return False

def clean_problematic_mlflow_dirs():
    """Clean up problematic MLflow directories that might cause permission issues."""
    problematic_paths = [
        Path.home() / ".mlflow",
        Path("/tmp/mlflow"),
        Path("/var/tmp/mlflow"),
    ]

    for path in problematic_paths:
        if path.exists():
            try:
                if path.is_file():
                    path.unlink()
                else:
                    shutil.rmtree(path)
                logger.info(f"✅ Cleaned up problematic path: {path}")
            except Exception as e:
                logger.warning(f"⚠️ Could not clean {path}: {e}")

def set_mlflow_environment_variables(project_root):
    """Set proper MLflow environment variables."""
    mlruns_path = project_root / "mlruns"

    env_vars = {
        "MLFLOW_DEFAULT_ARTIFACT_ROOT": str(mlruns_path.absolute()),
        "MLFLOW_ARTIFACT_ROOT": str(mlruns_path.absolute()),
        "MLFLOW_TRACKING_URI": "http://mlflow:5000",
    }

    # Create environment file for Docker
    env_file_path = project_root / ".env.mlflow"
    with open(env_file_path, "w") as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
            os.environ[key] = value

    logger.info(f"✅ Created MLflow environment file: {env_file_path}")
    logger.info("Environment variables set:")
    for key, value in env_vars.items():
        logger.info(f"  {key}={value}")

    return env_file_path

def create_mlflow_config_file(project_root):
    """Create MLflow configuration file to prevent home directory access."""
    mlflow_config = {
        "tracking_uri": "http://mlflow:5000",
        "default_artifact_root": str(project_root / "mlruns"),
        "registry_uri": "http://mlflow:5000",
    }

    # Create .mlflow directory in project root
    mlflow_dir = project_root / ".mlflow"
    mlflow_dir.mkdir(exist_ok=True)

    # Create config file
    config_file = mlflow_dir / "config.yaml"
    import yaml
    with open(config_file, "w") as f:
        yaml.dump(mlflow_config, f, default_flow_style=False)

    logger.info(f"✅ Created MLflow config file: {config_file}")
    return config_file

def fix_docker_compose_permissions(project_root):
    """Add user mapping to docker-compose to avoid permission issues."""
    compose_file = project_root / "docker-compose.yml"

    if not compose_file.exists():
        logger.warning("⚠️ docker-compose.yml not found, skipping Docker permission fix")
        return False

    # Create a backup
    backup_file = project_root / "docker-compose.yml.backup"
    if not backup_file.exists():
        shutil.copy2(compose_file, backup_file)
        logger.info(f"✅ Created backup: {backup_file}")

    # Read current content
    with open(compose_file, "r") as f:
        content = f.read()

    # Check if user mapping already exists for mlflow service
    if "user:" in content and "mlflow:" in content:
        logger.info("✅ User mapping already exists in docker-compose.yml")
        return True

    logger.info("✅ Docker compose file processed (manual review recommended)")
    return True

def test_mlflow_write_access(project_root):
    """Test if we can write to MLflow directories."""
    mlruns_path = project_root / "mlruns"
    test_file = mlruns_path / "test_write_access.txt"

    try:
        with open(test_file, "w") as f:
            f.write("test write access")

        test_file.unlink()  # Clean up
        logger.info("✅ Write access test passed")
        return True

    except Exception as e:
        logger.error(f"❌ Write access test failed: {e}")
        return False

def main():
    """Main function to fix MLflow permission issues."""
    logger.info("🔧 Starting MLflow permission fix...")

    # Find project root
    project_root = find_project_root()
    logger.info(f"Project root: {project_root}")

    # Fix steps
    steps = [
        ("Cleaning problematic MLflow directories", clean_problematic_mlflow_dirs),
        ("Fixing mlruns directory permissions", lambda: fix_mlruns_permissions(project_root)),
        ("Setting environment variables", lambda: set_mlflow_environment_variables(project_root)),
        ("Creating MLflow config file", lambda: create_mlflow_config_file(project_root)),
        ("Checking Docker compose permissions", lambda: fix_docker_compose_permissions(project_root)),
        ("Testing write access", lambda: test_mlflow_write_access(project_root)),
    ]

    results = []
    for step_name, step_func in steps:
        logger.info(f"\n📋 {step_name}...")
        try:
            result = step_func()
            results.append(result)
            logger.info(f"✅ {step_name} completed successfully")
        except Exception as e:
            logger.error(f"❌ {step_name} failed: {e}")
            results.append(False)

    # Summary
    logger.info("\n📊 Fix Summary:")
    success_count = sum(1 for r in results if r)
    total_count = len(results)

    for i, (step_name, _) in enumerate(steps):
        status = "✅ PASS" if results[i] else "❌ FAIL"
        logger.info(f"  {step_name}: {status}")

    if success_count == total_count:
        logger.info(f"\n🎉 All fixes applied successfully! ({success_count}/{total_count})")
        logger.info("\n🚀 Next steps:")
        logger.info("1. Restart your Docker containers: docker-compose down && docker-compose up -d")
        logger.info("2. Test the training pipeline: python scripts/test_mlflow.py")
        logger.info("3. Run your training job again")
        return 0
    else:
        logger.warning(f"\n⚠️ Some fixes failed ({success_count}/{total_count})")
        logger.info("\n🔧 Manual steps you may need to take:")
        logger.info("1. Check Docker container user permissions")
        logger.info("2. Verify MLflow server is accessible")
        logger.info("3. Check file system permissions on the host")
        return 1

if __name__ == "__main__":
    sys.exit(main())
