PYTHON ?= python

.PHONY: setup test lint prepare-fleurs index-public index-amedia status

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

index-amedia:
	$(PYTHON) scripts/index_amedia_video.py

status:
	$(PYTHON) scripts/acquisition_status.py
