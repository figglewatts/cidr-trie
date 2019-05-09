.PHONY: build
build:
	python3 setup.py sdist bdist_wheel

.PHONY: deploy
deploy:
	twine upload dist/*

.PHONY: clean
clean:
	rm -rf build
	rm -rf dist
	rm -rf docs/_build

.PHONY: docs
docs:
	sphinx-apidoc -f -o docs cidr_trie
	sphinx-build -b html -a -c docs docs docs/_build