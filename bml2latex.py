import sys
import os
import re
import bml
from io import StringIO

SUIT2LATEX = { 'C': '\BC', 'D': '\BD', 'H': '\BH', 'S': '\BS' }

def latex_replace_suits_bid(matchobj):
    text = matchobj.group(0)
    for s in ['C', 'D', 'H', 'S']:
        text = text.replace(s, SUIT2LATEX[s])
    text = text.replace('N', 'NT')
    text = text.replace('AP', 'All pass')
    return text

def latex_replace_suits_desc(matchobj):
    text = matchobj.group(1)
    for s in ['c', 'd', 'h', 's']:
        text = text.replace('!' + s, SUIT2LATEX[s.upper()])
    if matchobj.group(2) == ' ':
        text += '\\ '
    elif matchobj.group(2) == '\n':
        text += '\\ \n'
    else:
        text += ' ' + matchobj.group(2)
    return text

def latex_replace_suits_header(matchobj):
    text = matchobj.group(1)
    text = text.replace('!c', '\pdfc')
    text = text.replace('!d', '\pdfd')
    text = text.replace('!h', '\pdfh')
    text = text.replace('!s', '\pdfs')
    if matchobj.group(2) == ' ':
        text += '\\ '
    return text

def latex_bidtable(children, file, first=False):
    bid = None
    desc = None
        
    for i in range(len(children)):
        c = children[i]
        
        if bml.args.verbose >= 2:
            print("child %d: %s" % (i, str(c)))

        if not first:
            if bml.args.tree:
                file.write('\n')
            else:
                file.write('\\\\\n')

        if c.bid != bml.EMPTY:
            bid = re.sub(r'\d([CDHS]|N(?!T))+', latex_replace_suits_bid, c.bid)
            bid = re.sub(r'^P$', 'Pass', bid)
            bid = re.sub(r'^R$', 'Rdbl', bid)
            bid = re.sub(r'^D$', 'Dbl', bid)
            bid = re.sub(r';(?=\S)', '; ', bid)
            bid = bid.replace('->', '$\\rightarrow$')
            dots = "........"[:-1*len(bid.replace('\\',''))]
            desc = latex_replace_characters(c.desc)
        else:
            bid = "\\O"
            desc = None

        if bml.args.tree:
            file.write(' .%d ' % (c.level()))
        file.write(bid)
        
        if desc:
            desc = re.sub(r'(![cdhs])([^!]?)', latex_replace_suits_desc, desc)
            if bml.args.tree:
                desc = desc.replace('\\n', '\\\\\n')
                file.write(dots + '\\begin{minipage}[b]{0.8\\textwidth}\n' + desc.replace('.', '{.}') + '\n\\end{minipage}')
            else:
                desc = desc.replace('\\n', '\\\\\n\\>')
                file.write(' \\> ' + desc)

        if bml.args.tree:
            file.write('. ')
            
        if len(c.children) > 0:
            if not bml.args.tree:
                file.write('\\+')
            latex_bidtable(c.children, file)
            if not bml.args.tree:
                file.write('\\-')
                
        first = False
            
