# Package postprocess for PDFNLT

Re-implementation of [PDFNLT](https://github.com/KMCS-NII/PDFNLT)/postprocess
in Python.

# Requirements and Installation

This module is designed for Python3 (3.5 or later). You can install this module
and dependent libraries just by one shot:

```
$ python3 setup.py install
```

# Basic usage

Execute the `postprocess` package with Python3 interpreter. You can specify one
or more XHTML files to process:

```
$ python3 -m postprocess XHTML ...
```

The outputs go to `./out` directory as default. To output the files to the
other places, use `-o` option:

```
$ python3 -m postprocess -o DIR XHTML ...
```

Further options can be found with:

```
$ python3 -m postprocess -h
```

## Modules in postprocess

This project includes the following modules. Please see the docstrings in each moudle file for the details.

* Textualizer (`textualizer.py`)
* FigureTagger (`figuretagger.py`)
* MathTagger (`mathtagger.py`)
* CiteDetector (`citedetector.py`)

## Output files

The following files will be generated in the output DIR:

* `<input>.cite.tsv`: List of citations in TSV form
* `<input>.math.tsv`: List of mathematical expressions in TSV form
* `<input>.sent.tsv`: List of sentences in TSV form
* `<input>.txt`: Plain text extracted from the input
* `<input>.word.tsv`: List of words in TSV form
* `<input>.xhtml`: The postprocessed XHTML with following attributes

### XHTML attributes

* `data-sent-id`: sentence id
* `data-from`: start position of a word
* `data-to`: end position of a word
* `data-cite-id`: paragraph id corresponds to the reference paper in reference section
* `data-cite-end`: word id where the citation tokens end
* `data-cite-type`: citation type automatically determined by [Nanba, H., et al. 2000]  
	Citation types represent the reason for citation:
	* Type B: Citations that show other researchers' theories or methods for
the theoretical basis
	* Type C: Citations to point out the problems or gaps in related works
	* Type O: Citations other than types B and C
* `data-cite-type-cue`: the citation types are determined based on this cue phrases
* `data-math`: indicates in-line formulas. The range of a formula starts with "B-Math" and while "I-Math" continues
* `data-figref`: indicator of figure references. Starts with a `B-FIG` and continues during the `I-FIG`s
* `data-figref-id`: indicates the figure which it refers to. Corresponds to `data-fig` tag
* `data-figref-end`: the word span `id` of which the figure reference ends

# Advanced usage

Some modules in the postprocess package also provide independent CLI.

## Control mathtagger

You can execute "tag" and "learn" operation. Try following for the details:

```
$ python3 -m postprocess.mathtagger -h
```

<!--

# Running tests

You can also run all tests just by one shot:

```
$ python3 setup.py test
```

-->

# References

* Nanba, H., Kando, N., Okumura, M.: Classification of research papers using citation links and citation types: Towards automatic review article generation. (2000)

