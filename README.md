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
           "first_name": "Ake",
           "last_name": "Svensson",
           "country_code": "SE"
         }'
```

Response:

```json
{
  "first_name_matches": [
    {
      "name": "Akke",
      "score": 86,
      "base_similarity": 86,
      "metaphone": ["AK", "AK"],
      "is_nordic": false,
      "is_query_variant": false,
      "in_dataset": true,
      "type": "first_name",
      "data": {
        "country": {
          "BE": 0.019,
          "DE": 0.008,
          "FI": 0.075,
          "GB": 0.008,
          "IN": 0.011,
          "MA": 0.011,
          "MY": 0.011,
          "NL": 0.823,
          "SA": 0.011,
          "SE": 0.023
        },
        "gender": {
          "F": 0.831,
          "M": 0.169
        },
        "rank": {
          "FI": 1478,
          "NL": 1898,
          "SE": 2973
        }
      },
      "score_reasons": ["Similarity Only"]
    }
    // ...other first name matches...
  ],
  "last_name_matches": [
    {
      "name": "Svensson",
      "score": 100,
      "base_similarity": 100,
      "metaphone": ["SFNSN", "SFNSN"],
      "is_nordic": true,
      "is_query_variant": false,
      "in_dataset": true,
      "type": "last_name",
      "data": {
        "country": {
          "DE": 0.01,
          "DK": 0.033,
          "ES": 0.004,
          "FI": 0.006,
          "FR": 0.005,
          "GB": 0.01,
          "IT": 0.005,
          "NO": 0.014,
          "SE": 0.898,
          "US": 0.015
        },
        "rank": {
          "DE": 7681,
          "DK": 118,
          "FI": 3482,
          "GB": 12399,
          "NO": 256,
          "SE": 8
        }
      },
      "score_reasons": ["Exact Match", "+5 (Nordic)"]
    }
    // ...other last name matches...
  ]
}
```

### Explanation of Response Fields

- **first_name_matches**: A list of potential matches for the provided first name.

  - **name**: The matched name.
  - **score**: The confidence score for the match.
  - **base_similarity**: The base similarity score.
  - **metaphone**: Phonetic representations of the name.
  - **is_nordic**: Whether the name is Nordic.
  - **is_query_variant**: Whether the name is a variant of the query.
  - **in_dataset**: Whether the name exists in the dataset.
  - **type**: The type of match (e.g., "first_name").
  - **data**: Additional metadata about the name.
    - **country**: Country distribution of the name.
    - **gender**: Gender distribution of the name.
    - **rank**: Rank of the name in various countries.
  - **score_reasons**: Reasons for the assigned score.

- **last_name_matches**: A list of potential matches for the provided last name.
  - Similar structure to **first_name_matches**.

This structure provides detailed information about the matching process and the confidence of each match.
