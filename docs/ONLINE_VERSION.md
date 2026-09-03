# Scope 3 Estimator Online Version

This project is a Streamlit application. It can be shared online in two modes.

## Temporary public testing URL

Use this mode when the system is running on the local Mac and needs a quick
public URL for external reviewers.

```bash
cd "/Users/sashachen/Documents/Codex/scope3_estimator-working-20260729"
chmod +x run_online_tunnel.sh
./run_online_tunnel.sh
```

The script starts Streamlit on `localhost:8501`, then creates a public
`https://*.lhr.life` URL through localhost.run.

Limitations:

- The URL is temporary.
- The Mac must stay awake.
- The terminal running the tunnel must remain open.
- If the network changes or the tunnel reconnects, the URL may change.

## Production deployment

For the Streamlit Community Cloud version, use the deployment checklist in
`docs/STREAMLIT_COMMUNITY_CLOUD.md`. This is the recommended path for a stable
public demo URL.

For a container-based production deployment, deploy the Docker version to a
cloud host that supports long-running containers, such as Render, Railway,
Fly.io, Google Cloud Run, AWS ECS, Azure Container Apps, or a VM.

Recommended runtime environment variables:

```bash
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
```

The Dockerfile already exposes port `8501` and includes a Streamlit health
check at `/_stcore/health`.

Before production deployment, confirm that these assets are included:

- `data/emission_factors/tier1_local/tier1_embeddings.npy`
- `data/emission_factors/tier2_international/tier2_embeddings.npy`
- `data/emission_factors/tier3_eeio/tier3_eeio_embeddings.npy`
- Hugging Face model cache or a deployment startup step that downloads the
  model before offline mode is enabled.

For public demos, avoid uploading confidential procurement files unless the
hosting environment has access controls.
