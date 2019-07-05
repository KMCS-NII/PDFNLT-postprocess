#!/usr/bin/env python3

"""
The CiteDetector module.
"""

# libraries
import sys
import copy
import regex
from pathlib import Path
from docopt import docopt
from lxml import etree

from .config import PKG_NAME, VERSION
from .cli_utils import set_logger
from .structures import Document, Paragraph, Word, Sentence

# help text
MOD_NAME = "{}.citedetector".format(PKG_NAME)
HELP = """
Detect citation strings and type on academic paper
which is generated by 'pdfanalyzer'.

Usage:
    {m} [options] XHTML
    {m} -h | --help
    {m} -V | --version

Options:
    -h, --help             Show this screen and exit.
    -l FILE, --log=FILE    Output messages to FILE.
    -o DIR, --out=DIR      Output files to DIR.
    -q, --quiet            Show less messages.
    -v, --verbose          Show more messages.
    -V, --version          Show version.

""".format(m=MOD_NAME)

# use logger
from logging import getLogger
logger = getLogger('postprocess')


# the module
class CiteDetector:
    ns = {'x': 'http://www.w3.org/1999/xhtml'}
    year = '(?:19\d\d|20\d\d|[6789]\d)[a-g]?|forthcoming'
    plural = regex.compile('^(?:and|et|al|others)$')

    def __init__(self):
        """Initialize CiteDetector.

        Usually, you need to create only one CiteDetector in your script.

        Args:
            abbrev (list): List of abbreviations
        """
        self.tokenizer = ''

    def open(self, doc):
        """Open a XHTML file.

        Args:
            doc (Document): The input document.
        """
        self.matched = {}
        self.match_id = 0
        self.match_context = {}
        self.doc = doc
        self.docid = self.__get_docid()
        self.__split_references()
        self.__extract_reference_key()
        logger.info('Now docid = {}'.format(self.docid))

    def detect_cite(self):
        """Detect citations.

        Args:
            doc (Document): The input document.
        """
        person = '(?:van |de |\p{Lu}\p{Latin}+|Ciaramita)'
        head_phrase = '(?:eg\.|e\.g\.,?|see, e\.g\.,|cf\.|see|See) '
        foot_phrase = '(?:inter alia| |,|\.)+'

        type1 = regex.compile("(?:\((?:{head_phrase})?({person}[^()]*{year})(?:{foot_phrase})?\))|(?:\[(?:{head_phrase})?({person}[^\[\]]*{year})(?:{foot_phrase})?\])".format(head_phrase=head_phrase, person=person, year=CiteDetector.year, foot_phrase=foot_phrase))

        type2 = regex.compile("({person}(?:\sand\s{person}|[, ]+et[\. ]al)?)[\., ]*(?:['’]s )?[\(\[]((?:{year}|[;, ])+)[\)\]]".format(person=person, year=CiteDetector.year))
        type3 = regex.compile("\[({person})[, ]+(\d\d?)\]".format(person=person))
        type4 = regex.compile("\[([^\[]+?)\]")

        for ref in self.body:
            hoge = copy.copy(ref['text'])
            # type1.sub(lambda m: self.__replace1(m), ref['text'])
            ref['text'] = type1.sub(self.__replace1, ref['text'])
            ref['text'] = type2.sub(self.__replace2, ref['text'])
            ref['text'] = type3.sub(self.__replace3, ref['text'])
            if bool(self.ref_key):
                ref['text'] = type4.sub(self.__replace4, ref['text'])

        self.__cite_mark_range()


    def output_xhtml(self, filename=None):
        """Write xhtml to the file.

        If the filename is not specified, output to the stdout.
        """
        if filename is None:
            logger.info("Output xhtml to stdout")
            sys.stdout.buffer.write(etree.tostring(self.doc.tree))
        else:
            logger.info("Output xhtml to '{}'".format(filename))
            with open(filename, 'w+b') as fp:
                fp.write(etree.tostring(self.doc.tree))


    def __split_references(self):
        self.references = []
        self.body = []
        for sec in self.doc.tree.xpath('x:body/x:div', namespaces=CiteDetector.ns):
            sec_id = sec.get('id')
            sec_name = sec.get('data-name')

            for box in sec.xpath('x:div', namespaces=CiteDetector.ns):
                box_name = box.get('data-name')

                for par in box.xpath('x:p', namespaces=CiteDetector.ns):
                    ref = {
                        'id': par.get('id'),
                        'text': par.get('data-text'),
                        'node': par
                    }
                    if box_name == 'Reference':
                        self.references.append(ref)
                    else:
                        self.body.append(ref)


    def __extract_reference_key(self):
        bracket1 = regex.compile('^\[([^\[]+?)\]')
        bracket2 = regex.compile('^(\d\d?)\.\s?\p{Lu}')
        self.ref_key = {}
        for ref in self.references:
            m1 = bracket1.match(ref['text'])
            if m1:
                key = m1.group(1)
                regex.sub(' ', '', key)
                self.ref_key[key] = ref['id']
            else:
                m2 = bracket2.match(ref['text'])
                if m2:
                    self.ref_key[m2.group(1)] = ref['id']
        # print(self.ref_key)

    def __get_docid(self):
        """Get docid from the document element.
        """
        docid = self.doc.tree.xpath(
            'x:head/x:meta/@docid', namespaces=CiteDetector.ns)
        if docid is None:
            logger.error('This docid is not defined.')
            return False
        else:
            self.docid = docid[0]

        return self.docid

    def __replace1(self, mat):
        whole = mat.group(1) or mat.group(2)
        tmp_whole = regex.sub('', '\s', whole)
        m = regex.search('{year}(\W)\D'.format(year=CiteDetector.year), tmp_whole)
        splitStr = m.group(1) if m else ';'
        cites = regex.split('(?<=\d\d|\d[abcde])\s?{0}\s*'.format(splitStr), whole)
        m = regex.match('{year}[,; ]+{year}'.format(year=CiteDetector.year), tmp_whole)
        if m:
            cites = self.__split_year(cites)

        cids = []
        for cite in cites:
            m = regex.match('^\d', cite)
            if m:
                continue
            match = self.__search_reference(cite)
            if len(match) == 0:
                continue
            cid = match[0]['cid']
            if cid not in self.matched:
                self.matched[cid] = 0
            self.matched[cid] += 1
            cids.append(cid)

        if len(cids):
            self.match_id += 1
            self.match_context[self.match_id] = {
                'cids' : cids,
                'context' : whole,
                'rType' : 1
            }
            logger.info('match_id: {}, whole: {}'.format(self.match_id, whole))
            return '<refer cite="{0}">'.format(self.match_id)
        else:
            logger.info(whole)
            return whole

    def __replace2(self, mat):
        whole, names = mat.group(), mat.group(1)
        years = regex.split('[;, ]+', mat.group(2))

        cids = []
        for year in years:
            match = self.__search_reference(names + ' ' + year)
            if len(match) == 0:
                continue
            cid = match[0]['cid']
            if cid not in self.matched:
                self.matched[cid] = 0
            self.matched[cid] += 1
            cids.append(cid)

        if len(cids) > 0:
            self.match_id += 1
            self.match_context[self.match_id] = {
                'cids': cids,
                'context': whole,
                'rType': 2
            }
            logger.info('match_id: {}, whole: {}'.format(self.match_id, whole))
            return "<refer cite=\"{0}\">".format(self.match_id)
        else:
            return whole

    def __replace3(self, mat):
        whole, name, year = mat.group(), mat.group(1), mat.group(2)
        match = self.__search_reference(name + ' ' + year)
        if len(match):
            cid = match[0]['cid']
            if cid not in self.matched:
                self.matched[cid] = 0
            self.matched[cid] += 1
            self.match_id += 1
            self.match_context[self.match_id] = {
                'cids': cids,
                'context': whole,
                'rType': 3
            }
            logger.info('match_id: {}, whole: {}'.format(self.match_id, whole))
            return "<refer cite=\"{0}\">".format(self.match_id)
        else:
            return whole

    def __replace4(self, mat):
        whole, hit = mat.group(), mat.group(1)
        tmp_hit = regex.sub("\s", "", hit)
        cids = []
        for key in regex.split(",", tmp_hit):
            key = regex.sub("\s", "", key)
            if key in self.ref_key:
                cid = self.ref_key[key]
            else:
                continue
            cids.append(cid)
            if cid not in self.matched:
                self.matched[cid] = 0
            self.matched[cid] += 1

        if len(cids) > 0:
            self.match_id += 1
            self.match_context[self.match_id] = {
                'cids': cids,
                'context': whole,
                'rType': 4
            }
            logger.info('match_id: {}, whole: {}'.format(self.match_id, whole))
            return "<refer cite=\"{0}\">".format(self.match_id)
        else:
            return whole


    def __cite_mark_range(self):
        identify_type = IdentifyType()
        refer = regex.compile('<refer cite="(.+?)" type="(.*?)" cue="(.*?)">')
        self.cid2phrase = {}
        for ref in self.body:
            paragraph = identify_type.identify_citation_type(ref['text'])
            self.spans = ref['node'].xpath('x:span', namespaces=CiteDetector.ns)
            self.match_span = [False] * len(self.spans)
            if paragraph is not None:
                refer.sub(self.__annotate_tag, paragraph)

    def __annotate_tag(self, mat):
        match_id, rtype, cue = mat.group(1), mat.group(2), mat.group(3)
        logger.info("match_id: {}, rType: {}, cue: {}".format(match_id, rtype, cue))
        mc = self.match_context[int(match_id)]
        # hit = 'no hit'
        context = regex.sub('([ ,.\(\)\[\];:])', '\t\\1\t', mc['context'])
        phrase = [ p for p in regex.split('\t+', context) if p != ' ' ]
        last_year_idx = len(phrase) - 1
        if regex.search('[\)\]]', phrase[-1]):
            len(phrase) - 2 

        ## delete brackets
        if mc['rType'] == 3 or mc['rType'] == 4:
            phrase.pop(0)
            last_year_idx = len(phrase) - 1

        spans = self.spans
        for i in range(0, len(spans)):
            if i+last_year_idx < len(spans) and \
               spans[i].text is not None and \
               spans[i+last_year_idx].text is not None and \
               spans[i].text == phrase[0] and \
               spans[i+last_year_idx].text == phrase[last_year_idx] and \
               not self.match_span[i]:

                spans[i].set('data-cite-id', ','.join(mc['cids']))
                spans[i].set('data-cite-end', spans[i+len(phrase)-1].attrib['id'])
                spans[i].set('data-cite-type', rtype)
                spans[i].set('data-cite-type-cue', cue)
                # hit = join(" ", map { $_->{content} } @spans[$i .. $i+scalar(@phrase)-1])
                for j in range(i, i+len(phrase)):
                    self.match_span[j] = True
                break

        return ''


    def __search_reference(self, string):
        string = regex.sub(r'({0})'.format(CiteDetector.year), ' \\1', string)
        elem = regex.split(r'[,\. ]+', string)
        elem = [ regex.escape(e) for e in elem if not CiteDetector.plural.search(e) ] 
        reg = regex.compile('\W.*?'.join(elem), regex.IGNORECASE)
        match = []
        for ref in self.references:
            m = reg.search(ref['text'])
            if m:
                match.append({
                    'cid'  : ref['id'],
                    'start': m.start(),
                    'total': len(m.group())
                })
        if len(match) > 1:
            if regex.search('et[,\. ]+al|others', string):
                match = sorted(match, key=lambda x:(x['start'],-x['total']))
            else:
                match = sorted(match, key=lambda x:(x['start'],x['total']))
        return match


    def __split_year(cites):
        out = []
        for cite in cites:
            m = regex.match('^(\D+?)({year}(?:[,; ]+{year})+)$'.format(year=CiteDetector.year), cite)
            if m:
                names, years = m.group(1), m.group(2)
                for s in regex.split('[, ]+', years):
                    out.append(names + ' ' + s)
            else:
                out.append(cite)
        return out


