TEX=main

.PHONY: pdf clean

pdf:
	@if command -v latexmk >/dev/null 2>&1; then \
		latexmk -pdf -interaction=nonstopmode -halt-on-error $(TEX).tex; \
	else \
		pdflatex -interaction=nonstopmode -halt-on-error $(TEX).tex; \
		bibtex $(TEX); \
		pdflatex -interaction=nonstopmode -halt-on-error $(TEX).tex; \
		pdflatex -interaction=nonstopmode -halt-on-error $(TEX).tex; \
	fi

clean:
	@if command -v latexmk >/dev/null 2>&1; then \
		latexmk -c; \
	else \
		rm -f $(TEX).aux $(TEX).bbl $(TEX).blg $(TEX).fdb_latexmk $(TEX).fls $(TEX).log $(TEX).out $(TEX).synctex.gz $(TEX).toc; \
	fi
