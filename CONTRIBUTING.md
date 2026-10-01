# Contributing

Thanks for improving Media Downloader.

## Before you begin

- Follow the [Code of Conduct](CODE_OF_CONDUCT.md).
- Check existing issues before opening a new one.
- Discuss significant features or platform changes in an issue first.
- Do not submit private URLs, cookies, API keys, tokens, proxy credentials, or downloaded media.

## Development workflow

1. Fork the repository and create a focused branch from `main`.
2. Install the backend and frontend dependencies as described in the [README](README.md).
3. Make the smallest change that solves the problem.
4. Add or update tests for backend behaviour, where applicable.
5. Run the checks below before opening a pull request.

```bash
cd backend
python -m pytest tests -q
```

```bash
cd frontend
npm run typecheck
npm run lint
npm run build
```

## Pull requests

Use a clear title and explain the user-facing effect of the change. Keep pull requests small, include tests when behaviour changes, and update the README or feature reference when setup, configuration, or functionality changes.

By contributing, you agree that your contribution may be used under the repository's licence once one is selected.
