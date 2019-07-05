"""
The Textualizer module.
"""

# libraries
import re
from nltk.tokenize.punkt import PunktSentenceTokenizer, PunktParameters
from .structures import Paragraph, Word, Sentence

# use logger
from logging import getLogger
logger = getLogger('postprocess')


# the module
class Textualizer:
    """The Textualzer class."""

    def __init__(self, abbrev=['dr', 'vs', 'mr', 'mrs', 'prof', 'inc', 'i.e']):
        """Initialize Textualizer.

        Usually, you need to create only one textualizer in your script.

        Args:
            abbrev (list): List of abbreviations
        """
        punkt = PunktParameters()
        punkt.abbrev_types = set(abbrev)
        self.tokenizer = PunktSentenceTokenizer(punkt)

    def find_sentences(self, par):
        """Finding sentences from paragraph using nltk.

        Args:
            par (Paragraph): The input paragraph

        Returns:
            A list of sentences.
        """
        text = ''.join([w.text for w in par.words])

        word_iter = iter(par.words)
        word = next(word_iter)
        sent_ls = []

        for i, (b, e) in enumerate(self.tokenizer.span_tokenize(text)):
            _id = 's-' + par._id[2:] + '-' + str(i)
            sent = Sentence(_id, par.sec_name, par.box_name, text[b:e], [])

            sent_ls.append(sent)

            while word is not None and word.start < b:
                word = next(word_iter)

            while word is not None and word.start < e:
                if word._id is not None:
                    sent.words.append(word._id)

                try:
                    word = next(word_iter)
                except StopIteration:
                    word = None

        return sent_ls

    def textualize(self, doc, remove_pos=True):
        """Textualize the document.

        The main function of this methods are summarized:

            1. Add sentence information to Document.tree (i.e., XML)
            2. Put list of sentences to Document.sentences
            3. Provide additional attributes (Documents.words, Documents.sentences)

        Additionally, some normalization, e.g., breaking ligatures, are applied.

        In order for the compatibility, it adds following attributes for now:

            - Document.maths
            - Document.cites

        These attributes should be added by other modules in the future.

        Args:
            doc (Document): The input document
            remove_pos (bool): Whether remove positions or not
        """

        # basic variables
        ligatures = {
            '\ufb00': 'ff',
            '\ufb01': 'fi',
            '\ufb02': 'fl',
            '\ufb03': 'ffi',
            '\ufb04': 'ffl',
            '\ufb05': 'st',
            '\ufb06': 'st',
        }
        ns = {'x': 'http://www.w3.org/1999/xhtml'}
        end_token = re.compile(r'[?!.]$')
        tag_token = re.compile(r'(?<!\s)-$')

        pars = {}
        par_ls = []
        last_par = None
        ref_pars = []
        cite = None
        math = None
        ignore_math = False
        math_ls = []
        word_nodes = {}
        cites = {}

        for sec in doc.tree.xpath('x:body/x:div', namespaces=ns):
            sec_id = sec.get('id')
            sec_name = sec.get('data-name')

            for box in sec.xpath('x:div', namespaces=ns):
                box_name = box.get('data-name')

                for par in box.xpath('x:p', namespaces=ns):
                    math_par = False
                    par_id = par.get('id')
                    page_id = int(par.get('data-page'))

                    # standalone equations should continue from last par
                    if box_name == 'Equation' and last_par:
                        p = pars[last_par]
                        # TODO: a bit different from the original; please check
                        # print(len(p.words))

                        if not end_token.match(p.words[-1].text):
                            continued_from_id = last_par
                            math_par = True

                    else:
                        continued_from_id = par.get('data-continued-from')

                    # if not continued_from_id or par_ls:
                    #    text = '\n\n'
                    #    par_ls[-1].words.append(Word(None, text))

                    if not continued_from_id and box_name == 'Reference':
                        ref_pars.append(par_id)

                    nodes = list(par)
                    tmp_ref = nodes[0].get('data-refid', False)
                    tmp_ref = nodes[0].get('data-refid', False)
                    if tmp_ref and tmp_ref != nodes[0].get('id'):
                        del nodes[0]

                    if continued_from_id:
                        par = pars[continued_from_id]
                    else:
                        par = Paragraph(sec_id, par_id, sec_name, box_name, [],
                                        [])
                        par_ls.append(par)

                    pars[par_id] = par

                    for node in filter(
                            lambda n: n.get(
                                'data-refid') is None or n.get('id') == n.get('data-refid'),
                            nodes):

                        sp_val = node.get('data-space')
                        if sp_val == 'nospace' or (
                                sp_val == 'bol' and
                            (not par.words
                             or tag_token.search(par.words[-1].text))):
                            space = None
                        else:
                            space = Word(None, ' ')

                        text = node.get('data-fullform') or node.text or ''

                        text = re.sub(r'\s+', ' ', text)
                        text = ''.join([
                            ligatures[c] if ligatures.get(c, False) else c
                            for c in text
                        ])

                        _id = node.get('id')
                        word_nodes[_id] = node

                        # inside a citation; skip everything
                        if cite:
                            math = None
                            space = None
                            word = Word(_id, '')
                            if cite == node.get('id'):
                                cite = None

                        # starting a citation; make a dummy word
                        elif node.get('data-cite-end', False):
                            if math:
                                par.words = par.backup_words
                                math = None
                                ignore_math = True

                            cite = node.get('data-cite-end')
                            cids = node.get('data-cite-id').split(',')
                            text = ', '.join(map(lambda c: 'CITE-' + c, cids))
                            cites.update({c: _id for c in cids})
                            word = Word(_id, text)

                        # starting an equation
                        elif not ignore_math and (
                                node.get('data-math') == 'B-Math' or
                            (node.get('data-math') == 'I-Math' and not math) or
                                (math_par and not math)):
                            par.backup_words = par.words.copy()
                            if space:
                                par.backup_words.append(space)
                            par.backup_words.append(Word(_id, text, node))

                            if math_par:
                                mid = 'MATH-' + par_id
                            else:
                                mid = 'MATH-' + _id
                            word = Word(_id, mid)
                            math = [mid, _id, _id, page_id] + [
                                float(a)
                                for a in node.get('data-bdr').split(',')
                            ]
                            math_ls.append(math)

                        # inside an equation: skip while calculating bbox
                        elif not ignore_math and (
                                node.get('data-math') == 'I-Math' or math_par):
                            if space:
                                par.backup_words.append(space)
                            par.backup_words.append(Word(_id, text, node))

                            space = None
                            word = Word(_id, '')
                            math[2] = _id
                            new = [
                                float(a)
                                for a in node.get('data-bdr').split(',')
                            ]
                            math[4] = min(math[4], new[0])
                            math[5] = min(math[5], new[1])
                            math[6] = max(math[6], new[2])
                            math[7] = max(math[7], new[3])

                        # normal texts
                        else:
                            math = None
                            ignore_math = False
                            word = Word(_id, text, node)

                        # finish the loop
                        if space is not None:
                            par.words.append(space)
                        if word is not None:
                            par.words.append(word)

                    # set last_par
                    if box_name != 'Body':
                        last_par = None
                    elif continued_from_id:
                        last_par = continued_from_id
                    else:
                        last_par = par_id

        par_pos = 0
        for p in par_ls:
            p.words.append(Word(None, '\n\n'))
            pos = 0
            for w in p.words:
                w.start = pos
                next_pos = pos + len(w.text)
                if w.node is not None:
                    w.node.set('data-from', str(par_pos + pos))
                    w.node.set('data-to', str(par_pos + next_pos))
                pos = next_pos
            par_pos += pos

        # textualize
        sent_ls = []
        for p in par_ls:
            sent_ls.extend(self.find_sentences(p))

        for s in sent_ls:
            for w in s.words:
                word_nodes[w].set('data-sent-id', str(s._id))

        # collect the data
        word_ls = [(w.get('id'), int(w.get('data-from', 0)),
                    int(w.get('data-to', 0)))
                   for w in doc.tree.xpath('//x:span', namespaces=ns)]
        doc.words = sorted(word_ls, key=lambda w: (w[1], w[2]))

        doc.text = ''.join([w.text for p in par_ls for w in p.words])
        doc.sentences = sent_ls
        doc.maths = math_ls
        doc.cites = [('CITE-' + p, ''.join([w.text
                                            for w in pars[p].words]).strip(),
                      cites.get(p, [])) for p in ref_pars]

        # scrub the tree; remove positions
        if remove_pos:
            for w in doc.tree.xpath('//x:span', namespaces=ns):
                if w.get('class', None) == 'word':
                    w.attrib.pop('data-from', None)
