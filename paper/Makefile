all: figures main.pdf
figures:
	../.venv/bin/python ../scripts/make_figures.py
main.pdf: main.tex
	tectonic -X compile main.tex
.PHONY: all figures
