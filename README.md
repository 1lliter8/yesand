# <img src="static/images/logo.svg" alt="yes&" width="200" height="200">

A lightweight, minimal prompt database and webapp that aims to keep you creative.

## Philosophy

yes& wants to be simple to deploy, simple to work with, and simple to query. It's only ever opinionated enough to get you storing and serving your first prompt as quickly as possible.

* Minimal prompt storage overhead
* Flexible, enabling prompt organisation
* Serve prompts via API

## To do

- [ ] Add API to return prompts selected at any dirnode depth for max flexibility
- [ ] Add API key object
- [ ] Add user model and authentication

## Development

This Django project is managed using [poetry](https://python-poetry.org), and is linted and formatted with [ruff](https://docs.astral.sh/ruff/).

Task running is done with [poethepoet](https://poethepoet.natn.io/index.html). Run `poe` to see what's implemented.

Currently themed with [Pulse](https://bootswatch.com/pulse/) from Bootswatch but that can change.