def latex_diagram(diagram, file):
    header = []
    suits = {'S':'\\BS ',
             'H':'\\BH ',
             'D':'\\BD ',
             'C':'\\BC '}
    players = {'N':'North',
               'E':'East',
               'S':'South',
               'W':'West'}
    if diagram.board:
        header.append('Board %s' % diagram.board)
    if diagram.dealer and diagram.vul:
        header.append('%s / %s' % (players[diagram.dealer], diagram.vul))
    elif diagram.dealer:
        header.append(diagram.dealer)
    elif diagram.vul:
        header.append(diagram.vul)
    if diagram.contract:
        level, suit, double, player = diagram.contract
        if level == 'P':
            header.append("Pass")
        else:
            contract = level + suits[suit]
            if double:
                contract += double
            contract += ' by %s' % players[player]
            header.append(contract)
    if diagram.lead:
        suit, card = diagram.lead
        lead = 'Lead ' + suits[suit.upper()]
        lead += card
        header.append(lead)

    header = '\\\\'.join(header)
    
    def write_hand(hand, handtype):
        if hand:
            handstring = '{\\%s{%s}{%s}{%s}{%s}}\n' % \
                         (handtype, hand[0], hand[1], hand[2], hand[3])
            handstring = handstring.replace('-', '\\void')
            file.write(handstring)
        else:
            file.write('{}\n')
    if diagram.south:
        file.write('\\dealdiagram\n')
        handtype = 'hand'
        if(diagram.west or diagram.east):
            handtype = 'vhand'
        write_hand(diagram.west, handtype)
        write_hand(diagram.north, handtype)
        write_hand(diagram.east, handtype)
        write_hand(diagram.south, handtype)
        file.write('{%s}\n\n' % header)
    elif diagram.north:
        file.write('\\dealdiagramenw\n')
        handtype = 'vhand'
        write_hand(diagram.west, handtype)
        write_hand(diagram.north, handtype)
        write_hand(diagram.east, handtype)
        file.write('{%s}\n\n' % header)
    else:
        file.write('\\dealdiagramew\n')
        handtype = 'vhand'
        write_hand(diagram.west, handtype)
        write_hand(diagram.east, handtype)
        
def replace_quotes(matchobj):
    return "``" + matchobj.group(1) + "''"

def replace_strong(matchobj):
    return '\\textbf{' + matchobj.group(1) + '}'

def replace_italics(matchobj):
    return '\\emph{' + matchobj.group(1) + '}'

def replace_truetype(matchobj):
    return '\\texttt{' + matchobj.group(1) + '}'

def latex_replace_characters(text):
    text = text.replace('->', '$\\rightarrow$')
    text = text.replace('#', '\\#')
    text = text.replace('_', '\\_')
    text = re.sub(r'(?<=\s)"(\S[^"]*)"', replace_quotes, text, flags=re.DOTALL)
    text = re.sub(r'(?<=\s)\*(\S[^*]*)\*', replace_strong, text, flags=re.DOTALL)
    text = re.sub(r'(?<=\s)/(\S[^/]*)/', replace_italics, text, flags=re.DOTALL)
    text = re.sub(r'(?<=\s)=(\S[^=]*)=', replace_truetype, text, flags=re.DOTALL)
    return text
            
