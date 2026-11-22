FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY radar radar
COPY web web
COPY sources/catalog-filters.json sources/catalog-filters.json
COPY sources/catalog.json sources/catalog.json
COPY sources/review500/ sources/review500/
COPY sources/live-reviews/ sources/live-reviews/
COPY sources/search.sqlite.gz sources/search.sqlite.gz
RUN python -c "import gzip, shutil; from pathlib import Path; p=Path('sources/search.sqlite.gz'); shutil.copyfileobj(gzip.open(p,'rb'),p.with_suffix('').open('wb')); p.unlink()"
RUN python -m radar.enrich_projects && python -m radar.update_maturity
ENV RADAR_PHRASE_MODE=words
CMD ["sh", "-c", "exec uvicorn radar.public:app --host 0.0.0.0 --port ${PORT:-10000}"]
