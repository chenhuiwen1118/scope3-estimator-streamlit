# Streamlit Community Cloud Deployment

This note records the deployment shape for the online demo version of the
Scope 3 Estimator.

## Deployment Target

- Platform: Streamlit Community Cloud
- Entrypoint: `app.py`
- Python: 3.11
- Runtime dependency file: `requirements.txt`
- Linux package file: `packages.txt`
- Streamlit config: `.streamlit/config.toml`

## Required Repository Files

Make sure these files are committed to GitHub:

- `app.py`
- `src/`
- `data/emission_factors/tier1_local/tier1_unified.csv`
- `data/emission_factors/tier1_local/tier1_metadata.csv`
- `data/emission_factors/tier1_local/tier1_embeddings.npy`
- `data/emission_factors/tier2_international/tier2_unified.csv`
- `data/emission_factors/tier2_international/tier2_metadata.csv`
- `data/emission_factors/tier2_international/tier2_embeddings.npy`
- `data/emission_factors/tier3_eeio/tier3_eeio_unified.csv`
- `data/emission_factors/tier3_eeio/tier3_eeio_metadata.csv`
- `data/emission_factors/tier3_eeio/tier3_eeio_embeddings.npy`
- `data/reference_data/`
- `requirements.txt`
- `packages.txt`
- `runtime.txt`
- `.streamlit/config.toml`
- `.streamlit/secrets.toml.example`

Do not commit confidential procurement workbooks unless the repository and
Streamlit app are private.

## Model Mode

The app now chooses the model loading mode automatically:

- Local machine with Hugging Face model cache: offline mode.
- Cloud runtime without local model cache: online model download.

To force cloud mode in Streamlit Community Cloud, add this to the app Secrets:

```toml
SCOPE3_MODEL_MODE = "online"
```

To force local/offline mode:

```toml
SCOPE3_MODEL_MODE = "offline"
```

## Streamlit Community Cloud Steps

1. Upload or push this project to GitHub.
2. Go to `https://share.streamlit.io`.
3. Create a new app.
4. Select the GitHub repository and branch.
5. Set the main file path to `app.py`.
6. In advanced settings, select Python 3.11 if available.
7. In Secrets, optionally add `SCOPE3_MODEL_MODE = "online"`.
8. Deploy the app.

After deployment, the app will receive a stable `*.streamlit.app` URL. Future
changes can be made by pushing new commits to the same GitHub repository.

## Notes

- First deployment may take several minutes because `torch`,
  `sentence-transformers`, and `faiss-cpu` must be installed.
- The first app launch may also download the multilingual sentence-transformer
  model.
- `requirements.txt` is intentionally limited to runtime dependencies for the
  Streamlit app. Developer and API-server packages are listed in
  `requirements-dev.txt`.
- If the app exceeds memory limits, deploy a reduced demo dataset first or move
  large datasets to controlled cloud storage.
