.PHONY: run test install

install:
	pip install -r requirements.txt

run:
	python main.py

test:
	pytest