def to_latex(content, f):
    # the preamble
    # TODO: Config file for the preamble?
    if bml.args.tree:
        usepackage_dirtree = r"""\usepackage{dirtree}"""
    else:
        usepackage_dirtree = ""

    bml_tex_str = None
    if not bml.args.include_external_files:
        bml_tex_str = "\include{bml}"
    else:
        with open('bml.tex', 'r') as bml_tex:
            bml_tex_str = bml_tex.read()
        
    preamble = r"""\documentclass[a4paper]{article}
\usepackage[margin=1in]{geometry}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{newcent}
\usepackage{helvet}
\usepackage{graphicx}
%s
\usepackage[pdftex, pdfborder={0 0 0}]{hyperref}
\frenchspacing

%s
""" % (usepackage_dirtree, bml_tex_str)

    f.write(preamble)
    if 'TITLE' in bml.meta:
        f.write('\\title{%s}\n' % bml.meta['TITLE'])
    if 'AUTHOR' in bml.meta:
        f.write('\\author{%s}\n' % bml.meta['AUTHOR'])

    f.write('\\begin{document}\n')
    f.write('\\maketitle\n')
    f.write('\\tableofcontents\n\n')
        
    # then start the document
    for c in content:
        content_type, text = c
        if content_type == bml.ContentType.PARAGRAPH:
            text = re.sub(r'(![cdhs])([^!]?)', latex_replace_suits_desc, text)
            text = latex_replace_characters(text)
            f.write(text + '\n\n')
        elif content_type == bml.ContentType.BIDTABLE:
            if not text.export:
                continue
            if bml.args.tree:
                f.write('\\\n')
                f.write('\\dirtree{%%\n')
            else:
                f.write('\\begin{bidtable}\n')
            latex_bidtable(text.children, f, True)
            if bml.args.tree:
                f.write('\n}\n\n')
            else:
                f.write('\n\\end{bidtable}\n\n')
        elif content_type == bml.ContentType.DIAGRAM:
            latex_diagram(text, f)
        elif content_type == bml.ContentType.H1:
            text = latex_replace_characters(text)
            text = re.sub(r'(![cdhs])( ?)', latex_replace_suits_header, text)
            f.write('\\section{%s}' % text +'\n\n')
        elif content_type == bml.ContentType.H2:
            text = latex_replace_characters(text)
            text = re.sub(r'(![cdhs])( ?)', latex_replace_suits_header, text)
            f.write('\\subsection{%s}' % text +'\n\n')
        elif content_type == bml.ContentType.H3:
            text = latex_replace_characters(text)
            text = re.sub(r'(![cdhs])( ?)', latex_replace_suits_header, text)
            f.write('\\subsubsection{%s}' % text +'\n\n')
        elif content_type == bml.ContentType.H4:
            text = latex_replace_characters(text)
            text = re.sub(r'(![cdhs])( ?)', latex_replace_suits_header, text)
            f.write('\\paragraph{%s}' % text +'\n\n')
        elif content_type == bml.ContentType.LIST:
            f.write('\\begin{itemize}\n')
            for i in text:
                i = latex_replace_characters(i)
                i = re.sub(r'(![cdhs])([^!]?)', latex_replace_suits_desc, i)
                f.write('\\item %s\n' % i)
            f.write('\n\\end{itemize}\n\n')
        elif content_type == bml.ContentType.DESCRIPTION:
            f.write('\\begin{description}\n')
            for i in text:
                i = latex_replace_characters(i)
                i = re.sub(r'(![cdhs])([^!]?)', latex_replace_suits_desc, i)
                i = i.split(' :: ')
                f.write('\\item[%s] %s\n' % (i[0], i[1]))
            f.write('\n\\end{description}\n\n')
        elif content_type == bml.ContentType.ENUM:
            f.write('\\begin{enumerate}\n')
            for i in text:
                i = latex_replace_characters(i)
                i = re.sub(r'(![cdhs])([^!]?)', latex_replace_suits_desc, i)
                f.write('\\item %s\n' % i)
            f.write('\n\\end{enumerate}\n\n')
        elif content_type == bml.ContentType.TABLE:
            f.write('\\begin{tabular}{')
            columns = 0
            for i in text:
                if len(i) > columns:
                    columns = len(i)
            f.write('l' * columns)
            f.write('}\n')
            for i in text:
                if re.match(r'[+-]+$', i[0]):
                    f.write('\\hline\n')
                else:
                    f.write(' & '.join(i))
                    f.write(' \\\\\n')
            f.write('\\end{tabular}\n\n')
        elif content_type == bml.ContentType.BIDDING:
            f.write('\\begin{bidding}\n')
            for i, r in enumerate(text):
                r = ' \> '.join(r)
                r = re.sub(r'\d([CDHS]|N(?!T))+', latex_replace_suits_bid, r)
                r = r.replace('AP', 'All pass')
                r = r.replace('D', 'Dbl')
                r = r.replace('P', 'Pass')
                r = r.replace('R', 'Rdbl')

                f.write(r)
                if i < len(text) - 1:
                    f.write('\\\\\n')
            f.write('\n\\end{bidding}\n\n')
            
    f.write('\\end{document}\n')

if __name__ == '__main__':
    bml.args = bml.parse_arguments(description='Convert BML to LaTeX.')
    bml.content_from_file(bml.args.inputfile)
    if not bml.args.outputfile:
        bml.args.outputfile = '-' if bml.args.inputfile == '-' else bml.args.inputfile.split('.')[0] + '.tex'
    if bml.args.verbose >= 1:
        print("Output file:", bml.args.outputfile)
    if bml.args.outputfile == '-':
        to_latex(bml.content, sys.stdout)
    else:
        with open(bml.args.outputfile, mode='w', encoding="utf-8") as f:
            to_latex(bml.content, f)
