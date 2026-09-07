# Contributing

## Development Setup

```bash
git clone https://github.com/coder01128/agency-content-pipeline.git
cd agency-content-pipeline
pip install -e ".[dev]"
cp .env.example .env
```

## Code Style

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.

```bash
ruff check .
ruff format .
```

## Testing

```bash
pytest tests/ -v
```

All external API calls are mocked in tests. No live API keys needed to run the test suite.

## Commits

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation
- `test:` test additions or changes
- `refactor:` code change that neither fixes nor adds

## Pull Requests

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/your-feature`)
3. Make your changes
4. Run `ruff check . && ruff format . && pytest tests/ -v`
5. Open a PR with a clear description
