PYTHON ?= python

.PHONY: setup test lint prepare-fleurs index-public status

setup:
	$(PYTHON) -m pip install -e ".[quality,dev]"

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check .

prepare-fleurs:
	$(PYTHON) scripts/prepare_fleurs.py

index-public:
	$(PYTHON) scripts/index_sami_parliament.py
	$(PYTHON) scripts/index_registered_media.py --group sveriges_radio

status:
	$(PYTHON) scripts/acquisition_status.py
