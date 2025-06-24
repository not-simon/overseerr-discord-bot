FROM python:3.12-slim

WORKDIR /app

# Add /app to the PYTHONPATH so "from bot.config" works
ENV PYTHONPATH "${PYTHONPATH}:/app"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire bot directory, which includes main.py and all other code
COPY bot/ bot/

# Run the main script from its location inside the bot directory
CMD ["python", "bot/main.py"]