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