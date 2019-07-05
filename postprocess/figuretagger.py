"""
The FigureTagger module.
"""

# libraries
import re
from collections import defaultdict

# use logger
from logging import getLogger
logger = getLogger('postprocess')


# the module
class FigureTagger:
    ns = {'x': 'http://www.w3.org/1999/xhtml'}

    def __init__(self):
        """The constructor.
        """
        logger.info('FigureTagger initialized.')

    def tag(self, doc):
        """Embed data-figref, data-figref-id, and data-figref-end tags (attributes) to the document.

        Args:
            doc (Document): The input document.
        """
        figures, paragraphs = self.__extract_figures(doc)
        self.__search_context_and_tag(figures, paragraphs)

    def __extract_figures(self, doc):
        """Extract target figures and paragraphs.

        Args:
            doc (Document): The input document.

        Returns:
            figures (defaultdict): Number of occurence of a data-fig.
            paragraphs (array): Paragraphs that are NOT captions, figures, or tables.
        """
        figures = defaultdict(int)
        paragraphs = []

        for box in doc.tree.xpath(
                'x:body/x:div/x:div[@data-name]', namespaces=FigureTagger.ns):
            for p in box.xpath('x:p', namespaces=FigureTagger.ns):
                if 'data-fig' in p.attrib:
                    # Paragraph with data-fig attribute is a figure
                    figures[p.attrib['data-fig']] += 1
                    logger.debug('{} {}'.format(p.attrib['data-fig'],
                                                p.attrib['id']))

                if 'data-name' in box.attrib and \
                        box.attrib['data-name'] not in ['Caption', 'Figure', 'Table']:
                    # Paragraphs that are not captions, figures, or tables
                    paragraphs.append(p)

        return figures, paragraphs

    def __search_context_and_tag(self, figures, paragraphs):
        """Search contexts that refers to figures, and tag them.

        Args:
            figures (defaultdict): Number of occurence of a data-fig.
            paragraphs (array): Paragraphs that are NOT captions, figures, or tables.
        """
        for data_fig in figures.keys():
            typ, num = data_fig.split('_', 1)
            refer = []
            refer.append('{}s?\s*{}'.format(typ, num))  # ex. Figure 1
            refer.append('{}s?(?:\s*\d+(?:and|,|\s)+)+{}'.format(
                typ, num))  # ex. Figures 1, 2, and 3
            # TODO: Context with sub-indexes, i.e. "Figures 4 (a) and 4 (b) show ..."

            for p in paragraphs:
                text = p.attrib['data-text']
                phrase = None
                for r in refer:
                    res = re.search('({})(?:\s|\)|\.\D|\.$|,|:)'.format(r),
                                    text)
                    if res:
                        phrase = res.group(1)
                        break

                if phrase:
                    self.__embed_attribute(p, phrase, data_fig)

    def __embed_attribute(self, p, phrase, data_fig):
        spans = p.xpath('x:span', namespaces=FigureTagger.ns)
        phrase = re.sub(r'([,.:])', r' \1 ', phrase)
        words = re.split(r'\s', phrase)

        for i in range(len(spans)):
            length = len(words) - 1  # length of spans that covers the phrase
            for j in range(i + 1, i + len(words)):
                if len(spans) > j and not spans[j].text:
                    # Ignore spans without any text
                    length += 1

            if (i + length < len(spans) and spans[i].text
                    and spans[i + length].text and spans[i].text == words[0]
                    and spans[i + length].text == words[-1]):
                if 'data-figref-id' in spans[i].attrib:
                    spans[i].attrib['data-figref-id'] += ',{}'.format(data_fig)
                else:
                    spans[i].attrib['data-figref-id'] = data_fig

                spans[i].attrib['data-figref'] = 'B-FIG'
                if 'data-figref-end' in spans[i].attrib:
                    if spans[i + length].attrib['id'] > spans[i].attrib[
                            'data-figref-end']:
                        spans[i].attrib['data-figref-end'] = spans[
                            i + length].attrib['id']
                        for j in range(1, length + 1):
                            spans[i + j].attrib['data-figref'] = 'I-FIG'
                else:
                    spans[i].attrib['data-figref-end'] = spans[
                        i + length].attrib['id']
                    for j in range(1, length + 1):
                        spans[i + j].attrib['data-figref'] = 'I-FIG'
