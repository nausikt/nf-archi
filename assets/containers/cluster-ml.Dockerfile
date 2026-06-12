FROM python:3.12-slim
RUN pip install --no-cache-dir numpy pandas pyarrow==17.0.0 scikit-learn hdbscan umap-learn