class IdentifyType:
    typeB = [
        '[Ww]e adopt',
        '[Ww]e appl(y|ied)',
        '[Ww]e use',
        '[Ww]e follow',
        '[Ww]e select',
        '[Ww]e opt',
        '[Ww]e make use of',
        '[Ww]e utilize',
        '[Oo]ur .{,10} adopt',
        '[Oo]ur .{,10} apply',
        '[Oo]ur .{,10} use',
        '[Oo]ur .{,10} ma(k|d)e use of',
        '[Oo]ur .{,10} utilize'
    ]

    typeC = [
        { "context": [0,1,2,3,4,5], "regex": [
            "however\,[^<]*? not "
        ]},
        { "context": [0,1,2,3,4],   "regex": [
            "however\,[^<]*? our ",
            "However\,?",
            "however\, *the",
            "But "
        ]},
        { "context": [0,1,2,3],     "regex": [
            "however\,[^<]*? they "
        ]},
        { "context": [0,1,2],       "regex": [
            "[Aa]lthough the ",
            "\, ?although ",
            "Though[ ,]",
            "but (?:a|an|the|it|is|are|rather|no) ",
            "[Bb]ut (?:they|their|he|his|she|her|it|instead) ",
            "Instead ?\,",
            "In spite of ",
            " did not ",
            " not be ",
            " (?:that|this|it) is not ",
            " (?:was|were) not ",
            " it does not ",
            " (?:may|might|will|would|could|should|need|have|has) not ",
            " (?:would|could|have|has)n\'t ",
            " can ?not be",
            " not always ",
            " not have ",
            "that do not ",
            "[Tt]hey do ?n[o']t ",
            "[Hh]e does ?n[o']t ",
            "[Ss]he does ?n[o']t ",
            " not (?:require|provide|cover) ",
            " not in effect ",
            " more efficient than [^<]*?cite",
            "[Ll]ittle influence",
            " is too ",
            " (?:a|more) difficult ",
            " differences? between ",
            " the only "
        ]},
        { "context": [1,2],         "regex": [
            " does not ",
            " less studied"
        ]},
        { "context": [0],           "regex": [
            " not[^<]*?enough "
        ]}
    ]

    def identify_citation_type(self, paragraph):
        sentences = regex.split("(?<=\.) (?=\p{Lu})", paragraph)
        for i in range(0, len(sentences)):
            m = regex.search('<refer', sentences[i])
            if not m:
                continue
            citeType, cue = self.__rule_type_new_cue(sentences, i)
            sentences[i] = regex.sub('<refer cite="(.+?)">', '<refer cite="\\1" type="{0}" cue="{1}">'.format(citeType, cue), sentences[i])
                
        return " ".join(sentences)


    def __rule_type_new_cue(self, sentences, i):
        for cue in IdentifyType.typeC:
            context = []
            for j in cue['context']:
                if i+j < len(sentences):
                    context.append(sentences[i+j])
            cont = ' '.join(context)
            for reg in cue['regex']:
                m = regex.search(reg, cont)
                if m:
                    return 'C', m.group().strip(',. ]')

        cont = sentences[i]
        if i+1 < len(sentences):
            cont = cont + ' ' + sentences[i+1]
        for cue in IdentifyType.typeB:
            m = regex.search(cue, cont)
            if m:
                return 'B', m.group().strip(',. ]')

        return 'O', ''


def citedetector_cui():
    """The test function
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

    citedetector = CiteDetector()
    fn = Path(args['XHTML'])
    doc = Document(str(fn))
    citedetector.open(doc)
    citedetector.detect_cite()

    if args['--out']:
        out_dir = Path(args['--out'])
        out_dir.mkdir(parents=True, exist_ok=True)
        citedetector.output_xhtml(str(out_dir / fn.name))
    else:
        citedetector.output_xhtml()

if __name__ == '__main__':
    citedetector_cui()
