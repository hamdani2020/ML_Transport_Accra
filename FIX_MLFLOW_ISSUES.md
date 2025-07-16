# MLflow Permission Issues - Fix Guide

## Quick Fix Steps

### 1. Stop running containers
```bash
docker-compose down
```

### 2. Fix permissions automatically
```bash
python scripts/fix_mlflow_permissions.py
```

### 3. Create missing directories and set permissions
```bash
mkdir -p mlruns models
chmod -R 755 mlruns models
```

### 4. Restart containers
```bash
docker-compose up -d
```

### 5. Test MLflow connectivity
```bash
python scripts/test_mlflow.py
```

### 6. Run your training pipeline again
The training should now work without permission errors.

## Manual Fix (if automatic fix doesn't work)

### 1. Check Docker user mapping
Ensure your docker-compose.yml has proper user mapping for the mlflow service:
```yaml
mlflow:
  user: "1000:1000"  # or your actual user ID
```

### 2. Set environment variables
Add these to your shell environment or .env file:
```bash
export MLFLOW_DEFAULT_ARTIFACT_ROOT=/path/to/your/project/mlruns
export MLFLOW_ARTIFACT_ROOT=/path/to/your/project/mlruns
export MLFLOW_TRACKING_URI=http://localhost:5000
```

### 3. Fix directory ownership
```bash
sudo chown -R $USER:$USER mlruns/
sudo chown -R $USER:$USER models/
```

## What Was Fixed

### 1. Updated train.py script:
- Fixed config loading to use absolute paths
- Added comprehensive MLflow error handling
- Added fallback to save models locally if MLflow fails
- Set proper environment variables for artifact paths

### 2. Enhanced docker-compose.yml:
- Added MLflow environment variables to Airflow services
- Added user mapping to MLflow service
- Improved artifact root configuration

### 3. Created diagnostic tools:
- `test_mlflow.py`: Tests MLflow connectivity
- `fix_mlflow_permissions.py`: Automatically fixes permission issues

## Verification

After applying fixes, you should see:
1. Training completes without permission errors
2. Model artifacts saved both locally and in MLflow
3. Log message: "✅ Successfully logged artifacts to MLflow"

## Troubleshooting

If issues persist:

1. **Check Docker container logs:**
   ```bash
   docker-compose logs mlflow
   docker-compose logs airflow-scheduler
   ```

2. **Verify MLflow is accessible:**
   ```bash
   curl http://localhost:5000/health
   ```

3. **Check file permissions:**
   ```bash
   ls -la mlruns/
   ls -la models/
   ```

4. **Run diagnostic script:**
   ```bash
   python scripts/test_mlflow.py
   ```

5. **Check environment variables in container:**
   ```bash
   docker-compose exec airflow-scheduler env | grep MLFLOW
   ```

## Root Cause Analysis

The original error occurred because:

1. **MLflow was trying to access `/home/lusitech`** - This suggests the artifact store wasn't properly configured
2. **Relative path issues** - The config loading used relative paths that didn't resolve correctly in Docker
3. **Permission mismatches** - Docker containers running with different user IDs than the host

The fixes ensure MLflow uses the correct, writable artifact directory and handles permission issues gracefully.