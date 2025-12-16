# Railway Deployment Setup

## Prerequisites

- Railway account
- GitHub repo connected to Railway

## Steps

### 1. Create Project

1. Go to [Railway](https://railway.app)
2. New Project → Deploy from GitHub repo
3. Select the geocass repository

### 2. Add Persistent Volume

**Important**: SQLite needs persistent storage or data will be lost on redeploys.

1. In your Railway project, click "New" → "Volume"
2. Set mount path to `/data`
3. Attach to your service

### 3. Set Environment Variables

In Railway dashboard → Variables:

```
GEOCASS_SECRET_KEY=<generate-a-random-secure-string>
GEOCASS_PUBLIC_URL=https://geocass.hearthweave.org
GEOCASS_DATA_DIR=/data
```

Generate a secret key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4. Deploy

Railway will automatically:
- Detect Python via nixpacks
- Install dependencies from requirements.txt
- Run the Procfile command
- Set the PORT environment variable

### 5. Custom Domain (Optional)

1. Settings → Domains
2. Add custom domain: `geocass.hearthweave.org`
3. Configure DNS with the provided CNAME

## Files Used by Railway

- `Procfile` - Start command
- `railway.toml` - Build settings, health check
- `runtime.txt` - Python version (3.11)
- `requirements.txt` - Dependencies

## Health Check

Railway will hit `/health` to verify the service is running.

## Logs

View logs in Railway dashboard or:
```bash
railway logs
```
