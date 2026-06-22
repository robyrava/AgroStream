# Usa un'immagine base Python leggera
FROM python:3.11-slim

# Imposta la directory di lavoro
WORKDIR /app

# Non scrivere file .pyc
ENV PYTHONDONTWRITEBYTECODE=1
# Non bufferizzare stdout e stderr
ENV PYTHONUNBUFFERED=1

# Installa le dipendenze
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice dell'applicazione
COPY app.py .

# Esponi la porta 5000 (Flask di default, ma noi la leghiamo con gunicorn)
EXPOSE 5000

# Usa un utente non root per sicurezza
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Avvia gunicorn e collega l'applicazione
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:app"]
