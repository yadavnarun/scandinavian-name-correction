# Scandinavian Name Correction Service

A Django-based API service for correcting and matching Scandinavian names using phonetic algorithms and fuzzy matching techniques.

## Project Overview

This service provides an API for matching and correcting Scandinavian names, handling special characters and regional naming variations. It uses Double Metaphone algorithm and fuzzy matching to find the most likely correct spelling of a name.

## Requirements

- Python 3.13+
- Django 5.2+
- Required Python packages (see `requirements.txt`)

## Local Development Setup

### 1. Set up Python environment with pyenv

First, install pyenv and pyenv-virtualenv if you haven't already:

```bash
# macOS
brew install pyenv pyenv-virtualenv

# Linux
curl https://pyenv.run | bash
git clone https://github.com/pyenv/pyenv-virtualenv.git $(pyenv root)/plugins/pyenv-virtualenv
```

Add pyenv and pyenv-virtualenv to your shell configuration:

```bash
# Add to your .bashrc, .zshrc, or equivalent
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
```

Restart your shell or source your configuration file:

```bash
source ~/.bashrc  # or ~/.zshrc, etc.
```

### 2. Clone the repository

```bash
git clone <repository-url>
cd scandinavian_name_correction
```

### 3. Install Python and create a virtual environment

```bash
# Install Python 3.13.3
pyenv install 3.13.3

# Create a virtualenv using pyenv
pyenv virtualenv 3.13.3 scandinavian-env

# Set as local Python version for this project
pyenv local scandinavian-env

# Verify the environment is active
python --version  # Should show Python 3.13.3
```

The virtual environment will automatically activate when you enter the project directory thanks to the `.python-version` file created by `pyenv local`.

### 4. Install dependencies

```bash
# Ensure pip is up to date
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
```

### 5. Run migrations

```bash
python manage.py migrate
```

### 6. Start the development server

```bash
python manage.py runserver
```

The API will be available at http://localhost:8000/

## API Usage

### Health Check

Response: `OK` (Status 200)

### Name Correction API

#### Correct a name

```
POST /api/correct/
```

Request Body:

```json
{
  "first_name": "Ake",
  "last_name": "Svensson",
  "country_code": "SE"
}
```

Example using curl:

```bash
curl -X POST http://127.0.0.1:8000/api/correct/ \
     -H "Content-Type: application/json" \
     -d '{
           "first_name": "",
           "last_name": "",
           "country_code": "SE"
         }'
```

Parameters:

- `first_name`: The first name to correct
- `last_name`: The last name to correct
- `country_code`: ISO 3166-1 alpha-2 country code (e.g., "SE" for Sweden, "NO" for Norway, "DK" for Denmark)
