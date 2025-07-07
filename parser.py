from bs4 import BeautifulSoup

def ctvc(html):
    pass

def keepcool(html):
    pass

def fortune(html):
    pass

def european_substack(html):
    pass

def general_text_parser(html):
    soup = BeautifulSoup(html,"html.parser")
    return soup.get_text()