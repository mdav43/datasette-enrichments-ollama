# datasette-enrichments-ollama

[![PyPI](https://img.shields.io/pypi/v/datasette-enrichments-ollama.svg)](https://pypi.org/project/datasette-enrichments-ollama/)
[![Changelog](https://img.shields.io/github/v/release/mdav43/datasette-enrichments-ollama?include_prereleases&label=changelog)](https://github.com/datasette/datasette-enrichments-ollama/releases)
[![Tests](https://github.com/mdav43/datasette-enrichments-ollama/workflows/Test/badge.svg)](https://github.com/mdav43/datasette-enrichments-ollama/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/mdav43/datasette-enrichments-ollama/blob/main/LICENSE)

Datasette enrichment for analyzing row data using a locally hosted Ollama instance


## Requirement

you must have a running instance of ollama to use this plugin. At present this is only avialable on Linux or Macos. See more here: [https://github.com/ollama/ollama](https://github.com/ollama/ollama)

This is a straight fork from [datasette-enrichment-gpt](https://github.com/datasette/datasette-enrichments-gpt)

## Installation

Install this plugin in the same environment as Datasette.
```bash
datasette install datasette-enrichments-ollama
```

## Configuration

This plugin needs an API url for the ollama instance. Configure that in `metadata.yml` like so
```yaml
plugins:
  datasette-enrichments-ollama:
    api_url: "http://localhost:11434/api/generate"
```
Or to avoid that key being visible on `/-/metadata` set it as an environment variable and use this:
```yaml
plugins:
  datasette-enrichments-ollama:
    api_url:
      $env: OLLAMA_API_URL
```

## Usage
Once installed, this plugin will allow users to select rows to enrich and run them through prompts using models that are installed and registered in the ollama service, then saving the result of the prompt in the specified column.

## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:
```bash
cd datasette-enrichments-ollama
python3 -m venv venv
source venv/bin/activate
```
Now install the dependencies and test dependencies:
```bash
pip install -e '.[test]'
```
To run the tests:
```bash
pytest
```
