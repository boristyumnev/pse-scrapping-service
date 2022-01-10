# PSE Scraping Service

This is a Python service which scrapes Puget Sound Energy website:
* It uses provided credentials
* Downloads current electricity and natural gas usage
* Exposes latest usage value as RESTful JSON endpoint

## How to setup?

To try out:
* Setup via VSCode devcontainer 
* Copy `.env-example` as `.env` and setup there needed credentials
* Launch and it should work

To run it constantly:
* See `deploy/Dockerfile`
