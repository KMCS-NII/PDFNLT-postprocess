#!/usr/bin/env python3

# libraries
import re
import csv
from pathlib import Path
from docopt import docopt
from lxml import etree

from .config import PKG_NAME, VERSION
from .exceptions import AlreadyTaggedError
from .cli_utils import set_logger
from .structures import Document
from .figuretagger import FigureTagger
from .mathtagger import MathTagger
from .citedetector import CiteDetector
from .textualizer import Textualizer

# help text
HELP = """
The postprocess script for PDFNLT.

Usage:
    {p} [options] XHTML...
    {p} -h | --help
    {p} -V | --version

Options:
    -b, --batch          Execute with batch mode.
    -h, --help           Show this screen and exit.
    -l FILE, --log=FILE  Output messages to FILE.
    -m, --map            Insert positions into the xhtml.
    -o DIR, --out=DIR    Output files to DIR.
    -q, --quiet          Show less messages.
    -v, --verbose        Show more messages.
    -V, --version        Show version.

""".format(p=PKG_NAME)

# use logger
import logging as log
logger = log.getLogger('postprocess')


# the application
def output(doc, out_dir):
    """Output the result files."""

    # general preparation
    logger.debug('Outputting the results into {}'.format(out_dir))
    out_dir.mkdir(parents=True, exist_ok=True)
    src = Path(doc.filename)

    def get_writer(f):
        return csv.writer(
            f,
            delimiter='\t',
            quotechar='"',
            lineterminator='\n',
            quoting=csv.QUOTE_MINIMAL)

    # word.tsv
    word_tsv = out_dir / Path(src.stem + '.word.tsv')
    logger.debug('Writing {}'.format(word_tsv))

    with open(str(word_tsv), 'w', newline='') as f:
        writer = get_writer(f)
        writer.writerow(['ID', 'From', 'To', src])
        for w in doc.words:
            writer.writerow(w)

    # xhtml
    xhtml = out_dir / Path(src.name)
    logger.debug('Writing {}'.format(xhtml))
    xhtml.write_bytes(etree.tostring(doc.tree))

    # plain text
    txt = out_dir / Path(src.stem + '.txt')
    logger.debug('Writing {}'.format(txt))
    txt.write_text(doc.text, encoding='utf-8')

    # sent.tsv
    sent_tsv = out_dir / Path(src.stem + '.sent.tsv')
    logger.debug('Writing {}'.format(sent_tsv))

    with open(str(sent_tsv), 'w', newline='') as f:
        writer = get_writer(f)
        writer.writerow(['id', 'sect_name', 'box_name', 'text', 'words'])
        for s in doc.sentences:
            writer.writerow([
                s._id, s.sec_name, s.box_name,
                s.text.strip(), ','.join(s.words)
            ])

    # math.tsv
    math_tsv = out_dir / Path(src.stem + '.math.tsv')
    logger.debug('Writing {}'.format(math_tsv))

    with open(str(math_tsv), 'w', newline='') as f:
        writer = get_writer(f)
        writer.writerow(
            ['MathID', 'StartID', 'EndId', 'Page', 'X1', 'Y1', 'X2', 'Y2'])
        for m in doc.maths:
            writer.writerow(m)

    # cite.tsv
    cite_tsv = out_dir / Path(src.stem + '.cite.tsv')
    logger.debug('Writing {}'.format(cite_tsv))

    with open(str(cite_tsv), 'w', newline='') as f:
        writer = get_writer(f)
        writer.writerow(['CiteID', 'Text', 'From'])
        for c in doc.cites:
            writer.writerow([c[0], c[1], ','.join(c[2])])


def main():
    """The main function.

    1. parse command line options
    2. setup the logger
    3. treat all input xhtml
    """
    # parse options and arguments
    args = docopt(HELP, version=VERSION)

    # setup the logger
    log_level = 1  # info (default)
    if args['--quiet']:
        log_level = 0  # warn
    if args['--verbose']:
        log_level = 2  # debug

    log_file = args['--log']  # output messages stderr as default

    set_logger(log_level, log_file)

    # batch mode
    batch_mode = args['--batch']
    if batch_mode:
        logger.debug('Selected mode: batch')
    else:
        logger.debug('Selected mode: normal')

    # map
    remove_pos = not args['--map']

    # prepare the output dir
    if args['--out'] is None:
        out_dir = Path('out')
        logger.info('Using the default outdir: {}'.format(out_dir))
    else:
        out_dir = Path(args['--out'])

    for fn in args['XHTML']:
        # initialize
        fn = Path(fn)
        logger.info('Begin to process: {}'.format(fn))

        textualizer = Textualizer()
        citedetector = CiteDetector()
        figuretagger = FigureTagger()

        model_file = 'postprocess/mathtagger/model/inline_math.model'
        mathtagger = MathTagger(model_file)

        # try to process the file
        try:
            # load the xhtml
            doc = Document(str(fn))

            # figure tagging
            figuretagger.tag(doc)

            # math tagging
            mathtagger.open(doc)

            try:
                mathtagger.tag()

            except AlreadyTaggedError:
                logger.warn(
                    'mathtagger: File "{}" is already math-tagged. Skipping'.
                    format(fn))

            # citation detection
            citedetector.open(doc)
            citedetector.detect_cite()

            # textualize
            textualizer.textualize(doc, remove_pos)

            # output the results
            output(doc, out_dir)

        except Exception as e:
            logger.exception('Failed to process "{}"'.format(fn))

            # in batch mode, just report the error and continue
            if batch_mode:
                logger.warn(
                    'We got an error, but continuing the process (batch mode)')

            # otherwise, raise the error
            else:
                raise


# execute
main()
